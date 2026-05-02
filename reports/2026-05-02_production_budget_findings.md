# Production Budget Findings — what 20-30 min/analysis really excludes

**Date:** 2026-05-02
**Hardware:** NVIDIA DGX Spark (GB10, 128 GB)
**Test pipeline:** literary-master v2 full `/api/analyze`
**Reference inputs:**
- 1 KB Gift of Magi excerpt (4 paragraphs)
- 11.7 KB Gift of Magi full story (~2,200 words / 159 blocks)

This report records what we tried, what works inside the **20-30 min single-analysis production budget** stated for literary-master, what we had to drop because it pushed past the budget, and the architectural alternatives that would actually unblock the budget if pursued.

## TL;DR

- 1 KB excerpt completes in ~7 min on default settings — comfortably in budget.
- 11.7 KB full short story completes in **40-70 min** depending on tuning — **out of budget regardless of which knobs we turn at the current architecture**.
- Per-token wall-clock is dominated by Pass 2 block batches (159 blocks × ~85 s/batch on gemma4 = 46 min). No single-model tuning got block stage under ~25-30 min on this input.
- Genuine budget compliance for full short stories needs an **architectural** change, not parameter tuning. Five alternatives proposed below; #1 (UI text-size cap) is the cheapest win.

## Hardware + model baseline

| Stage | Model | Tokens/s | Notes |
|---|---|---:|---|
| All stages default | `bjoernb/gemma4-26b-fast` (Q4_K_M, 17 GB) | 28 | DGX Spark memory bandwidth (~273 GB/s) bottleneck |
| Block batch alternative | `gpt-oss:20b` (MXFP4, 13 GB) | 35 | DGX, not Mac's 56. **Disqualified** — Korean semantic errors |
| Fallback | `qwen3:30b-a3b-instruct-2507-q4_K_M` (Q4_K_M, 18 GB) | 47 | JSON champion; long-form Korean untested for blocks |

## Things tried — kept

| Change | Effect | Where |
|---|---|---|
| `BATCH_PARALLELISM=2` | Block stage ~1.6× faster (probe shows 1.93×, real ~1.4-1.6× with prompt overhead) | orchestrator parallel dispatch |
| Glossary stage (Track C) | +30s. Quality protection — pins canonical Korean for proper nouns (e.g. "Magi" → "마기"), prevents the gpt-oss-family "마귀" mistranslation across batches | new Pass 1.5 |
| `FALLBACK_MODEL=qwen3:30b` | Salvages malformed Profile/Synthesis merge JSON | F-1, conditional |
| Coverage Repair `retries: 1` (was 2) | Saves ~3-5 min on long inputs; small loss in recovery rate | repair-agent default |
| Verify v2 `maxIterations: 2` (was 3) | Saves ~1 min; iter 3 historically rarely converged | verify-agent input |
| Phase 3 synthesis-side trigger 800 chars (was 1500) | Catches more synthesis-side proofread cases | gate condition |
| Per-batch retry on parse-fail | Recovers blocks that would otherwise be lost without changing batch size | batch loop |
| Phase G hallucination guard | Synthesis prompt + Verify Step C; verify catches what synthesis still hallucinates. **Free** (prompt-only) | synthesis.ts + verify.ts |

## Things tried — dropped from default for budget reasons

| Change | Why dropped | Status |
|---|---|---|
| `BLOCK_BATCH_MODEL=gpt-oss:20b` | Block 1 produced **"마귀의 선물"** (devils) instead of **"마기의 선물"** (Magi) — same Korean semantic error gpt-oss:120b made. gpt-oss family disqualified for Korean block translation. | Code path retained for non-Korean use cases via env var; default unset |
| Batch size 5→3 + per-batch retry | 53 batches × longer overhead per batch yielded ~30 min slower total than batch-5 + retry. Smaller batch helps loss recovery in theory; in practice the per-batch retry already handled it. | Reverted to 5 |
| `max_predict 4000 → 2200` (block prompts) | Ollama generates until natural EOS, not max_predict. Per-batch wall-clock unchanged. | Reverted to 4000 |
| `BATCH_PARALLELISM=3` | Slower than parallelism=2: 11 min for 3 batches (3.7 min/batch effective) vs parallelism=2's 1.75 min/batch effective. Memory-bandwidth contention + KV-cache pressure outweighs added concurrency. | Default cap at 2 |
| Phase 3 Korean Proofreader on **all** block fields by default | 159 blocks × 3 fields × ~2s = ~10-15 min added — alone ~25-50% of the budget. | Made opt-in via `PROOFREAD_BLOCKS=true`. Synthesis-side fields still gated by length |

## Things tried — dropped without retest because evidence said they wouldn't help

| Change | Why | Evidence |
|---|---|---|
| Routing block stage to a faster model entirely | Faster models (gpt-oss:20b 35 t/s, qwen3:30b 47 t/s) are 1.25-1.7× of gemma4's 28 t/s. Estimated full-story wall-clock improvement: 47 min → 28-38 min. Still over budget. | Korean quality regression (gpt-oss) outweighs speed gain |
| `OLLAMA_NUM_PARALLEL` server tuning above default | 2-request probe already showed ~1.93× at default (which appears to be ≥4). Application-level dispatch is what caps benefit, not server config. | Probe data |
| Skipping Coverage Repair entirely | Saves ~10 min but turns 11% block loss into permanent missing data | Quality regression unacceptable |
| Skipping Verify v2 entirely | Saves ~5 min but loses the only guard against synthesis hallucinations | Phase G's value collapses |

## Where the budget actually goes (default + Track B + C, 11.7 KB)

| Stage | Wall-clock | Why |
|---|---:|---|
| Profile (single-shot) | ~1.5 min | one LLM call, full text |
| Glossary | ~30 s | one LLM call, sample of text |
| Block batches (parallelism=2) | **~28-30 min** | 32 batches in 16 groups × ~1.75 min/group |
| Coverage Repair | ~5 min | depends on missing/empty count (0-18 typical) |
| Synthesis (chunk-merge) | ~3 min | 2 partials + 1 merge for ≥150 blocks |
| Verify v2 (max 2 iter) | ~5 min | 2 iter × verify+correct cycles |
| **Total** | **~43-45 min** | |

Block batches alone (~30 min) is at the budget ceiling. Everything else collectively (~13 min) breaks it.

## Architectural alternatives that would actually unblock the budget

Ranked by implementation cost vs. budget impact.

### 1. UI-level text-size cap (cheapest)

**Mechanism**: at submit time, classify input length and route to the right UX:

| Input | UX | Wall-clock |
|---|---|---:|
| < 5 KB | Synchronous, real-time progress | ~7-15 min |
| 5-10 KB | Synchronous with explicit "this will take ~25 min" warning | ~20-30 min |
| > 10 KB | **Reject by default**. Offer "long-form mode" opt-in (next item). |

**Cost**: ~1 hr UI code in literary-master.
**Budget impact**: keeps default-mode users in budget; long-form is a separate product expectation.
**Trade-off**: full short stories require explicit user action.

### 2. Async submit + notification UX

**Mechanism**: submit goes to a queue; user gets a "분석 요청 접수" message with estimated time and a notification (email / browser push / saved-page indicator) when done.

**Cost**: ~1 day UI/server work (job queue, status endpoint, notification mechanism).
**Budget impact**: any-length analyses become acceptable since user isn't waiting in the page.
**Trade-off**: completely changes the product feel from "tool" to "service". Bigger commitment.

### 3. vLLM continuous batching for blocks

**Mechanism**: replace Ollama for the Pass 2 block stage with vLLM, which natively supports continuous batching and gets 4-8× throughput on identical hardware for batched workloads.

**Cost**: significant — vLLM service alongside Ollama, model availability check (gemma4 has Q4_K_M GGUF only; vLLM prefers AWQ/GPTQ/FP8). We have `qwen36-vllm-env` already running for one model; reusing the infra is plausible.
**Budget impact**: Pass 2 block stage potentially 4-8× faster — would bring 11.7 KB Gift of Magi to ~12-15 min comfortably in budget.
**Trade-off**: model swap likely needed (gemma4 not first-class on vLLM); Korean quality must be re-validated for the chosen vLLM model.

### 4. Slim the per-block schema

**Mechanism**: reduce annotations object size. The current per-block JSON has 16 annotation fields, mostly emitted as null/empty/false defaults; each batch wastes tokens emitting defaults for every block.

Specific cuts:
- Drop `dialogueSpeaker` and `notable_quote` (rarely populated in literary text)
- Make `key_vocabulary` optional and skip unless `flag_for_revision` is true
- Move `pronunciation` field to a separate enrichment pass for vocab only
- Remove `containsCallback`/`callbackRef` (covered by foreshadowing)

**Cost**: ~3-4 hr (schema, prompt, downstream consumers).
**Budget impact**: estimated ~30% per-batch token reduction → 30% block-stage wall-clock reduction. ~30 min → ~21 min. **Just inside budget**.
**Trade-off**: less annotation richness; need migration for already-saved teaching materials.

### 5. Pre-segmentation by section + parallel segments

**Mechanism**: for long inputs, segment by chapter/section first (Segmentation Agent v2 already exists). Run each section as a separate analysis job in parallel (different model instances or sequential time-boxed jobs). Stitch synthesis at the end.

**Cost**: ~1-2 days — orchestration redesign, segment-aware synthesis merge.
**Budget impact**: per-section budget is small, total wall-clock = max(section times) + merge.
**Trade-off**: cross-section coherence (synthesis quality) requires careful merge. Better fit for *novellas/chapter books* than short stories.

### 6. Two-pass split: quick pass + deep pass

**Mechanism**: first pass produces only block translations (no annotations), runs in ~10 min. User sees translations immediately. Second pass runs synthesis + annotations + verify in background, results appended later.

**Cost**: ~1 day — pipeline split, two-phase storage, UI display change.
**Budget impact**: first-result-visible time ~10 min for 11.7 KB. Total time same as current.
**Trade-off**: complicates UX (two states per analysis). Best for "I want to read in Korean immediately, depth analysis can wait" use case.

## Recommended path

**Short-term (this week)**: implement #1 (text-size cap) as the immediate operational fix. Default to <5 KB synchronous; surface a clear "긴 텍스트는 곧 지원" message for >5 KB.

**Medium-term (next 2-3 weeks)**: pursue #4 (schema slim) in parallel with #2 (async UX) since they compose well — #4 brings short stories under 25 min synchronously; #2 catches the rest.

**Long-term (separate sprint)**: evaluate #3 (vLLM block stage) when a Korean-validated vLLM-compatible model is available. Requires its own model evaluation cycle (likely qwen3 or DeepSeek family on vLLM; both untested for our use case).

**Skip**: #5 and #6 for now — both add architectural complexity without a clear product win for short fiction.

## Methodology

All measurements taken on the same DGX Spark instance, identical Ollama 0.20.5 server, default `OLLAMA_NUM_PARALLEL`, identical Gift of Magi inputs. Each tuning change validated with a full pipeline run. Wall-clock numbers are single-sample (each run is 30-60 min; multi-sample testing was budget-prohibitive itself).

Quality observations cite specific saved teaching-material JSONs for verification. See `data/2026-05-02_korean_long_form/` for raw evidence and the companion [korean_long_form_failure_modes report](2026-05-02_korean_long_form_failure_modes.md) for the underlying Korean quality findings that constrained the model choices above.

# Combo D Configuration Playbook — D-20b baseline through D-120b premium

**Date:** 2026-05-02
**Purpose:** Reference document for choosing and running Combo D ensemble configurations on local LLM hardware. Covers the canonical D-20b (universal default) and D-120b (DGX premium) configurations in detail. Other variants (D-S, D-C, D-SC) covered in [combo_d_swap_experiments.md](2026-05-02_combo_d_swap_experiments.md).

## Pipeline overview — what Combo D is

Combo D ("Triple Gloss") is a 4-stage local-LLM ensemble for chapter-level analysis of humanities and social-science texts. The design comes from [devbourne/locallm-humanities-bench](https://github.com/devbourne/locallm-humanities-bench).

```
                ┌─ 02a Gloss-meta   (metaphysical/epistemological)  ┐
01 Extract  →   ├─ 02b Gloss-polit  (political/linguistic)          ├ → 03 Synthesis → 04 Critique
   (JSON)       └─ 02c Gloss-text   (close textual reading)         ┘    (3-way merge)    (anchored)
                       3-way parallel
```

The unifying idea: a single model has one perspective; splitting analysis into *parallel angles* and then forcing a *named-tension synthesis* produces output that no single model can match — it surfaces tensions where the angles disagree and forces the synthesizer to take a position.

### Why each stage exists

**Stage 01 — Extract (JSON):** Produces a structured outline of the passage's argument: thesis, premises, key concepts (term + role), argumentative moves, intended conclusion. Feeds every downstream stage so all 3 glosses work from the same ground truth, not from independent re-readings of the raw text. Without this, glosses can drift apart on basic facts.

**Stage 02 — Triple Gloss (parallel):** Three independent semantic glosses, each pinned to a different angle:
- *02a Metaphysical*: ontological symbols, theory of knowledge being asserted, non-obvious metaphysical implications
- *02b Political/linguistic*: chains as conditioning, power dynamics, Greek concepts (paideia, periagoge, episteme), psychological/political stakes
- *02c Textual close-reading*: specific passage details (puppeteers, sequence of vision, Glaucon's "Yes/Certainly"), rhetorical strategy, internal tensions in the imagery

The key insight: a single model defaulted to one angle (usually metaphysical for Plato). Pinning three different models to three different angles via prompt forces *perspective diversity*. This is the core of the ensemble's value.

**Stage 03 — Synthesis (3-way merge):** Reads all 3 glosses + original passage. Produces three sub-sections:
- *Unified Gloss*: integrates all 3 angles without redundancy
- *Complementary Insights*: where each gloss illuminates another (one names what another implies; metaphysical claim grounds political stake)
- *Unresolved Tensions*: where glosses disagree, **with explicit verdict on which is more defensible** ← this is the load-bearing instruction

The synthesis verdict is what turns "three opinions" into "an argument that took a position." Skipping this verdict (or letting it hedge) collapses the ensemble to a 3-gloss summary.

**Stage 04 — Critique (anchored):** Reads original passage + synthesis (with flagged tensions). Produces:
- *Weaknesses*: 2-3 internal tensions in the source itself (with branded labels if possible)
- *Counterarguments*: 2 specific objections from later philosophical traditions, named
- *Follow-up questions*: 3 ordered concrete → speculative

The critique anchors on synthesis tensions ("the synthesis correctly identifies the tension between X and Y, but..."), producing more concrete output than a critique that tries to read the raw passage cold.

## D-20b — Universal Default Configuration

The canonical Combo D from the upstream README. Universally deployable.

### Slot assignments

| Stage | Model | Tag | Memory | Why this model |
|---|---|---|---|---|
| 01 Extract | Qwen3 30B-A3B | `qwen3:30b-a3b-instruct-2507-q4_K_M` | 18 GB | Cleanest JSON adherence; no `<think>` leak; no code-fence pollution |
| 02a Gloss-meta | Qwen3 30B-A3B | (same) | (already loaded) | Strong abstract/analytical phrasing; pairs with extract |
| 02b Gloss-polit | Gemma4 26B-fast | `bjoernb/gemma4-26b-fast:latest` | 17 GB | Best at branded framings + Greek term integration (*periagoge*, *episteme*); naturally goes political |
| 02c Gloss-text | GPT-OSS 20B | `gpt-oss:20b` | 13 GB | Strongest textual-detail capture in single-model tests; uniquely catches puppeteers as media intermediaries |
| 03 Synthesis | Qwen3 30B-A3B | (same) | (loaded) | Structurally cleanest sectioning, consistent verdict format |
| 04 Critique | Gemma4 26B-fast | (same) | (loaded) | Brand-creation specialist (coins memorable labels: "Continuity Fallacy", "Coercion Paradox") |

**Total resident memory during parallel 02 stage**: 18 + 17 + 13 = **48 GB** (fits any hardware ≥64 GB)

### Wall-clock — Mac Studio 64 GB baseline (canonical README run)

| Stage | Model | tok | s | tok/s |
|---|---|---:|---:|---:|
| 01 Extract | Qwen3 | 438 | 16.4 | 51.9 |
| 02a Gloss-meta | Qwen3 | 518 | 18.0 | 32.9 |
| 02b Gloss-polit | Gemma4 | 1654 | 100.2 | 23.2 |
| 02c Gloss-text | GPT-OSS:20b | 1317 | 41.4 | 39.2 |
| 03 Synthesis | Qwen3 | 1508 | 44.7 | 38.3 |
| 04 Critique | Gemma4 | 2259 | 118.1 | 19.9 |
| **Total (with parallel 02)** | | **7,694** | **~279s** | |

### Wall-clock — DGX Spark 128 GB

| Stage | Model | tok | s | tok/s |
|---|---|---:|---:|---:|
| 01 Extract | Qwen3 | 482 | 17.7 | 46.5 |
| 02a Gloss-meta | Qwen3 | 488 | 18.9 | 29.4 |
| 02b Gloss-polit | Gemma4 | 1582 | 120.9 | 17.3 |
| 02c Gloss-text | GPT-OSS:20b | 1154 | 91.0 | 14.8 |
| 03 Synthesis | Qwen3 | 1568 | 54.8 | 31.9 |
| 04 Critique | Gemma4 | 2246 | 95.7 | 25.6 |
| **Total (with parallel 02)** | | **7,520** | **~289s** | |

DGX is +3.5% slower than Mac at the wall-clock level despite per-token slowdown of 25-45% on individual stages. The ensemble structure absorbs the per-token gap because (a) stage 04 critique on the large synthesis context is *faster* on DGX, and (b) parallel 02 stage's GPT-OSS slowdown is invisible because gemma4 is the bottleneck either way.

### Output quality — D-20b on Plato passage

Produces:
- **Stage 01 Extract**: ~6-8 key concepts, 7-9 premises, structured argumentative moves
- **Stage 02 Triple gloss**: three perspective-diverse readings, each ~400-1500 words
- **Stage 03 Synthesis**: 3 unresolved tensions surfaced with explicit verdicts
- **Stage 04 Critique**: 2-3 branded weakness labels, 2 traditions invoked, 3 follow-up questions

Composite quality (Mac canonical run): **9.0 / 10**

Mac D-20b's signature labels: *Puppeteer's Vacuum*, *Compulsion Loop*, *Epistemic Leap*

### How to run D-20b

```bash
# In the locallm-humanities-bench repo
cd bench/
bash run_ensemble_d.sh
# Output: multi_agent/  (legacy name) or multi_agent_d/
```

Models needed (Ollama):
```bash
ollama pull qwen3:30b-a3b-instruct-2507-q4_K_M
ollama pull bjoernb/gemma4-26b-fast
ollama pull gpt-oss:20b
```

Settings (hard-coded in `run_ensemble_d.sh`):
- `temperature=0.3`
- `num_ctx=8192`
- `stream=false`
- API: `POST http://localhost:11434/api/generate`

To analyze a different passage: replace `bench/passage.txt`. Output structure stays identical, all intermediate stages preserved as standalone files.

## D-120b — DGX Premium Configuration (RECOMMENDED for ≥128 GB hardware)

Same as D-20b except stage 02c (textual close-reading) uses `gpt-oss:120b` (65 GB MXFP4) instead of `gpt-oss:20b` (13 GB MXFP4).

### Slot assignments

| Stage | Model | Tag | Memory | Change from D-20b |
|---|---|---|---|---|
| 01 Extract | Qwen3 30B-A3B | `qwen3:30b-a3b-instruct-2507-q4_K_M` | 18 GB | unchanged |
| 02a Gloss-meta | Qwen3 30B-A3B | (same) | (loaded) | unchanged |
| 02b Gloss-polit | Gemma4 26B-fast | `bjoernb/gemma4-26b-fast:latest` | 17 GB | unchanged |
| 02c Gloss-text | **GPT-OSS 120B** | `gpt-oss:120b` | **65 GB** | **+52 GB vs 20b** |
| 03 Synthesis | Qwen3 30B-A3B | (loaded) | — | unchanged |
| 04 Critique | Gemma4 26B-fast | (loaded) | — | unchanged |

**Total resident memory during parallel 02 stage**: 18 + 17 + 65 = **100 GB** (requires ≥128 GB hardware — DGX Spark territory only)

### Why upgrade only the textual gloss slot

Single-model Round 4 measurements showed `gpt-oss:120b` is the field's depth specialist on textual close-reading specifically:
- Uniquely identifies Plato's **Two Worlds** distinction (world of sight vs world of knowledge)
- Catches **ethics-primacy**: "scientific/mathematical knowledge ... is still a step below ultimate moral insight"
- Implies *methexis* without naming it: "rationality itself is a participation in the Good"
- Frames political peril as Socrates-trial echo ("corrupting the masses")

These are catches no other keeper produces in single-model mode. Putting 120b in 02c gives the ensemble *a textual gloss with crystallized philosophical formulations* that Qwen3 and Gemma4 syntheses can then anchor on.

The other slots don't benefit from 120b in the same way:
- 01 Extract: 120b is no better at JSON than Qwen3 (and Qwen3 is more reliable)
- 02a/02b: 120b would give just "deeper" prose but doesn't surface different angles
- 03 Synthesis: 120b shifts to meta-level tensions (see [D-S variant](2026-05-02_combo_d_swap_experiments.md)) — different territory, exploratory only
- 04 Critique: gemma4 is the brand-creation specialist; 120b loses memorability (see [D-C variant](2026-05-02_combo_d_swap_experiments.md))

The 02c slot is the *unique fit* — close textual reading is exactly what 120b excels at, and the sharper textual gloss propagates through synthesis to critique without needing further model changes.

### Wall-clock — D-120b on DGX Spark

| Stage | Model | tok | s | tok/s |
|---|---|---:|---:|---:|
| 01 Extract | Qwen3 | 518 | 16.8 | 34.9 |
| 02a Gloss-meta | Qwen3 | 559 | 24.1 | 28.0 |
| 02b Gloss-polit | Gemma4 | 525 | 53.5 | 16.7 |
| 02c Gloss-text | **gpt-oss:120b** | 1039 | 93.6 | **24.4** |
| 03 Synthesis | Qwen3 | 1393 | 49.4 | 31.4 |
| 04 Critique | Gemma4 | 2244 | 94.0 | 25.9 |
| **Total (with parallel 02)** | | **6,278** | **~254s** | |

Notable: **gpt-oss:120b at 02c was *faster per-token* (24.4 t/s) than gpt-oss:20b at the same slot in the D-20b run (14.8 t/s)**. The 120b doesn't generate as much harmony-format thinking on the same prompt and does less self-correction. Larger model, less wasted compute.

Wall-clock 254s is within the 254-289s sampling-variance band of all 6 runs across rounds 6-9. **No additional time cost vs D-20b** despite 108% more memory.

### Output quality propagation

The 120b textual gloss feeds the entire downstream pipeline. Effects observed:

#### Stage 03 Synthesis (Qwen3 unchanged)
With sharper 02c input, Qwen3 synthesis surfaces a tension other variants don't catch: **"language: prison vs bridge"**. The 02c gloss's emphasis on rhetorical architecture ("silent chorus", "didactic force behind the veneer of collaborative discovery") gives the synthesizer material to identify this tension dimension that the 20b textual gloss didn't surface.

#### Stage 04 Critique (Gemma4 unchanged)
The richer synthesis input makes Gemma4 produce **3 branded labels matching its strongest single-model Plato critique verbatim** (*Continuity Fallacy*, *Coercion Paradox*) plus the ensemble-derived *Puppeteer Vacuum*. Reproduces gemma4's "A-game" inside the ensemble.

Plus invokes **Frankfurt School (Critical Theory)** — a tradition that no other round (single-model or ensemble, Mac or DGX, Round 1-9) used. The 120b gloss's emphasis on regime-of-truth / power-dynamics framings primed gemma4 toward Critical Theory.

### Composite quality (DGX D-120b on Plato): **9.5 / 10** — best in the proven-reliable category

### How to run D-120b

```bash
# In locallm-humanities-bench/bench/
bash run_ensemble_d_dgx_120b.sh
# Output: multi_agent_d_dgx_120b/
```

Or use this repo's [scripts/run_one_strip.sh](../scripts/run_one_strip.sh) approach for single-model + custom ensemble.

Additional model needed (vs D-20b):
```bash
ollama pull gpt-oss:120b   # 65 GB
```

All other settings identical to D-20b (same `temperature=0.3`, `num_ctx=8192`).

### When to choose D-120b over D-20b

| Choose D-120b if | Choose D-20b if |
|---|---|
| Hardware has ≥128 GB unified memory (DGX Spark, Mac Studio M2 Ultra 192GB) | Hardware ≤96 GB |
| Output will be published, graded, or inform original scholarship | Quick reads, summaries, test-prep, exploratory draft |
| Text rewards close textual analysis (most humanities/philosophy) | Text is purely conceptual with little rhetorical structure |
| You can spare ~5 min per chapter | Time-budget tight for multiple chapters in sequence |
| Want crystallized philosophical phrasing in output | Standard rigorous output is sufficient |

D-120b is **the new default for DGX Spark deployments** processing humanities texts where output quality matters.

## Configuration matrix at a glance

| Config | Stage 02c | Stage 03 | Stage 04 | Memory | Use case |
|---|---|---|---|---|---|
| **D-20b** | gpt-oss:20b | Qwen3 | Gemma4 | 48 GB | Universal default, any hardware ≥64 GB |
| **D-120b** | gpt-oss:120b | Qwen3 | Gemma4 | 100 GB | DGX premium, proven reliable |
| D-S | gpt-oss:120b | gpt-oss:120b | Gemma4 | 100 GB | Exploratory: meta-level synthesis tensions, novel labels |
| D-C | gpt-oss:120b | Qwen3 | gpt-oss:120b | 100 GB | Academic: cited works in critique |
| ✗ D-SC | gpt-oss:120b | gpt-oss:120b | gpt-oss:120b | 100 GB | Avoid: perspective collapse |

D-S, D-C, and D-SC details: [2026-05-02_combo_d_swap_experiments.md](2026-05-02_combo_d_swap_experiments.md).

## Operational notes

### Memory management on DGX Spark

128 GB total. D-120b uses 100 GB resident during parallel 02 stage. With Ollama's automatic loading, the system handles this:
- All three models stay resident throughout the run after first parallel stage
- 28 GB headroom for OS, ollama runner overhead, kernel caches
- No swap thrashing observed in our runs

If running multiple D-120b sessions concurrently or alongside other work that needs GPU memory, consider unloading models between runs (`ollama stop`).

### Why temperature=0.3

Default for all reported runs. Trade-off:
- Lower (0.0-0.2): more deterministic, less creative — gemma4 brand-creation suffers
- Higher (0.5+): more variation, JSON adherence in stage 01 starts to suffer
- 0.3 is the sweet spot for humanities analysis where structured output matters but creative framings are valued

### Why num_ctx=8192

The Plato passage is ~750 words (~1k tokens). With prompts and prior-stage context, individual stages use 1.5-7 KB. 8192 token context fits everything with margin.

For longer chapters (Sandel ch.1 = 3,278 words), the README upstream uses `num_ctx=16384` via `run_ensemble_d_generic.sh`. Note: 3-way parallel at 16K context produces significant memory contention on DGX Spark (Qwen3 dropped from 47 → 11 t/s in the Sandel run).

### Reproduction

Both Mac D-20b and DGX D-120b runs are deterministic-ish at temperature=0.3 — exact outputs will vary slightly each run (sampling), but the *structural* output (3 glosses, synthesis with 3 tensions, critique with 2-3 labels and 2 traditions) is consistent. Composite quality scores stay within ±0.5 across runs.

The signature labels (*Continuity Fallacy*, *Compulsion Loop*, etc.) are gemma4's reproducible patterns on the Plato text — different runs surface different subsets but draw from the same conceptual repertoire.

## Related documents

- [Combo D ensemble — DGX vs Mac platform comparison](2026-05-02_combo_d_dgx_vs_mac.md) — the wall-clock parity finding
- [Combo D slot-swap experiments](2026-05-02_combo_d_swap_experiments.md) — D-S / D-C / D-SC variants in detail
- [locallm-humanities-bench Round 4-9 (canonical)](https://github.com/devbourne/locallm-humanities-bench/blob/main/bench/DGX_SPARK_RESULTS.md)

## Files referenced

```
data/2026-05-02_combo_d_dgx/        # D-20b on DGX (Round 6) — 8 files
data/2026-05-02_combo_d_dgx_120b/   # D-120b on DGX (Round 7) — 8 files
data/2026-05-02_combo_d_dgx_s/      # D-S variant (Round 8) — 8 files
data/2026-05-02_combo_d_dgx_c/      # D-C variant (Round 8) — 8 files
data/2026-05-02_combo_d_dgx_sc/     # D-SC variant (Round 9) — 8 files
```

Each folder: `01_extract.json`, `02a_gloss_qwen3.md`, `02b_gloss_gemma4.md`, `02c_gloss_gptoss.md`, `03_synthesis.md`, `04_critique.md`, `REPORT.md`, `timings.csv`.

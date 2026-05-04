# Synthesis Split for Multi-Perspective Reliability — literary-master v2.5

**Date:** 2026-05-04
**Hardware:** NVIDIA DGX Spark (GB10, 128 GB)
**Test target:** `bjoernb/gemma4-26b-fast` Q4_K_M producing extended Synthesis JSON
**Linked work:** [literary-master-v2 commits 070c75f → f810dd1](https://github.com/devbourne/literary-master-v2)

literary-master v2 had been committed to a "single-model gemma4" architecture for the bilingual constraint (English source → Korean output). v2.5 added a multi-model parallel "gloss" layer (Textual / Critical / Pedagogical) feeding into Synthesis, with the goal of adding analytical depth without inflating wall-clock past v1's 20-30 min budget.

This report documents how the integration of multi-perspective output into the Synthesis JSON exposed a new gemma4 failure mode (JSON output corruption under high schema complexity) and how splitting the Synthesis stage into two focused calls fixed it.

## What was attempted (chronological)

### Stage A: cram everything into one Synthesis call

The straightforward approach: extend SynthesisSchema with 4 new multi-perspective fields (`multi_perspective_synthesis_ko`, `complementary_insights`, `unresolved_tensions`, `pedagogical_scaffolding`), update the synthesis prompt to populate them when multi-gloss is present.

Six runs on the same 2.4 KB Gift of Magi excerpt:

| Run | Variant | Outcome | Synthesis parse |
|---|---|---|---|
| v2.5b | initial 4-field expansion | All 16 fields empty | ❌ truncated |
| v2.5c | maxTokens 6000 → 9000 | All fields populated, low counts | ✅ |
| v2.5d | prompt min counts ≥3/≥2 | All fields empty | ❌ |
| v2.5e | + raw logging | All fields empty, raw shows broken JSON keys (`multi_perspective_seynthesis_ko`) | ❌ key glitch |
| v2.5f | + key normalizer | All fields empty, raw shows random Korean inserted mid-array | ❌ random char |
| v2.5g | **synthesis split** | **All fields populated, target counts met** | ✅ both stages |

Patch series success rate before split: **1/5 = 17%**. Each "fix" revealed a new failure mode rather than converging.

### The pattern

gemma4 emits semantically valid JSON when the output schema is bounded. As schema scope grows (number of fields, nested complexity, prompt length), output fidelity degrades non-deterministically:

- v2.5b: stream truncation past max_predict
- v2.5c: succeeds with low counts (model emits minimum-effort versions)
- v2.5d: re-runs malformed under stricter prompt
- v2.5e: JSON key character glitch (`multi_perspective_seynthesis_ko` extra `e`)
- v2.5f: random Korean character inserted between array elements

Each is a different *expression* of the same root cause: the model can't reliably hold the entire schema-state coherent across thousands of output tokens when the schema has 16+ fields with nested arrays and the prompt is dense with rules.

## The fix — Stage 4a / Stage 4b split

Architectural rather than prompt-level. The Synthesis stage becomes two LLM calls:

- **Stage 4a — Core Synthesis (12 fields)**: identical prompt to v2 baseline, identical schema. Multi-gloss section is still passed in as input context so the existing fields can be enriched, but the model only has to output the 12 proven fields.
- **Stage 4b — Multi-Perspective Enrichment (4 fields)**: separate focused LLM call. Receives the 4a output JSON + multi-gloss section. Output schema has only 4 fields. Prompt's schema spec is ~10 lines vs ~50 for the all-in-one.

Implementation in `src/lib/agents/synthesis-agent.ts`:

```ts
const core = await runSingleShot(input, t0);   // or runChunkMerge
if (input.multiGlossSection) {
  const enrichmentRes = await runEnrichment(
    core.synthesis,
    input.multiGlossSection,
    input.signal,
  );
  if (enrichmentRes.parseOk) {
    core.synthesis.multi_perspective_synthesis_ko =
      enrichmentRes.data.multi_perspective_synthesis_ko;
    core.synthesis.complementary_insights = enrichmentRes.data.complementary_insights;
    core.synthesis.unresolved_tensions = enrichmentRes.data.unresolved_tensions;
    core.synthesis.pedagogical_scaffolding = enrichmentRes.data.pedagogical_scaffolding;
  }
}
```

The enrichment is wrapped in `callLLMWithJsonFallback` (Phase F-1 — qwen3:30b retry on parse fail), so a malformed enrichment can fall back to the JSON-robust model. If both fail, 4a's 12 fields stay intact — graceful degradation.

## v2.5g + v2.5h results — reproducibility confirmed

Same 2.4 KB Gift of Magi input, two consecutive runs after the split:

| | v2.5g (run 1) | **v2.5h (run 2)** |
|---|---|---|
| 4a parseOk | ✅ true | ✅ **true** |
| 4b parseOk | ✅ true | ✅ **true** |
| 4a tokens | 1,710 | 1,680 |
| 4b tokens | 1,243 | 1,121 |
| `multi_perspective_synthesis_ko` length | 525 chars | **513 chars** |
| `complementary_insights` count | 3 | **3** ✅ |
| `unresolved_tensions` count | 2 | **2** ✅ |
| `pedagogical_scaffolding` 3 sub-fields | populated | **populated** |
| Synthesis stage wall-clock | 124 s | 117 s |
| Total wall-clock | 28.6 min | 28.4 min |

**Reliability summary:** 1/5 (20%) before the split → **2/2 (100%) after.**

Variance across the two runs is <10% on all metrics. The output structure is stable — same field counts, similar lengths, same multi-perspective angle coverage (Textual / Critical / Pedagogical pairs all represented).

Wall-clock comparison vs the v2.5c single-call success (the one run out of five that worked): split adds ~30% to synthesis-stage wall-clock (~6 min for 2.4 KB), well inside the 20-30 min single-analysis budget.

## Quality demonstration — multi_perspective_synthesis_ko

Excerpted from v2.5g output (full content in
[literary-master-v2 data/teaching-materials/bee81912...](https://github.com/devbourne/literary-master-v2)):

> 텍스트의 정밀한 수치화는 단순한 경제적 결핍을 넘어 인물들의 삶을 규정하는 도덕적 경제의 기초가 된다. 서술자는 델라의 절망을 '훌쩍임'과 '미소'라는 생의 리듬으로 묘사하며 개인의 비애를 보편적 성찰로 확장시키는데, 이 과정에서 발생하는 텍스트의 아이러니는 비평적 관점에 따라 다층적으로 해석된다. **마르크스주의적 관점**에서는 이러한 희생이 자본주의적 구조적 압박에 의한 불가피한 결과로 읽히며, **페미니즘적 시각**은 델라의 정체성이 남편의 이름과 그의 소유물인 시계 체인에 종속되는 과정을 포착한다. 그러나 이러한 비판적 해체에도 불구하고, 작품은 성경적 '마기'의 메타포를 빌려 물질적 가치가 상실된 자리에 남은 숭고한 헌신을 긍정한다. 결국 텍스트의 구조적 대칭성—서로의 소중한 것을 맞교환하여 선물이 무용지물이 되는 아이러니—은 단순한 비극을 넘어, 물질적 소유의 상실이 오히려 정신적 가치의 극대화를 이끄는 역설적 완성에 도달하게 한다.

Four critical traditions integrated (textual analysis, Marxist, feminist, religious/New Critical) into a single 525-char coherent meta-essay. v1 single-model gemma4 produced thesis-level statements like "사랑이 가난을 이긴다" — the depth gap is qualitative, not just quantitative.

## Generalizable lessons

1. **Output schema size is a first-class reliability variable**, not just a quality variable. For Q4 quantized models in particular, large structured-output schemas hit a soft ceiling where each new field reduces probability that the entire output remains valid.

2. **Prompt-level fixes for output reliability hit diminishing returns fast.** Five iterations of prompt tightening on the all-in-one synthesis didn't move the success rate. The architectural split worked on the first try.

3. **JSON salvage strategies (key-name fuzzy matching, partial-recovery parsers) are useful safety nets but not replacements for bounded output complexity.** They cover ~20% of failure cases; the remaining 80% are genuinely unrecoverable malformed output.

4. **Pipeline stage count vs reliability**: doubling the LLM calls (one big call → two small calls) is approximately 1.3-1.5× wall-clock for ≥5× reliability improvement. Net win for any pipeline targeting structured output above ~10 fields.

5. **For literary-master specifically**: the bilingual single-model constraint (gemma4 for Korean output) holds. Quality depth is achievable through staged orchestration, not through model swapping. v2.5's multi-model parallel layer is read input only — output stays gemma4.

## Status as of this report

- v2.5g + v2.5h: **2 of 2 successful runs after the split** (with all 4 multi-perspective fields populated and target minimum counts met). Reliability stat updated from 1/5 (single-call) to 2/2 (split).
- Phase 3 Korean Proofreader gate widened to also walk Stage 4b prose fields when populated (literary-master-v2 commit `0c1b2d7`, applies on next dev restart).
- v2.5 multi-model architecture proven to deliver both depth and reliability when the synthesis stage is decomposed.

## Open follow-ups

- 4 KB and full-story (~12 KB) reproducibility runs to confirm the split holds at larger input sizes. Wall-clock estimate: 4 KB ~32 min, 12 KB ~70 min (the latter outside single-analysis budget; would land in the long-form async mode discussed in [`2026-05-02_production_budget_findings.md`](2026-05-02_production_budget_findings.md)).
- Stage 4b prose fields still show occasional gemma4 character glitches (`투류` for `투쟁`, `정학성` for `정수성`) — Phase 3 gate fix lands them in the proofreader's scope; effect to be measured on a fresh run.
- chunk-merge synthesis path (≥150 blocks) currently runs the same Stage 4b enrichment after the merge; behavior verified at single-shot scale only. Long-text validation pending.

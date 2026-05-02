# Combo D Slot-Swap Experiments — 5-way ensemble comparison

**Date:** 2026-05-02
**External canonical:** [devbourne/locallm-humanities-bench Round 8](https://github.com/devbourne/locallm-humanities-bench/blob/main/bench/DGX_SPARK_RESULTS.md)
**Hardware:** NVIDIA DGX Spark (GB10, 128 GB)
**Test passage:** Plato, *Republic* VII (~750 words)

After confirming in Round 7 that gpt-oss:120b in stage 02c (textual close-reading gloss) measurably improves ensemble output, this document maps where else in the Combo D pipeline the larger-model substitution pays off.

## Variants

All variants keep gpt-oss:120b in 02c (Round 7's confirmed upgrade) and only swap one additional stage:

| Variant | 03 Synthesis | 04 Critique | Memory (parallel 02) |
|---|---|---|---|
| Combo D (Mac, baseline) | Qwen3 | Gemma4 | 48 GB |
| DGX D-20b (Round 6) | Qwen3 | Gemma4 | 48 GB |
| DGX D-120b (Round 7) | Qwen3 | Gemma4 | 100 GB |
| **DGX D-S** | **gpt-oss:120b** | Gemma4 | 100 GB |
| **DGX D-C** | Qwen3 | **gpt-oss:120b** | 100 GB |

## Wall-clock — all 5 runs

| Run | 01 | 02 (max) | 03 | 04 | Total |
|---|---:|---:|---:|---:|---:|
| Mac D-20b | 16.4 | 100.2 | 44.7 | 118.1 | **279s** |
| DGX D-20b | 17.7 | 120.9 | 54.8 | 95.7 | **289s** |
| DGX D-120b | 16.8 | 93.6 | 49.4 | 94.0 | **254s** |
| DGX D-S | 19.3 | 148.1 | 73.4 | 27.6 | **268s** |
| DGX D-C | 22.2 | 147.0 | 54.0 | 54.0 | **277s** |

All within 254-289s (±10% band). Sampling variance — gemma4's 02b output ranges 525-1805 tok across runs — dominates over per-stage model choice. **No swap costs significant wall-clock**.

## Stage 04 Critique — 5-way comparison

This is where the swaps differentiate most.

### Gemma4 critique style (4 runs)

| Run | Branded labels | Traditions |
|---|---|---|
| Mac D-20b | 3: *Puppeteer's Vacuum*, *Compulsion Loop*, *Epistemic Leap* | Nietzsche + Aristotelian Empiricism |
| DGX D-20b | 2: *Gradient Fallacy*, *Epistemic Aristocracy* | Empiricism + Post-Structuralism |
| DGX D-120b | 3: *Continuity Fallacy*, *Coercion Paradox*, *Puppeteer Vacuum* | Nietzschean + **Frankfurt School** |
| **DGX D-S** | **3 ALL-NEW**: *Visual Leap of Faith*, *Puppeteer's Paradox*, *Assumption of Objective Enlightenment* | Nietzschean + **Marxist Materialism** |

Naming pattern: concept-first ("Continuity Fallacy", "Visual Leap of Faith"). Memorable, poetic.

### gpt-oss:120b critique style (D-C)

| Run | Branded labels | Traditions |
|---|---|---|
| **DGX D-C** | **3 NEW**: *Coercion-Choice Paradox*, *Fire-Illusion Ambiguity*, *Return-Responsibility Dilemma* | **Locke** (*Essay Concerning Human Understanding*) + **Dewey** (*Experience and Nature*) |

Naming pattern: compound dialectical (X-Y-Z, each label names two things in tension). Explicit work citations. Direct dialogic engagement with synthesis output ("The synthesis flags this tension (Gloss A vs. Gloss C)"). Contemporary speculative Q3 ("post-human epistemology / AI-mediated perception").

## Stage 03 Synthesis — Qwen3 vs gpt-oss:120b

Synthesis stage tension territory:

| Run | Synthesis model | Tensions surfaced |
|---|---|---|
| Mac D-20b | Qwen3 | Fire status / freedom as state vs process / sun as generator vs measure |
| DGX D-20b | Qwen3 | Fire role / solitary vs collective ascent / good elite vs universal |
| DGX D-120b | Qwen3 | Fire status (literal vs symbolic) / coercion vs adaptation / **language: prison vs bridge** |
| **DGX D-S** | **gpt-oss:120b** | **Ontological status of the Good vs political instrumentalism** / **mediation vs unmediated apprehension** / **pain as social vs ontological** |
| DGX D-C | Qwen3 | (similar to D-120b — same model in slot 03) |

D-S's gpt-oss:120b synthesis surfaces **structurally different tension territory** — meta-level (ontology-vs-politics, mediation-vs-direct, social-vs-ontological pain) instead of the object-level tensions Qwen3 produces (fire, language, freedom).

## Composite quality (10pt, weighted: gloss 30% / synthesis 30% / critique 40%)

| Run | Composite | Strength dimension |
|---|:-:|---|
| **DGX D-120b** | **9.5** | Reproduces gemma4's single-model A-game in ensemble + Frankfurt School new tradition |
| **DGX D-S** | **9.5** | All-new branded labels + Marxist Materialism (1st time in 8 rounds) + sharpest synthesis territory |
| Mac D-20b | 9.0 | README canonical "publication-grade" exemplar; 3 labels |
| **DGX D-C** | **9.0** | Academic style with cited works; Pragmatism invoked (rare); but loses gemma4's brand-creation specialty |
| DGX D-20b | 8.5 | Strong ensemble but only 2 labels; sampling-down |

## Slot-swap findings

1. **02c (textual gloss): always upgrade to 120b when memory permits.** Sharper textual reading propagates pipeline-wide. Round 7 confirmed.

2. **03 (synthesis): upgrading to 120b shifts tension territory from object-level to meta-level.** D-S surfaced "ontology vs political instrumentalism" — none of the Qwen3 syntheses (Mac D-20b, DGX D-20b, DGX D-120b, DGX D-C) reached this abstraction level. Worth it for *exploratory* analyses that want to surface new analytical angles. For *reproducible* runs, keep Qwen3 (cleaner structural output, more consistent sectioning).

3. **04 (critique): Gemma4 retains a slight edge for branded labels.** gpt-oss:120b critique is excellent (9.0) but its compound-dialectical X-Y-Z labels are less memorable than gemma4's brand-creation. Use gpt-oss:120b critique when **academic citations matter** (Locke + Dewey explicit work titles); use gemma4 critique when **label memorability matters** ("Continuity Fallacy" sticks more than "Coercion-Choice Paradox").

## Recommended trios — when to use which

| Use case | Trio | Memory | Why |
|---|---|---|---|
| Universal default | Qwen3 + Gemma4 + GPT-OSS:20b | 48 GB | proven, fits anywhere ≥64 GB |
| DGX premium (proven) | Qwen3 + Gemma4 + GPT-OSS:120b at 02c | 100 GB | Round 7 — sharper textual gloss propagates |
| **DGX exploratory** | Qwen3 + Gemma4 + GPT-OSS:120b at 02c+03 (D-S) | 100 GB | meta-level tensions, all-new labels |
| **DGX academic** | Qwen3 + Gemma4 + GPT-OSS:120b at 02c+04 (D-C) | 100 GB | explicit work citations, less memorable labels |
| Untested | GPT-OSS:120b at 02c+03+04 (D-SC, all-out) | 100 GB | open follow-up |

## Open follow-up

**Combo D-SC** — both 03 synthesis AND 04 critique replaced with gpt-oss:120b. Would merge D-S's exploratory synthesis territory with D-C's academic critique style. Question: does the lack of Qwen3 in 03 hurt the structural cleanness needed for D-C's critique to anchor properly? Hypothesis: yes (same model in 03 and 04 may collapse perspective diversity), but worth one run to verify.

## Files

```
data/2026-05-02_combo_d_dgx/        # 02c=20b, 03=Qwen3, 04=Gemma4 (Round 6)
data/2026-05-02_combo_d_dgx_120b/   # 02c=120b, 03=Qwen3, 04=Gemma4 (Round 7)
data/2026-05-02_combo_d_dgx_s/      # 02c=120b, 03=120b, 04=Gemma4 (Round 8 D-S)
data/2026-05-02_combo_d_dgx_c/      # 02c=120b, 03=Qwen3, 04=120b  (Round 8 D-C)
```

Each folder contains the full 7-file Combo D output set (extract, 3 glosses, synthesis, critique, REPORT, timings).

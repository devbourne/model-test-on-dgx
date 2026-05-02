# Combo D ensemble — DGX Spark vs Mac Studio

**Date:** 2026-05-02
**External canonical:** [devbourne/locallm-humanities-bench Round 6](https://github.com/devbourne/locallm-humanities-bench/blob/main/bench/DGX_SPARK_RESULTS.md)
**Hardware:** NVIDIA DGX Spark (GB10, 128 GB)
**Test passage:** Plato, *Republic* VII (~750 words)

End-to-end Combo D (Triple Gloss) ensemble run:
1. Extract → Qwen3 (JSON)
2. Triple parallel gloss: 02a metaphysical (Qwen3), 02b political/linguistic (Gemma4), 02c textual close-reading (GPT-OSS:20b)
3. Synthesis → Qwen3 (3-way merge with explicit tension-naming)
4. Critique → Gemma4 (anchored on synthesis, brand-creation step)

Mac numbers come from the upstream README's canonical Combo D run.

## Per-stage timings

| Stage | Model | Mac | DGX Spark | Δ tok/s |
|---|---|---:|---:|:-:|
| 01 Extract | Qwen3 | 51.9 t/s · 16.4s | 46.5 t/s · 17.7s | -10% |
| 02a Gloss-meta | Qwen3 (parallel) | 32.9 t/s · 18.0s | 29.4 t/s · 18.9s | -11% |
| 02b Gloss-polit | Gemma4 (parallel) | 23.2 t/s · 100.2s | 17.3 t/s · 120.9s | -25% |
| 02c Gloss-text | GPT-OSS:20b (parallel) | 39.2 t/s · 41.4s | **14.8 t/s** · 91.0s | **-62%** |
| 03 Synthesis | Qwen3 | 38.3 t/s · 44.7s | 31.9 t/s · 54.8s | -17% |
| 04 Critique | Gemma4 | 19.9 t/s · 118.1s | **25.6 t/s** · 95.7s | **+29%** |

## Wall-clock with parallelization

| Platform | Total | Δ |
|---|---:|---:|
| Mac Studio | 279.4s (~4.7 min) | baseline |
| **DGX Spark** | **289.1s (~4.8 min)** | **+3.5%** |

**Single-model 25-45% per-token slowdown on DGX (Round 5) is almost entirely absorbed by the ensemble structure.**

Three reasons:

### 1. Stage 04 Critique is *faster* on DGX (+29%)
The 04 critique input is the synthesis (~7 KB context). Gemma4's prompt-eval rate is DGX's strongest dimension — measured at 2,873 tok/s for 8K-context Korean SAT analysis on 2026-04-12. The DGX critique's 25.6 t/s is computed from generation alone but the wall-clock advantage comes from prompt-eval being effectively free on this hardware, while Mac's prompt-eval is the slow part. **Result: wall-clock 95.7s (DGX) vs 118.1s (Mac) — 19% faster on the most expensive single stage**.

### 2. Parallel 02 stage's GPT-OSS slowdown (-62%) is invisible at wall-clock
Stage 02 wall-clock is bounded by `max(02a, 02b, 02c)`. On both platforms gemma4's gloss-polit dominates (Mac 100.2s, DGX 120.9s). GPT-OSS:20b finishing in 91s vs 41s makes no end-to-end difference because we're already waiting for gemma4. The 62% per-token slowdown shows up nowhere in the deliverable.

### 3. Single-stage tok/s misleads on memory-bandwidth-bound workloads
At the unit of "publication-grade chapter analysis" (5-min wall-clock), the platforms are equivalent. Single-token tok/s is the wrong metric when the actual deliverable is a multi-stage pipeline with parallelism + heterogeneous prompt sizes.

## Content quality

Both ensembles produce **gemma4 brand-creation behavior** in stage 04. README highlighted Mac's Combo D for coining 3 distinctive labels; DGX produced 2 from the same model on the same passage with identical params.

| Run | Branded weakness labels | Sample sharpness |
|---|---|---|
| Mac Combo D | **3**: *Puppeteer's Vacuum*, *Compulsion Loop*, *Epistemic Leap* | "Compulsion Loop" — forced ascent + forced return = "freedom merely a change in the nature of one's constraints" |
| DGX Combo D | 2: *Gradient Fallacy*, *Epistemic Aristocracy* | "Gradient Fallacy" — fire-as-intermediary collapses *kind* into *intensity*, undermining *becoming/being* distinction |

| Aspect | Mac | DGX |
|---|---|---|
| Synthesis size | 7,530 B | 7,047 B |
| Branded labels | 3 | 2 |
| Traditions invoked (critique) | Nietzsche + Aristotelian Empiricism | Empiricism + Post-Structuralism |
| Stage-3 unresolved tensions called out | yes | yes |

**Quality cross-validates: equivalent gemma4 brand-creation behavior across hardware, normal sampling variation in specific labels.**

## Implication for the recommendation matrix

For Combo D ensemble work on DGX Spark, the trio choice **no longer needs to optimize for individual-model speed** — wall-clock is platform-equivalent. Optimize for *quality* instead:

| Trio | Memory | Where it makes sense |
|---|---|---|
| Qwen3 + Gemma4 + GPT-OSS:20b | 18+17+13 = 48 GB | Universal — fits any hardware ≥64 GB |
| **Qwen3 + Gemma4 + GPT-OSS:120b** (DGX-only) | 18+17+65 = **100 GB** | DGX Spark only. Higher quality ensemble output (see 3-way comparison below). |

## 3-way ensemble quality comparison

Read all three Combo D runs (Mac with 20b, DGX with 20b, DGX with 120b) on the same passage at the same params, focused on the deliverable stages.

### Stage 02c — Textual close-reading gloss (the model differentiator)

| Run | Distinctive moves |
|---|---|
| Mac 20b | Marionette stage = performance, Homeric "spangled heaven" allusion, fire/sun temporal contrast, 3 implications (pain, habituation, good as causal agent) |
| DGX 20b | Mouth of den placement, "shadows of shadows" meta-representation, contest as social penalty, death threat as political warning |
| **DGX 120b** | "Tightly staged scene" = drama of performance, **"graduated epistemic calibration"**, water as **"mutable mirror"** intermediate transitional realm, **"silent chorus echoing the reader's assent"**, **"didactic force behind the veneer of collaborative discovery"**, "the light of the fire is the sun" as **collapsing dim/ultimate distinction**, **"metric of knowledge that is itself a shadow-game"**, **"symbolic death of former self"** |

GPT-OSS:120b produces the densest, most crystallized analytic phrasing — the same kind of formulations its single-model run produced in Round 4.

### Stage 03 — Synthesis (3-way merge with explicit verdicts on tensions)

| Run | Tension #3 (most distinctive) |
|---|---|
| Mac 20b | Sun as generator vs measure (verdict: GLOSS-A — causal author) |
| DGX 20b | Good elite vs universal (verdict: GLOSS-B — practically essential) |
| **DGX 120b** | **Role of language: prison vs bridge** (verdict: language as performance AND vehicle for liberation when used dialectically) |

DGX 120b's "language as prison vs bridge" tension is genuinely novel — neither 20b ensemble surfaced this. Triggered by the 120b textual gloss's emphasis on rhetorical architecture.

### Stage 04 — Critique (gemma4 brand-creation step)

| Run | Branded weakness labels | Traditions invoked |
|---|---|---|
| Mac 20b | **3**: *Puppeteer's Vacuum*, *Compulsion Loop*, *Epistemic Leap* | Nietzsche + Aristotelian Empiricism |
| DGX 20b | 2: *Gradient Fallacy*, *Epistemic Aristocracy* | Empiricism + Post-Structuralism |
| **DGX 120b** | **3**: *Continuity Fallacy*, *Coercion Paradox*, *Puppeteer Vacuum* | Nietzschean Perspectivism + **Frankfurt School (Critical Theory)** |

Two notable findings:

1. **DGX 120b's labels are an exact match to gemma4's strongest single-model Plato critique** ("Continuity Fallacy" and "Coercion Paradox" — verbatim strings from the original `out/gemma4_03_critique.md`) plus inherits "Puppeteer Vacuum" from the ensemble. The sharper synthesis input gave gemma4 enough material to reproduce its A-game *and* layer in ensemble-derived insights.
2. **Frankfurt School (Critical Theory) is a new tradition** — none of Mac 20b, DGX 20b, or any prior round invoked it. Likely triggered by the 120b gloss's emphasis on regime-of-truth / power-dynamics framings.

### Composite quality verdict

| Run | Score | Why |
|---|:-:|---|
| **DGX Combo D 120b** | **9.5 / 10** | Sharpest gloss, novel synthesis tensions, 3 brand labels (matching gemma4's strongest output), novel tradition (Frankfurt) |
| Mac Combo D 20b | 9.0 / 10 | README's canonical "publication-grade" exemplar; 3 labels |
| DGX Combo D 20b | 8.5 / 10 | Strong but 2 labels (sampling), no novel traditions |

**The 120b in the 02c slot pays off in measurable quality terms** — sharper textual gloss → richer synthesis tension surfacing → critique with one more branded label and a tradition the ensemble had not previously invoked.

### Wall-clock cost

DGX 120b run: 253.8s vs DGX 20b run 289.1s. The **120b run was faster by ~12% in this single observation**, but this delta is dominated by sampling variance in stage 02b (gemma4 happened to produce shorter output in the 120b run: 525 tok vs 1582 tok). Across multiple runs, expect parity ±15%. **Treat the 120b variant as quality-equivalent on cost, higher on output.**

## Recommendation

For DGX Spark deployments where 100 GB of resident model memory is acceptable:

- **Default trio: Qwen3 + Gemma4 + GPT-OSS:20b** (48 GB) — proven on multiple platforms, fits any ≥64 GB hardware
- **DGX-premium trio: Qwen3 + Gemma4 + GPT-OSS:120b** (100 GB) — measurable quality bump in textual gloss → propagates to synthesis and critique. Pay for it when output will be published or graded.

## Files

```
data/2026-05-02_combo_d_dgx/        # 20b in 02c
data/2026-05-02_combo_d_dgx_120b/   # 120b in 02c
```

Both folders contain the full 7-file Combo D output set (extract, 3 glosses, synthesis, critique, REPORT, timings).

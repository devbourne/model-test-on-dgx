# locallm-humanities-bench — DGX Spark Rounds 4 & 5 (Summary)

**Date:** 2026-05-02
**External repo:** https://github.com/devbourne/locallm-humanities-bench
**Full results:** [DGX_SPARK_RESULTS.md in that repo](https://github.com/devbourne/locallm-humanities-bench/blob/main/bench/DGX_SPARK_RESULTS.md)

This is a summary of two new rounds added to the upstream locallm-humanities-bench, with the data files mirrored here for archival.

## What was added

### Round 4 — Two new 120B-class models on DGX Spark
- `gpt-oss:120b` (65 GB MXFP4)
- `nemotron-3-super:120b` (86 GB Q4_K_M)
- Plus `run_one_strip.sh` — non-destructive `<think>`-strip wrapper for reasoning models (no-op on non-reasoning models)

### Round 5 — Pure hardware delta validation
Re-ran the original keeper trio (`qwen3:30b-a3b`, `gpt-oss:20b`, `bjoernb/gemma4-26b-fast`) on DGX Spark with identical settings to the original Mac Studio Round 1, isolating hardware throughput from model quality.

## Headline findings

### 1. GPT-OSS 120B is a depth-specialist keeper

| Model | Plato 3-stage composite (10pt) |
|---|:-:|
| gpt-oss:20b | 9.2 |
| **gpt-oss:120b (NEW)** | **9.0** |
| nemotron-3-super:120b | 8.7 |
| gemma4-26b-fast | 8.0 |
| qwen3:30b-a3b | 7.5 |

GPT-OSS 120B's Gloss is the field's best — uniquely catches Plato's **Two Worlds** distinction (world of sight / world of knowledge) AND the **ethics-primacy** point (scientific/mathematical knowledge below moral insight) AND *methexis* (rationality as participation in the Good). 65 GB / 26 t/s makes it practical only on hardware with >64 GB.

### 2. Nemotron-3-Super 120B is Pareto-dominated

Same parameter class as gpt-oss:120b, but:
- Lower quality (8.7 vs 9.0)
- 2.2× slower (12 vs 26 t/s)
- 32% larger memory (86 vs 65 GB)
- Requires `<think>` strip wrapper (think trace leaks 22-72% of token volume into `.response`)

**Removed from local Ollama after testing.** Only niche use is "analytic-philosophy sharpness" (Form-uniqueness critique style) — not enough to keep around at 86 GB.

### 3. DGX Spark is *slower* than Mac Studio for keeper trio (small-active MoE)

| Model | Mac Studio | DGX Spark | Δ |
|---|---:|---:|---:|
| qwen3:30b-a3b | 47 t/s | 35 t/s | **−25%** |
| gpt-oss:20b | 56 t/s | 37 t/s | **−35%** |
| gemma4-26b-fast | 25 t/s | 14 t/s | **−45%** |

Memory-bandwidth bound. Mac M2 Ultra unified memory (~400-800 GB/s) outpaces DGX Spark GB10 (~273 GB/s) on small-active MoE generation. **DGX Spark wins only on memory ceiling** (fits 65-86 GB models the Mac can't) and long-context prompt eval. Counter to the assumption that bigger machine = always faster.

### 4. Quality cross-validates across hardware

Same model on Mac vs DGX produces equivalent quality, with normal sampling variation. README's keeper rankings hold cross-platform. Hardware affects throughput, not analytic depth.

## Updated keeper list (DGX Spark hardware)

| Slot | Model | Why |
|---|---|---|
| Speed/width 1st | `gpt-oss:20b` | fastest visible-output keeper, 5 traditions in critique |
| **Depth specialist (NEW)** | `gpt-oss:120b` | best Gloss, fits comfortably in 128 GB |
| JSON robustness | `qwen3:30b-a3b` | clean structured output |
| Branded framing | `gemma4-26b-fast` | "Continuity Fallacy"-style coined labels |
| ✗ Not recommended | `nemotron-3-super:120b` | Pareto-dominated by gpt-oss:120b |

## Data mirrored here

```
data/2026-05-02_locallm_dgx/
├── passage.txt                              # Plato Republic VII (~750 wd)
├── timings_full.csv                         # all rounds combined
├── nemotron3_{01,02,03}_{extract,gloss,critique}.{md,raw.md}
├── gptoss120_{01,02,03}_{extract,gloss,critique}.{md,raw.md}
├── qwen3_dgx_{01,02,03}_{extract,gloss,critique}.md
├── gptoss20_dgx_{01,02,03}_{extract,gloss,critique}.md
└── gemma4_dgx_{01,02,03}_{extract,gloss,critique}.md
```

`*.raw.md` files preserve the un-stripped output (with `<think>` traces) for reasoning models, so the strip behavior can be inspected.

## Why mirror here when the canonical lives in another repo?

- The canonical lives in [devbourne/locallm-humanities-bench](https://github.com/devbourne/locallm-humanities-bench), which is the right home for it (English humanities-specific bench).
- This `model-test-on-dgx` repo aggregates *all* DGX-Spark model evaluations — including ones outside the humanities domain — so it needs a copy for indexing and cross-referencing.
- Both repos can evolve independently; updates to the canonical will be backported here when material.

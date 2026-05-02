# model-test-on-dgx

Consolidated repository of LLM evaluation experiments run on **NVIDIA DGX Spark** (GB10 Grace Blackwell Superchip, 128 GB LPDDR5X unified memory, ~273 GB/s).

These tests originated as ad-hoc benchmarks scattered across separate project repos (literary-master, structural-labeling, locallm-humanities-bench, etc.). This repo collects them into one place so that:
- Results stay comparable across experiments (same hardware, documented methodology)
- Future tests can reference and extend prior findings
- A single git history records the evolution of which models we keep and why

## Hardware

| Item | Spec |
|---|---|
| Machine | NVIDIA DGX Spark |
| SoC | GB10 Grace Blackwell Superchip |
| Memory | 128 GB LPDDR5X unified |
| Bandwidth | ~273 GB/s |
| Driver | 580.126.09 / CUDA 13.0 |
| Architecture | aarch64 |

## Reports (chronological)

| Date | Report | What it tests |
|---|---|---|
| 2026-02-28 | [5model_baseline](reports/2026-02-28_5model_baseline.md) | Korean SAT analysis, 5 models (gemma3, qwen3, gpt-oss-120b, mistral-large, deepseek-r1) — Ollama 0.17.4 baseline |
| 2026-03-02 | [structural_role_qlora](reports/2026-03-02_structural_role_qlora.md) | Sentence-level structural role labeling — QLoRA vs prompt-tuning vs few-shot |
| 2026-04-12 | [ollama_3model_bench](reports/2026-04-12_ollama_3model_bench.md) | gemma4-26b-fast emerges; 3-way Korean tasks |
| 2026-04-18 | [qwen36_vllm_bench](reports/2026-04-18_qwen36_vllm_bench.md) | Qwen3.6-35B-A3B-FP8 on vLLM — first cross-runtime test |
| 2026-04-18 | [literary_irony_3config](reports/2026-04-18_literary_irony_3config.md) | Literary irony interpretation — gemma4 / Qwen3.6 / Hybrid pipeline configurations |
| 2026-05-02 | [locallm_humanities_dgx](reports/2026-05-02_locallm_humanities_dgx.md) | English humanities pipeline (Plato, Sandel) — Rounds 4+5 of [devbourne/locallm-humanities-bench](https://github.com/devbourne/locallm-humanities-bench) |
| 2026-05-02 | [gptoss20_vs_gemma4_multiaxis](reports/2026-05-02_gptoss20_vs_gemma4_multiaxis.md) | Direct head-to-head: gpt-oss:20b vs gemma4-26b-fast across 4 task axes |

## Data layout

```
data/
├── 2026-03-02_structural_role_qlora/   # eval scripts + per-model JSON results
├── 2026-04-12/                          # prompts (capital, suneung, creative) + raw_api JSON + formatted outputs
├── 2026-05-02_locallm_dgx/              # extract/gloss/critique outputs for nemotron3, gptoss120, qwen3, gptoss20, gemma4 + Plato passage
└── 2026-05-02_gptoss20_multiaxis/       # gpt-oss:20b on capital/suneung/creative
```

## Scripts

- `scripts/run_one.sh` — generic single-model 3-stage pipeline (used by [locallm-humanities-bench](https://github.com/devbourne/locallm-humanities-bench))
- `scripts/run_one_strip.sh` — non-destructive variant that strips `<think>` traces (for reasoning models like nemotron-3-super, magistral)
- `scripts/run_gptoss20_compare.sh` — multi-prompt driver for the 2026-05-02 multi-axis test

## Methodology baseline

Unless a specific report says otherwise:
- **Runtime**: Ollama on `localhost:11434`
- **Sampler**: `temperature=0.3`, `num_ctx=8192`
- **API**: `/api/generate` with `stream:false`, raw JSON saved per call
- **Stages saved**: each output preserved as both raw JSON (`raw_api/`) and rendered Markdown
- **Hardware delta**: cross-platform comparisons explicitly note Mac Studio (M2 Ultra ~400-800 GB/s) vs DGX Spark (~273 GB/s) since memory bandwidth dominates throughput for small-active MoE models

## Current keepers (as of 2026-05-02)

| Slot | Model | Memory | Notes |
|---|---|---|---|
| Speed/width 1st | `gpt-oss:20b` | 13 GB | Best for English humanities pipeline width; **fails on highly constrained Korean/creative writing** |
| Korean tasks | `bjoernb/gemma4-26b-fast` | 17 GB | Best Korean naturalness + factual accuracy + instruction adherence (-ly avoidance, word count, banned-word compliance) |
| Depth specialist | `gpt-oss:120b` | 65 GB | Best Gloss in English humanities; only fits on DGX Spark (>64 GB requirement) |
| JSON robustness | `qwen3:30b-a3b-instruct-2507-q4_K_M` | 18 GB | Cleanest structured output, lowest variance |
| Tool calling | `Qwen/Qwen3.6-35B-A3B-FP8` (vLLM) | 34 GB | Native tool-calling support, but Korean text shows hanja contamination |
| ✗ Eliminated | `nemotron-3-super:120b` | 86 GB | Pareto-dominated by gpt-oss:120b (lower quality, 2.2× slower, 32% larger) |
| ✗ Eliminated | `gemma3:27b`, `magistral:24b`, `mistral-large:123b`, `deepseek-r1:70b` | — | See historical reports |

See [2026-05-02_gptoss20_vs_gemma4_multiaxis.md](reports/2026-05-02_gptoss20_vs_gemma4_multiaxis.md) for the most recent verdict.

## Convention for new reports

- File naming: `YYYY-MM-DD_short_topic.md`
- Always record: hardware, runtime version, model tags+sizes, prompt source, full timings (eval_count, total_duration, eval_duration, prompt_eval_count), per-stage outputs
- Keep raw API responses — model behavior changes with Ollama version updates and we want to be able to retroactively diagnose
- Cross-link related prior reports

## Related external repos

- [devbourne/locallm-humanities-bench](https://github.com/devbourne/locallm-humanities-bench) — English humanities multi-agent ensemble bench. DGX Spark cross-validation lives there as `bench/DGX_SPARK_RESULTS.md` (Rounds 4+5).

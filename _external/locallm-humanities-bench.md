# External: locallm-humanities-bench

**Repo:** https://github.com/devbourne/locallm-humanities-bench

English humanities-specific multi-agent ensemble benchmark. Runs Extract → Gloss → Critique on philosophical / social-science chapters using local LLMs, with single-model and multi-agent ensemble (Combo B / Combo D) configurations.

## Our contributions there

- **Round 4** (commit `466b710`): added `gpt-oss:120b` and `nemotron-3-super:120b` test results, plus `run_one_strip.sh` think-trace wrapper
- **Round 5** (commit `05c7e98`): cross-platform validation — re-ran original keeper trio on DGX Spark to isolate hardware delta from model quality

Full DGX Spark write-up: [bench/DGX_SPARK_RESULTS.md](https://github.com/devbourne/locallm-humanities-bench/blob/main/bench/DGX_SPARK_RESULTS.md)

Local mirror summary: [reports/2026-05-02_locallm_humanities_dgx.md](../reports/2026-05-02_locallm_humanities_dgx.md)

## Why it stays separate

- It's a domain-specific benchmark (English humanities, philosophical texts) that other people may want to fork independently of our DGX-aggregator
- The original maintainer convention (`bench/README.md` style) is well-established
- We push improvements upstream rather than vendor it

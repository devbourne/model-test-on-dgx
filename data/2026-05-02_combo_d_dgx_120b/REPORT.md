# Multi-Agent Ensemble Run — Combo D (Triple Gloss)

## Pipeline
1. Extract (Qwen3) → `01_extract.json`
2a. Gloss metaphysical (Qwen3, parallel) → `02a_gloss_qwen3.md`
2b. Gloss political/linguistic (Gemma4, parallel) → `02b_gloss_gemma4.md`
2c. Gloss textual close-reading (GPT-OSS, parallel) → `02c_gloss_gptoss.md`
3. Synthesis (Qwen3) → `03_synthesis.md`
4. Critique (Gemma4) → `04_critique.md`

## Timings

```
stage,model,eval_count,total_s,tok_per_s
01_extract,qwen3:30b-a3b-instruct-2507-q4_K_M,518,16.8,34.9
02a_gloss_meta,qwen3:30b-a3b-instruct-2507-q4_K_M,559,24.1,28.0
02b_gloss_polit,bjoernb/gemma4-26b-fast:latest,525,53.5,16.7
02c_gloss_text,gpt-oss:120b,1039,93.6,24.4
03_synthesis,qwen3:30b-a3b-instruct-2507-q4_K_M,1393,49.4,31.4
04_critique,bjoernb/gemma4-26b-fast:latest,2244,94.0,25.9
```

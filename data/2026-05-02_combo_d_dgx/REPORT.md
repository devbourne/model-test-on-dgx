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
01_extract,qwen3:30b-a3b-instruct-2507-q4_K_M,482,17.7,46.5
02a_gloss_meta,qwen3:30b-a3b-instruct-2507-q4_K_M,488,18.9,29.4
02c_gloss_text,gpt-oss:20b,1154,91.0,14.8
02b_gloss_polit,bjoernb/gemma4-26b-fast:latest,1582,120.9,17.3
03_synthesis,qwen3:30b-a3b-instruct-2507-q4_K_M,1568,54.8,31.9
04_critique,bjoernb/gemma4-26b-fast:latest,2246,95.7,25.6
```

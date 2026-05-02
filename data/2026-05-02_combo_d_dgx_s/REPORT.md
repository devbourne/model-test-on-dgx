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
01_extract,qwen3:30b-a3b-instruct-2507-q4_K_M,483,19.3,44.8
02a_gloss_meta,qwen3:30b-a3b-instruct-2507-q4_K_M,500,19.4,30.5
02c_gloss_text,gpt-oss:120b,1089,122.4,12.3
02b_gloss_polit,bjoernb/gemma4-26b-fast:latest,1685,148.1,16.5
03_synthesis,gpt-oss:120b,1604,73.4,25.1
04_critique,bjoernb/gemma4-26b-fast:latest,695,27.6,30.9
```

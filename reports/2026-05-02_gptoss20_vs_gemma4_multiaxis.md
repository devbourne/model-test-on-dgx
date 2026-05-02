# gpt-oss:20b vs gemma4-26b-fast — Multi-axis Head-to-Head

**Date:** 2026-05-02
**Hardware:** NVIDIA DGX Spark (GB10, 128 GB)
**Runtime:** Ollama 0.21.0+
**Settings:** `temperature=0.3`, `num_ctx=8192`

## Why this comparison

Earlier rounds settled on `bjoernb/gemma4-26b-fast` as the literary-master default. The locallm-humanities-bench round (English Plato passage) suggested `gpt-oss:20b` was the keeper there — yet we hadn't directly compared the two on Korean tasks the literary-master pipeline actually runs. This report fills that gap across four axes:

1. Korean short answer (factual accuracy)
2. Korean SAT-style English reading analysis (8-item rubric in Korean)
3. English constrained creative writing (9-point compliance)
4. English humanities analysis pipeline (Extract → Gloss → Critique on Plato)

Plus speed and memory.

## Models

| Model | Tag | Size | Arch | Quant |
|---|---|---|---|---|
| gpt-oss 20B | `gpt-oss:20b` | 13 GB | MoE | MXFP4 |
| Gemma4 26B fast | `bjoernb/gemma4-26b-fast:latest` | 17 GB | MoE A4B (25.8B) | Q4_K_M |

Memory edge: gpt-oss:20b 24% smaller (13 vs 17 GB).

## Speed across tasks (DGX Spark, identical params)

| Task | Prompt size | gpt-oss:20b | gemma4-26b-fast | Winner |
|---|---|---:|---:|---|
| Korean capital (3-sentence factual) | ~30 tok | 33.7 t/s · 12.8s | 64.1 t/s · 17.8s | **gemma4** (≈2× tok/s) |
| Korean SAT 8-item analysis | ~290 tok | 14.6 t/s · 123.6s | 62.1 t/s · 33.7s | **gemma4** (≈4× tok/s, 3.7× total) |
| English creative (500 wd, 9 constraints) | ~280 tok | **TIMEOUT** (>10 min, 0 visible tok produced) | 56.0 t/s · ~80s · 491 wd | **gemma4** (gpt-oss failed entirely) |
| English humanities Extract (Plato) | ~960 tok | 37.1 t/s · 37.9s | 14.2 t/s · 57.3s | **gpt-oss:20b** (≈2.5× tok/s) |
| English humanities Gloss (Plato) | ~1200 tok | 36.8 t/s · 27.7s | 14.1 t/s · 38.8s | **gpt-oss:20b** |
| English humanities Critique (Plato) | ~1500 tok | 35.6 t/s · 125.2s* | 14.5 t/s · 42.4s | **gpt-oss:20b** on visible content; eval_count inflated |

\* gpt-oss:20b stage 3 reported 4181 eval tokens but visible response is ~600 tokens. Harmony-format internal thinking is being counted in `eval_count` by the current Ollama. Visible-content tok/s is much lower than reported 35.6.

**Pattern**: speed flips by task. gemma4 is 2-4× faster on Korean tasks; gpt-oss:20b is 2.5× faster on English humanities. Same hardware, same params — the difference is **prompt language and task structure interacting with each model's internal token economy**.

## Quality

### Axis 1 — Korean short answer (capital of Korea)

**gpt-oss:20b** ([data](../data/2026-05-02_gptoss20_multiaxis/gpt-oss-20b_capital.md)):
> 서울은 삼국시대에는 작은 어촌이었으나, **10세기 고구려의 수도였던 개성의 유산을 이어받아** 고려시대에 수도가 옮겨졌고…

**Two factual errors**:
1. Goguryeo's capital was **Pyongyang** (not 개성/Kaesong)
2. Seoul as "어촌 (fishing village)" during 삼국시대 is misleading — it was a contested strategic location (한성, capital of early Baekje)

**gemma4** ([data](../data/2026-04-12/korean_suneung/gemma4-26b-fast_capital.md)):
> 조선 왕조가 건국된 1394년, 한양(현재의 서울)이 국가의 중심지로 지정… 한강을 끼고 있는 지리적 이점…

Clean, accurate, no factual errors.

**Verdict — gemma4 wins on Korean factual accuracy.** This matters for any literary-master deployment that handles Korean source material with historical context.

### Axis 2 — Korean SAT analysis (8 items in Korean about a digital-platforms passage)

Both models produced all 8 items. Direct rubric comparison:

| Item | gpt-oss:20b | gemma4 |
|---|---|---|
| 1. 주제 (one sentence) | ✅ accurate | ✅ accurate |
| 2. 요지 (one sentence) | ✅ accurate, slightly wordier | ✅ accurate |
| 3. 제목 2개 | Korean only | **Both English + Korean** (수능 출제 관점에서 더 유용) |
| 4. 논리 구조 | 8단계 표 (most granular) | 5단계 (cleaner narrative) |
| 5. 핵심 어휘 10개 | accurate, original phrasing | accurate, original phrasing |
| 6. 빈칸 추론 2개 | original-text quote ✅ | original-text quote ✅ |
| 7. 선지 함정 3개 | listed but not labeled by type | **Typology-labeled**: 범위 오류 / 인과관계 역전 / 내용 왜곡 |
| 8. 한 줄 요약 | ✅ | ✅ |

**Verdict — gemma4 wins narrowly.** Both achieve the 5/5 threshold but gemma4 has two task-design wins: bilingual title presentation (matches actual 수능 출제 format) and **typological labeling of distractor traps** (more usable for downstream test-prep generation).

### Axis 3 — English constrained creative writing (500 wd, 9 craft constraints)

Constraints recap: literary SF, melancholy tone, Ines (72 yo), 2147 lighthouse, 40-yr-old ship Morse signal, *in medias res* sensory opening, exactly one 2-3 sentence flashback, ambiguous ending, banned words (hope/beacon/echo/ghost), ≥2 marine biology metaphors, avoid -ly adverbs, exactly 500 words ±10.

**gpt-oss:20b**:
- Run 1 (think enabled): 7+ minute hang, **30,664 chars of thinking, zero visible response tokens**, request returned with `done: false`
- Run 2 (think disabled, `think:false`): curl `--max-time 600` reached without response, JSON file empty
- **Total failure on this axis** ([raw](../data/2026-05-02_gptoss20_multiaxis/gpt-oss-20b_creative.json), [no-think attempt](../data/2026-05-02_gptoss20_multiaxis/gpt-oss-20b_creative_nothink.json))

**gemma4** ([data](../data/2026-04-12/creative_story/gemma4-26b-fast.md)): Produced a complete 491-word literary SF story.
- Word count: 491 ✅
- Banned words: avoided ✅
- Sensory opening: "The copper tang of old battery acid coated Ines's tongue" ✅
- Flashback: 3 sentences (acid-etched tides → lighthouse refuge → solitude) ✅
- Marine biology metaphors: "marine snow drifting through the bathypelagic zone", "bioluminescent flash in a lightless trench" ✅✅
- Ambiguous ending: pale undulating light dissolving into silt ✅
- -ly adverbs: not zero but minimal
- **Compliance: 7/9 (locked in 2026-04-12 evaluation)**

**Verdict — gemma4 absolute win.** gpt-oss:20b's reasoning loop on a 9-constraint task is a hard failure mode worth documenting. Either gpt-oss:20b cannot satisfy all constraints simultaneously without exhausting its thinking budget, or the harmony-format generation gets stuck in self-correction loops on tightly constrained outputs. Either way, **do not use gpt-oss:20b for highly constrained creative tasks**.

### Axis 4 — English humanities pipeline (Plato Allegory of the Cave, locallm-bench rubric)

Detailed scoring in [2026-05-02_locallm_humanities_dgx.md](2026-05-02_locallm_humanities_dgx.md). Summary:

| Stage | gpt-oss:20b | gemma4 |
|---|:-:|:-:|
| Extract (JSON granularity) | 9 (8 concepts) | 7 (4 concepts) |
| Gloss (semantic depth) | 9 (wall+puppeteers as media intermediaries) | 9 (*periagoge*, *episteme*, Plato direct quote) |
| Critique (analytic sharpness + breadth) | 9.5 (5 traditions, fire/Good ambiguity catch) | 8 (2 traditions, "Continuity Fallacy"/"Coercion Paradox" branded labels) |
| **Composite** | **9.2** | **8.0** |

**Verdict — gpt-oss:20b wins, with gemma4 holding the "branded framing" niche.**

## Composite verdict

| Axis | Winner | Margin |
|---|---|---|
| Korean factual accuracy | **gemma4** | hard win (gpt-oss errors are wrong, not just less detailed) |
| Korean SAT analysis | **gemma4** | narrow (both 5/5 on rubric; gemma4 has two design wins) |
| English constrained creative | **gemma4** | absolute (gpt-oss:20b cannot complete the task) |
| English humanities pipeline | **gpt-oss:20b** | clear (9.2 vs 8.0) |
| Speed (Korean tasks) | **gemma4** | 2-4× tok/s |
| Speed (English humanities) | **gpt-oss:20b** | 2.5× tok/s |
| Memory footprint | **gpt-oss:20b** | 13 vs 17 GB (24% smaller) |

**Overall**: This is **not a single-winner comparison**. The two models are complementary specialists.

### When to pick gemma4-26b-fast
- Korean source material (factual, analytical, or generative)
- English creative writing with explicit constraints (word counts, banned words, structural rules)
- Long-context prompt evaluation (separate measurement: 2,873 tok/s prompt eval at 8K context)
- When you need *typological labeling* (gemma4's 함정 분류 / "Continuity Fallacy" framings — it likes inventing names for things)
- Default for literary-master pipelines

### When to pick gpt-oss:20b
- English philosophical/humanities analysis where critique breadth (multiple traditions) matters
- When width-first analytical passes are the goal — empiricism + pragmatism + Nietzsche + phenomenology + post-structuralism in one critique
- When 13 GB footprint matters (smaller, fits more parallel models)
- *Not* for: Korean tasks, constrained creative writing, factual claims about non-English history

### Why we missed gpt-oss:20b earlier
The 2026-04-12 ollama bench tested `gpt-oss:120b` (65 GB), not `gpt-oss:20b` (13 GB). On 5/5-saturated Korean rubrics, the larger model's depth advantage doesn't show, and the 65 GB model excludes itself from anyone with <128 GB. Adding gpt-oss:20b retroactively as a Korean candidate exposes the **factual accuracy regression vs gemma4** that the larger model didn't show — likely because the smaller MXFP4 quant has weaker Korean historical knowledge.

## Methodological notes

### Speed asymmetry across task languages

Same model, same hardware, same `num_ctx`, drastically different tok/s:
- gpt-oss:20b: 36 t/s on English Plato vs 14-33 t/s on Korean
- gemma4: 14 t/s on English Plato (with `temperature=0.3`, our run today) vs 62 t/s on Korean (2026-04-12)

The Korean SAT prompt has English passage embedded but Korean instruction wrap, requiring multi-script tokenization. Why gpt-oss slows so much more than gemma4 on Korean is open — possibly tokenizer-vocabulary efficiency for Korean glyphs, or harmony-format overhead per non-English generation.

### gpt-oss:20b reasoning loop on constrained creative

The thinking trace shows the model methodically working through each constraint before generating. With 9 constraints, the reasoning expanded to >7,500 tokens *before any visible output*, exceeding what either Ollama or the model itself could complete within reasonable time. Setting `think:false` did not resolve the issue (10 minute curl timeout on retry). The harmony format may not cleanly support pure non-thinking output for highly-constrained creative tasks. **This is a real production-blocking issue for any pipeline that includes such tasks.**

### Cross-platform speed delta context

For both models, DGX Spark is *slower* than Mac Studio per-token (memory bandwidth: ~273 vs ~400-800 GB/s). DGX wins on memory ceiling (fits 65-86 GB models) and long-context prompt eval. See [locallm_humanities_dgx Round 5](2026-05-02_locallm_humanities_dgx.md) for the cross-platform numbers.

## Recommendation for literary-master

Stay with `bjoernb/gemma4-26b-fast` as default. Do **not** swap in `gpt-oss:20b` even though it's smaller and faster on English humanities — the Korean accuracy regression (factual errors on basic Korean history) and creative-writing failure mode would degrade the literary-master use case more than the English-humanities-pipeline depth gain would help.

Optional: add `gpt-oss:20b` as an *opt-in* English-humanities chapter mode, gated by language detection. Keep `gpt-oss:120b` for the depth-specialist slot when 65 GB is available.

## Files

```
data/
├── 2026-04-12/                          # gemma4 baselines (capital, suneung, creative)
└── 2026-05-02_gptoss20_multiaxis/       # gpt-oss:20b new measurements
    ├── gpt-oss-20b_capital.{md,json}
    ├── gpt-oss-20b_suneung.{md,json}
    ├── gpt-oss-20b_creative.json        # 7-min hang, done:false, 0 response tokens
    └── gpt-oss-20b_creative_nothink.json # 10-min curl timeout, no JSON
```

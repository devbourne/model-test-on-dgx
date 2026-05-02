# Korean Long-Form Failure Modes — gemma4 vs gpt-oss:120b

**Date:** 2026-05-02
**Hardware:** NVIDIA DGX Spark (GB10, 128 GB)
**Test pipeline:** literary-master v2 full analyze pipeline (`/api/analyze`)
**Input:** *Gift of the Magi* opening (~1 KB English, 5 blocks)
**Output expected:** Korean long-form analysis (synthesis essay ~3 KB, per-block commentary ~500 chars each)

This report documents a failure mode the previous multi-axis evaluation ([2026-05-02_gptoss20_vs_gemma4_multiaxis.md](2026-05-02_gptoss20_vs_gemma4_multiaxis.md)) **did not measure** and therefore did not catch — and proposes both a model-routing fix and an evaluation-methodology fix.

## TL;DR

- gemma4-26b-fast and gpt-oss:120b **both fail** at Korean long-form generation, in *different* ways.
- gemma4: character-level glitches (typos like "20나기" for "20세기"). Surface defects, meaning preserved.
- gpt-oss:120b: semantic errors (literal title "마기의 선물" → "마귀들의 선물" — *Magi* mistranslated as *devils*). Surface clean, meaning inverted.
- Both: hallucinated content not present in the input passage (the famous *Gift of the Magi* twist ending was added even though only the opening 4 paragraphs were sent).
- gemma4 finished in 7 min; gpt-oss:120b took 31 min (4.4× slower) and finished `complete_with_warnings` after Verify v2 diverged.
- **Recommendation**: keep gemma4 as default; add a Korean proofreading post-stage and a hallucination guard. Update the evaluation framework to include a "Korean long-form" axis.

## How this gap was created

The previous multi-axis evaluation tested four axes:
1. Korean factual short answer (~200 tokens)
2. Korean SAT-style analytical output (~2,000 tokens, mostly *factual* content with structured sections)
3. English constrained creative writing (~500 words)
4. English humanities pipeline (extract → gloss → critique)

literary-master's actual production task — **English literary text in → Korean long-form analytical prose out (1,500–3,000+ tokens of *flowing essay*)** — is none of these. Axis 2 was the closest, but its output is structured/listy rather than continuous prose. The character-glitch failure mode in particular only appears reliably in continuous Korean generation past ~1,500 tokens; structured short-answer output stays clean.

**Lesson**: Evaluation axes must map 1:1 to production tasks. We selected models on Korean instruction-following and English humanities; both held. The actual gap was in the cross-product (English-in, Korean-out, long-form, prose). Adding axis-mapping audit to future evaluations.

## Test setup

Same input text, same params, same `literary-master-v2` pipeline (default `temperature=0.3`, `num_ctx=32768`):

```
The Gift of the Magi

One dollar and eighty-seven cents. That was all. ... [opening 4 paragraphs only]
```

Two runs:
- `ANALYSIS_MODEL=bjoernb/gemma4-26b-fast` (default)
- `ANALYSIS_MODEL=gpt-oss:120b`

Saved evidence: [data/2026-05-02_korean_long_form/](../data/2026-05-02_korean_long_form/) — full teaching-material JSONs from both runs plus input.

## Quantitative

| | gemma4-26b-fast | gpt-oss:120b |
|---|---|---|
| Wall-clock | **419 s** (~7 min) | 1,847 s (~31 min) — **4.4× slower** |
| Total tokens | 11,709 | 41,986 (3.6× more) |
| Coverage Repair | 0 partial blocks | **1 partial** (Repair Agent failed to recover one empty block) |
| Verify v2 result | `VERIFIED` (2 iter) | `UNCERTAIN` (3 iter — max, divergent) |
| Final state | `complete` | **`complete_with_warnings`** (4 warnings) |
| Memory footprint | 17 GB | 65 GB |

### Verify v2 divergence (gpt-oss:120b)

| iter | issues found | corrections applied |
|---|---|---|
| 1 | 4 | 4 |
| 2 | **5** (more than iter 1) | 5 |
| 3 | 0 (parse failure) | 0 — UNCERTAIN |

Each round of corrections introduced new issues. The `max_iterations=3` cap fired as designed (Verify v2 §3.7), and the Finalization Gate emitted `complete_with_warnings` rather than `complete` — the safety net works, but the *primary defense* (Verify→Correct→Re-verify converging to VERIFIED) does not converge for this model on this task.

## Qualitative — failure modes side by side

### Failure mode 1: gemma4 character-level glitches

From the synthesis `overview_essay_ko`:

> 오 헨리의 이 단편 소설은 **20나기** 초 미국의 경제적 빈곤 속에서도 빛나는 **숭거한** 사랑을 다룹니다. 작품은 극심한 결핍을 보여주는 건조한 수치로 시작하여 ... 독자로 하여금 선물이라는 **행의** 본질을 다시금 성찰하게 만듭니다.

Three errors in the first paragraph:
- "20나기" → should be "20세기" (Hanja-derived syllable substitution: 세 → 나)
- "숭거한" → should be "숭고한" (Hanja-derived syllable substitution: 고 → 거)
- "행의 본질" → should be "행위의 본질" or "행동의 본질" (missing syllable)

**Same paragraph later contains "숭고한 희생" written correctly** — the model "knows" the word; the Q4_K_M quantization corrupts it non-deterministically. Reading the whole synthesis confirms: glitches are sparse but present throughout long Korean prose, never in short Korean output.

### Failure mode 2: gpt-oss:120b semantic error

From block 001 translations:

```json
{
  "literary_translation": "마기의 선물",
  "literal_translation": "마귀들의 선물",     // ← Magi rendered as DEVILS
  "korean_commentary": "오헨리의 짧은 이야기를 알리는 제목이다. '마기'는 동방박사를 의미하며..."
}
```

The model **knows** in commentary that "마기 = 동방박사 (Magi)" but emits "마귀들 (devils)" in literal_translation a few tokens earlier. This is a *worse* failure than character glitches:

- gemma4 typo: a Korean reader recognizes "20나기" → "20세기" and self-corrects mentally
- gpt-oss:120b inversion: a Korean reader has no signal; "마귀들의 선물" reads as legitimate "Devils' Gift", a completely different work

Synthesis essay itself is clean character-wise — no typos. Naturalness is high. But the per-block translations carry the semantic flip.

### Failure mode 3: shared — content hallucination

Both models invented an ending:

> "결말에서는 서로가 포기한 물건이 바로 상대에게 줄 선물이라는 역설적인 상황이 드러난다." (gpt-oss:120b)
> "물질적 가치가 무너진 자리에 남는 정신적 풍요를 조명합니다." (gemma4 — softer but same direction)

The input was the opening 4 paragraphs only. Della counts $1.87 and starts to weep — that's where the input ends. Both models pulled the famous Della-sells-her-hair / Jim-sells-his-watch twist from prior training and presented it as if it were in the source.

Verify v2 correctly flagged this in gpt-oss:120b's iter 3 (`보고서는 원문 결말에 존재하지 않는 사건과 주제를 해석하고 있어 원문과 불일치합니다`) — but the divergent loop ended UNCERTAIN before the fix could land. gemma4's Verify VERIFIED the hallucinated essay, missing the issue entirely.

This is a third orthogonal failure mode: **prior-knowledge fabrication**. Independent of quantization, independent of Korean — caused by both models having the work in training data. Will hit any well-known text.

## Failure-mode summary table

| Mode | Source | gemma4 | gpt-oss:120b | Severity for production |
|---|---|---|---|---|
| Character glitches | Q4 quant + sparse Korean tokens at length | ❌ frequent | ✅ clean | Medium — readable but sloppy |
| Semantic error in translation | MXFP4 quant + harmonization edge case | ✅ correct | ❌ "마기→마귀들" | **High — silently wrong** |
| Content hallucination | Prior knowledge of canonical texts | ❌ adds twist | ❌ adds twist | **High — fabricated facts** |
| Verify divergence | Model unable to apply own corrections cleanly | ✅ converges | ❌ 4→5 issues | Medium — gate catches it |
| Coverage Repair miss | Single-block prompt fails on edge cases | ✅ 0 partial | ❌ 1 partial | Low — surfaced as warning |
| Speed | Memory bandwidth / output verbosity | ~7 min | ~31 min | Operational |

## Why no qwen3 test

The plan was conditional: if gpt-oss:120b were clean, also run qwen3:30b for the size-optimal candidate. Since gpt-oss:120b is *worse* than gemma4 on the most-critical axes (semantic accuracy, speed), and the failure modes are *intrinsic to long-form Korean from any large MoE quant model with Western-text prior knowledge*, qwen3:30b is unlikely to bring a clean win. Skipped.

If a future need arises (e.g. exploring a non-quantized setup), qwen3:30b should be tested with the same harness.

## Recommendation

**Keep `bjoernb/gemma4-26b-fast` as the literary-master v2 default.** It is the fastest, smallest, and produces the most semantically-correct Korean. Its character glitches are addressable by a post-processing layer; gpt-oss:120b's semantic errors are not.

Add two new defensive layers to v2:

### Phase 3 — Korean Proofreading Agent (post-Synthesis)

- New agent: takes Synthesis JSON's Korean fields, asks an LLM to *only* fix character-level errors (typos, missing syllables, broken Hanja transliterations) without touching meaning, structure, or rephrasing.
- Use FALLBACK_MODEL (e.g. qwen3:30b) for precision; reject if diff exceeds 5% per field (signal that the model is rewriting rather than proofreading).
- Hooks between Synthesis Agent and Verify Agent so Verify sees clean text.
- Catches: gemma4's "20나기 / 숭거한 / 행의" class.

### Phase G — Hallucination Guard (Synthesis prompt + Verify schema)

- Strengthen synthesis prompt with explicit "Use ONLY information present in the provided block summaries. Do NOT use prior knowledge of the work itself." Include a self-check checklist at the prompt's end.
- Extend VerificationSchema with `grounded_only: boolean`. Verify prompt asks: "Does the report cite any sentence not derivable from the source passage?" If false → flag as warning even when no other issues.
- Catches: both models' "fabricated ending" class.

These two layers together attack the two intrinsic failure modes that single-model swap cannot fix.

## Recommendation for the evaluation framework

This report is itself the artifact of the methodology fix:

1. **Map each evaluation axis to a production task.** Before adding a model to the keepers list, verify there is at least one axis whose I/O language pair, output length range, and output structure (prose vs structured) match the model's intended production use.
2. **Add a "Korean long-form analytical prose" axis** to the next round. Inputs: 1–3 KB English literary text. Outputs: 1,500+ tokens of continuous Korean essay. Score on character integrity (auto-detect typos), semantic accuracy (manual review of named-entity translations), and source-grounding (does it cite content in the input only?).
3. **Run the new axis on every existing keeper** before publishing the multi-axis report as final. Keepers that fail it must either be excluded for the matching production task or be paired with a documented post-processing layer.

## Files

```
data/2026-05-02_korean_long_form/
├── input_text.json              # Gift of Magi opening (4 paragraphs)
├── gemma4_gift_of_magi.json     # default model run (complete, 7 min)
└── gptoss120b_gift_of_magi.json # gpt-oss:120b run (complete_with_warnings, 31 min)
```

The full saved teaching materials include profile, all 5 blocks, synthesis, verification record (with Verify v2's full corrections trail for gpt-oss:120b), and stats. Useful for direct inspection of glitch patterns or for re-grading by future evaluators.

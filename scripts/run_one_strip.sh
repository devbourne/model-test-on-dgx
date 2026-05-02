#!/bin/bash
# Generic single-model 3-stage pipeline runner — with <think>...</think> stripping.
# For reasoning models (nemotron, magistral, qwen3-thinking) whose deliberation
# trace leaks into .response. Behavior is identical to run_one.sh on non-reasoning
# models (the strip is a no-op when no </think> tag is present).
# Usage: bash run_one_strip.sh <ollama_model_tag> <alias>
set -e
cd "$(dirname "$0")"

MODEL="${1:?usage: bash run_one_strip.sh <model> <alias>}"
ALIAS="${2:?usage: bash run_one_strip.sh <model> <alias>}"
PASSAGE="$(cat passage.txt)"
OUT="out"
mkdir -p "$OUT"

run_stage() {
  local stage="$1" prompt="$2"
  local file="$OUT/${ALIAS}_${stage}.md"
  local raw_file="$OUT/${ALIAS}_${stage}.raw.md"
  echo "[${ALIAS}/${stage}] running..." >&2
  local payload
  payload=$(jq -n --arg model "$MODEL" --arg prompt "$prompt" \
    '{model:$model, prompt:$prompt, stream:false, options:{temperature:0.3, num_ctx:8192}}')
  local resp
  resp=$(curl -s http://localhost:11434/api/generate -d "$payload")
  # Save raw response (with any <think> trace) for inspection
  echo "$resp" | jq -r '.response' > "$raw_file"
  # Stripped version: drop everything up to and including the first </think>
  # No-op when </think> is absent.
  echo "$resp" | jq -r '.response' \
    | sed -E ':a;N;$!ba;s|^.*</think>[[:space:]]*||' \
    > "$file"
  local ec ed td tps ts
  ec=$(echo "$resp" | jq -r '.eval_count // 0')
  ed=$(echo "$resp" | jq -r '.eval_duration // 0')
  td=$(echo "$resp" | jq -r '.total_duration // 0')
  if [ "$ed" -gt 0 ]; then
    tps=$(awk -v e="$ec" -v d="$ed" 'BEGIN{printf "%.1f", e/(d/1e9)}')
  else tps="0"; fi
  ts=$(awk -v t="$td" 'BEGIN{printf "%.1f", t/1e9}')
  echo "${ALIAS},${stage},${ec},${ts},${tps}" >> "$OUT/timings.csv"
  echo "  → ${file} (${ec} tok, ${ts}s, ${tps} tok/s)" >&2
}

P1="You are an analytical reading assistant. The passage below is from a humanities/philosophy text.

TASK: Extract the argumentative structure as STRICT JSON with this schema:
{
  \"thesis\": string,
  \"premises\": [string],
  \"key_concepts\": [{\"term\": string, \"role\": string}],
  \"argumentative_moves\": [string],
  \"intended_conclusion\": string
}
Output ONLY the JSON, no prose, no code fences.

PASSAGE:
---
${PASSAGE}
---"

run_stage "01_extract" "$P1"
S1=$(cat "$OUT/${ALIAS}_01_extract.md")

P2="You are explaining a philosophical passage to an advanced undergraduate.
Below is the original passage and a JSON outline of its structure.

TASK: Produce a SEMANTIC GLOSS — a careful explanation that:
1. Restates the central image/metaphor in plain modern English
2. Decodes each key symbol (cave, chains, fire, shadows, sun, ascent, etc.) — what it stands for and why
3. Explains the epistemological claim being made (about knowledge, illusion, education)
4. Surfaces 2-3 non-obvious implications a first-time reader might miss

Aim for ~400 words. No bullet salad — write paragraphs. Be precise, not florid.

PASSAGE:
---
${PASSAGE}
---

STRUCTURE OUTLINE (from prior stage):
---
${S1}
---"

run_stage "02_gloss" "$P2"
S2=$(cat "$OUT/${ALIAS}_02_gloss.md")

P3="You are a critical reader writing for a humanities seminar.
Below is the original passage and a semantic gloss of it.

TASK: Produce a CRITIQUE in three sections:

(A) WEAKNESSES: 2-3 internal tensions, ambiguities, or unargued assumptions in Plato's allegory itself.
(B) COUNTERARGUMENTS: 2 substantive objections from later philosophical traditions (e.g., empiricism, pragmatism, Nietzsche, phenomenology, post-structuralism). Name the tradition and state the specific objection.
(C) FOLLOW-UP QUESTIONS: 3 questions a serious reader should pursue next, ordered from concrete to speculative.

Be concise and sharp. ~350 words total. Avoid hedging.

PASSAGE:
---
${PASSAGE}
---

GLOSS (from prior stage):
---
${S2}
---"

run_stage "03_critique" "$P3"
echo "Done. ${ALIAS} stages saved to $OUT/"

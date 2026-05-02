#!/bin/bash
# Multi-axis benchmark: gpt-oss:20b on the 2026-04-12 prompts
# (Korean short answer, Korean SAT analysis, English constrained creative).
# Same prompts gemma4 was tested on, so quality/speed deltas isolate the model.
set -e
cd "$(dirname "$0")"

MODEL="${1:-gpt-oss:20b}"
ALIAS="${2:-gpt-oss-20b}"
OUT_RAW="raw_api"
OUT_KS="korean_suneung"
OUT_CS="creative_story"
mkdir -p "$OUT_RAW" "$OUT_KS" "$OUT_CS"

run_task() {
  local task_name="$1" prompt_file="$2" out_dir="$3" extra_opts="$4"
  local prompt
  prompt=$(cat "prompts/${prompt_file}")
  local payload
  payload=$(jq -n \
    --arg model "$MODEL" \
    --arg prompt "$prompt" \
    --argjson opts "${extra_opts:-{\}}" \
    '{model:$model, prompt:$prompt, stream:false, options:({temperature:0.3,num_ctx:8192} + $opts)}')
  echo "[${ALIAS}/${task_name}] running..." >&2
  local t0 t1
  t0=$(date +%s.%N)
  local resp
  resp=$(curl -s http://localhost:11434/api/generate -d "$payload")
  t1=$(date +%s.%N)
  echo "$resp" > "${OUT_RAW}/${ALIAS}_${task_name}.json"
  echo "$resp" | jq -r '.response' > "${out_dir}/${ALIAS}_${task_name}.md"
  local ec ed td tps ts
  ec=$(echo "$resp" | jq -r '.eval_count // 0')
  ed=$(echo "$resp" | jq -r '.eval_duration // 0')
  td=$(echo "$resp" | jq -r '.total_duration // 0')
  if [ "$ed" -gt 0 ]; then
    tps=$(awk -v e="$ec" -v d="$ed" 'BEGIN{printf "%.1f", e/(d/1e9)}')
  else tps="0"; fi
  ts=$(awk -v t="$td" 'BEGIN{printf "%.1f", t/1e9}')
  echo "  → ${out_dir}/${ALIAS}_${task_name}.md (${ec} tok, ${ts}s, ${tps} tok/s)" >&2
}

run_task "capital"  "korean_capital_prompt.txt"   "$OUT_KS" '{}'
run_task "suneung"  "suneung_english_prompt.txt"  "$OUT_KS" '{}'
run_task "creative" "creative_story_prompt.txt"   "$OUT_CS" '{}'

echo "Done. ${ALIAS} results saved." >&2

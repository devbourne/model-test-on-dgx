#!/usr/bin/env python3
"""
Evaluate structural role analysis with refined compact prompt via Ollama.
Usage: python eval_structural_prompt.py <model> [max_samples]
  model: qwen3:30b | gpt-oss:120b
"""
import json, re, sys, requests
from collections import Counter, defaultdict

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3:30b"
MAX_SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 10
TEST_PATH = "/home/code/structural_labeling/training_data/structural_test.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"

# ========================================
# Refined Compact Prompt
# ========================================
SYSTEM_PROMPT = """You are a structural analysis expert for English reading comprehension passages (수능 영어).

TASK: Analyze each sentence's structural role, identify the main claim, and map structural relationships.

## Structural Roles (assign ONE per sentence):
- Main Claim: Central thesis (핵심 주장) — the passage's core message
- Background: Context/setup (배경)
- Definition: Defines key terms (정의)
- Explanation: Clarifies the main idea (설명) — expands HOW/WHY
- Evidence: Facts/data proving the claim (증거) — objective proof
- Illustration: Specific example (예시) — concrete case/story
- Comparison: Parallel case (비교)
- Contrast: Opposing view (대조)
- Evaluation: Author's judgment (평가)
- Consequence: Result/implication (결과)
- Conclusion: Final wrap-up (결론)

### Role Disambiguation:
- Explanation vs Evidence: Explanation = abstract clarification; Evidence = concrete facts/data
- Explanation vs Illustration: Explanation = general elaboration; Illustration = specific named example
- Evidence vs Illustration: Evidence = data/research; Illustration = anecdote/scenario
- Consequence vs Conclusion: Consequence = causal result; Conclusion = summary/restatement

## Hierarchical Levels:
- Intro: Background, Definition
- Main: Main Claim
- Support: Explanation, Evidence, Illustration, Comparison, Contrast
- Addition: Consequence, Conclusion, Evaluation

## Structural Relationships (src → dst):
- supports: dst proves src
- exemplifies: dst gives example of src
- explains: dst clarifies src
- contrasts: dst opposes src
- compares: dst parallels src
- contextualizes: dst provides background for src
- concludes: dst wraps up src
- evaluates: dst judges src
- extends: dst shows consequence of src
- defines: dst defines term in src

RULES:
1. Main Claim sentence = src in most relationships
2. Intro → Main (contextualizes), Main → Support (supports/exemplifies/explains)
3. Only create meaningful relationships, not all consecutive pairs
4. Output ONLY valid JSON, no markdown or extra text"""

USER_TEMPLATE = """/no_think
Analyze this passage structurally.

**Text ID**: {text_id}

## Sentences:
{sentences}

Output JSON:
{{
  "text_id": {text_id},
  "sentence_analysis": [
    {{"sentence_id": <int>, "structural_role": "<role>", "hierarchical_level": "<level>", "signal_words": [...]}}
  ],
  "main_sentence_ids": [<int>],
  "sentence_pairs": [
    {{"src_sentence_id": <int>, "dst_sentence_id": <int>, "relationship": "<type>", "confidence": "<high|medium|low>"}}
  ]
}}"""


def query_ollama(messages, temperature=0):
    for attempt in range(3):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": 8192}
            }, timeout=600)
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            if content.strip():
                return content
            print(f"    Empty response, retry {attempt+1}")
        except Exception as e:
            print(f"    Retry {attempt+1}: {e}")
    return ""


def parse_json_response(text):
    text = text.strip()
    # Remove Qwen3 thinking blocks
    text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
    # Remove markdown code blocks
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def format_sentences(sample):
    """Extract sentences from the user message in training data."""
    user_msg = sample["messages"][1]["content"]
    # Extract the sentences section
    lines = []
    in_sentences = False
    for line in user_msg.split('\n'):
        if '## Sentences:' in line:
            in_sentences = True
            continue
        if in_sentences and line.startswith('## '):
            break
        if in_sentences and line.strip():
            lines.append(line)
    return '\n'.join(lines)


def main():
    print(f"Model: {MODEL}")
    print(f"Prompt: Refined Compact Structural Analysis")

    samples = []
    with open(TEST_PATH) as f:
        for line in f:
            samples.append(json.loads(line))
    samples = samples[:MAX_SAMPLES]
    print(f"Evaluating {len(samples)} samples...\n")

    # Metrics
    json_ok = 0
    role_correct = role_total = 0
    level_correct = level_total = 0
    main_tp = main_fp = main_fn = 0
    rel_correct = rel_total = 0
    role_confusion = defaultdict(Counter)
    rel_confusion = defaultdict(Counter)

    for i, sample in enumerate(samples):
        true_output = json.loads(sample["messages"][2]["content"])
        true_roles = {s["sentence_id"]: s["structural_role"] for s in true_output["sentence_analysis"]}
        true_levels = {s["sentence_id"]: s["hierarchical_level"] for s in true_output["sentence_analysis"]}
        true_mains = set(true_output["main_sentence_ids"])
        true_pairs = {(p["src_sentence_id"], p["dst_sentence_id"]): p["relationship"]
                      for p in true_output["sentence_pairs"]}

        # Build user message
        text_id = sample["text_id"]
        sentences_text = format_sentences(sample)
        user_msg = USER_TEMPLATE.format(text_id=text_id, sentences=sentences_text)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        response = query_ollama(messages)
        pred = parse_json_response(response)

        if pred is None:
            role_total += len(true_roles)
            level_total += len(true_levels)
            main_fn += len(true_mains)
            rel_total += len(true_pairs)
            snippet = response[:200].replace('\n', '\\n') if response else "(empty)"
            print(f"  [{i+1}/{len(samples)}] JSON FAIL | text_id={text_id}")
            print(f"    Response start: {snippet}")
            continue

        json_ok += 1

        # Role accuracy
        pred_roles = {}
        if "sentence_analysis" in pred:
            for s in pred["sentence_analysis"]:
                sid = s.get("sentence_id")
                if sid is not None:
                    pred_roles[sid] = s.get("structural_role", "")

        for sid, true_role in true_roles.items():
            role_total += 1
            pred_role = pred_roles.get(sid, "MISSING")
            if pred_role == true_role:
                role_correct += 1
            role_confusion[true_role][pred_role] += 1

        # Level accuracy
        pred_levels = {}
        if "sentence_analysis" in pred:
            for s in pred["sentence_analysis"]:
                sid = s.get("sentence_id")
                if sid is not None:
                    pred_levels[sid] = s.get("hierarchical_level", "")

        for sid, true_level in true_levels.items():
            level_total += 1
            if pred_levels.get(sid, "") == true_level:
                level_correct += 1

        # Main sentence
        pred_mains = set(pred.get("main_sentence_ids", []))
        main_tp += len(true_mains & pred_mains)
        main_fp += len(pred_mains - true_mains)
        main_fn += len(true_mains - pred_mains)

        # Relationship accuracy
        pred_pairs = {}
        if "sentence_pairs" in pred:
            for p in pred["sentence_pairs"]:
                src = p.get("src_sentence_id")
                dst = p.get("dst_sentence_id")
                if src is not None and dst is not None:
                    pred_pairs[(src, dst)] = p.get("relationship", "")

        for (src, dst), true_rel in true_pairs.items():
            rel_total += 1
            pred_rel = pred_pairs.get((src, dst), "MISSING")
            if pred_rel == true_rel:
                rel_correct += 1
            rel_confusion[true_rel][pred_rel] += 1

        r_acc = role_correct / role_total * 100 if role_total else 0
        l_acc = level_correct / level_total * 100 if level_total else 0
        print(f"  [{i+1}/{len(samples)}] Role:{r_acc:.1f}% Level:{l_acc:.1f}% | text_id={text_id}")

    # Results
    total = len(samples)
    print("\n" + "=" * 60)
    print(f"RESULTS: {MODEL} + Refined Compact Prompt")
    print("=" * 60)

    print(f"\n1. JSON Parse: {json_ok}/{total} ({json_ok/total*100:.1f}%)")

    if role_total:
        print(f"\n2. Structural Role: {role_correct}/{role_total} ({role_correct/role_total*100:.1f}%)")
        for role in sorted(role_confusion.keys()):
            preds = role_confusion[role]
            t = sum(preds.values())
            c = preds.get(role, 0)
            print(f"     {role:20s}: {c:3d}/{t:3d} = {c/t*100:5.1f}%")

    if level_total:
        print(f"\n3. Hierarchical Level: {level_correct}/{level_total} ({level_correct/level_total*100:.1f}%)")

    mp = main_tp / (main_tp + main_fp) if (main_tp + main_fp) else 0
    mr = main_tp / (main_tp + main_fn) if (main_tp + main_fn) else 0
    mf = 2*mp*mr/(mp+mr) if (mp+mr) else 0
    print(f"\n4. Main Sentence: P={mp:.3f} R={mr:.3f} F1={mf:.3f}")

    if rel_total:
        print(f"\n5. Relationship: {rel_correct}/{rel_total} ({rel_correct/rel_total*100:.1f}%)")
        for rel in sorted(rel_confusion.keys()):
            preds = rel_confusion[rel]
            t = sum(preds.values())
            c = preds.get(rel, 0)
            print(f"     {rel:20s}: {c:3d}/{t:3d} = {c/t*100:5.1f}%")

    # Save
    out = {
        "model": MODEL, "prompt": "refined_compact",
        "total": total, "json_parse_rate": json_ok/total,
        "role_accuracy": role_correct/role_total if role_total else 0,
        "level_accuracy": level_correct/level_total if level_total else 0,
        "main_f1": mf,
        "rel_accuracy": rel_correct/rel_total if rel_total else 0,
    }
    safe = MODEL.replace(":", "_").replace("/", "_")
    outfile = f"/home/code/structural_labeling/eval_{safe}_compact_{total}.json"
    with open(outfile, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {outfile}")


if __name__ == "__main__":
    main()

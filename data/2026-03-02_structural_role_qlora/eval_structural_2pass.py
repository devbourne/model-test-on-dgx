#!/usr/bin/env python3
"""
2-Pass Structural Role Analysis Evaluation via Ollama.
Pass 1: sentence_analysis + main_sentence_ids
Pass 2: sentence_pairs (using Pass 1 results as context)

Usage: python eval_structural_2pass.py <model> [max_samples]
"""
import json, re, sys, requests
from collections import Counter, defaultdict

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-oss:120b"
MAX_SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 10
TEST_PATH = "/home/code/structural_labeling/training_data/structural_test.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"

# ========================================
# Pass 1: Sentence Analysis + Main IDs
# ========================================
SYSTEM_PASS1 = """You are a structural analysis expert for English reading comprehension passages (수능 영어).

TASK: Analyze each sentence's structural role and identify the main claim sentence(s).

## Structural Roles (assign ONE per sentence):
- Main Claim: Central thesis (핵심 주장) — the passage's core message
- Background: Context/setup (배경) — introduces the topic before the main point
- Definition: Defines key terms (정의) — "X is/means/refers to..."
- Explanation: Clarifies the main idea (설명) — expands HOW/WHY abstractly
- Evidence: Facts/data proving the claim (증거) — studies, statistics, research findings
- Illustration: Specific example (예시) — concrete case, named example, anecdote
- Comparison: Parallel case (비교) — "similarly", "just as", "likewise"
- Contrast: Opposing view (대조) — "however", "on the other hand", "but"
- Evaluation: Author's judgment (평가) — "importantly", "unfortunately", value judgment
- Consequence: Result/implication (결과) — "as a result", "therefore", causal outcome
- Conclusion: Final wrap-up (결론) — summarizes/restates the main point at the end

### Role Disambiguation:
- Explanation vs Evidence: Explanation = abstract reasoning ("because..."); Evidence = concrete data ("studies show...")
- Explanation vs Illustration: Explanation = general elaboration; Illustration = specific named example/story
- Evidence vs Illustration: Evidence = research/data with numbers; Illustration = narrative/scenario
- Consequence vs Conclusion: Consequence = causal result of something; Conclusion = passage-ending summary
- Background vs Definition: Background = situational context; Definition = explicit term explanation

## Hierarchical Levels:
- Intro: Background, Definition
- Main: Main Claim
- Support: Explanation, Evidence, Illustration, Comparison, Contrast
- Addition: Consequence, Conclusion, Evaluation

RULES:
1. Every passage has exactly ONE Main Claim (rarely two)
2. Main Claim is usually in the first 3 sentences
3. Assign hierarchical_level based on the role-level mapping above
4. Output ONLY valid JSON, no markdown or extra text"""

USER_PASS1 = """/no_think
Analyze each sentence's structural role.

**Text ID**: {text_id}

## Sentences:
{sentences}

Output JSON:
{{
  "text_id": {text_id},
  "sentence_analysis": [
    {{"sentence_id": <int>, "structural_role": "<role>", "hierarchical_level": "<level>", "signal_words": [...]}}
  ],
  "main_sentence_ids": [<int>]
}}"""

# ========================================
# Pass 2: Sentence Pairs (Relationships)
# ========================================
SYSTEM_PASS2 = """You are a structural relationship expert for English reading comprehension passages (수능 영어).

TASK: Given sentence-level structural analysis, determine the structural relationships between sentences.

## Relationship Types (src → dst):
- supports: dst provides evidence/proof FOR src (data backs up a claim)
- exemplifies: dst gives a specific example OF src (concrete instance of abstract idea)
- explains: dst clarifies/elaborates src (tells HOW or WHY)
- contrasts: dst presents an opposing view TO src ("however", "but", "on the other hand")
- compares: dst draws a parallel TO src ("similarly", "just as", "likewise")
- contextualizes: dst provides background/setup FOR src (scene-setting before main point)
- concludes: dst summarizes/wraps up src (final restatement)
- evaluates: dst makes a judgment ABOUT src (author's assessment)
- extends: dst shows a consequence/result OF src ("therefore", "as a result")
- defines: dst defines a term mentioned IN src

## Key Rules:
1. The Main Claim sentence is typically the SOURCE (src) of most relationships
2. Direction: src is the sentence being supported/explained/exemplified; dst does the supporting/explaining
3. Common patterns:
   - Background → Main Claim: contextualizes (Background is dst)
   - Main Claim → Explanation: explains (Explanation is dst)
   - Main Claim → Evidence: supports (Evidence is dst)
   - Main Claim → Illustration: exemplifies (Illustration is dst)
   - Main Claim → Contrast: contrasts (Contrast is dst)
   - Main Claim → Consequence: extends (Consequence is dst)
   - Main Claim → Conclusion: concludes (Conclusion is dst)
4. NOT every pair of sentences has a relationship — only create meaningful ones
5. Support sentences can also relate to each other (e.g., Illustration exemplifies Explanation)
6. Output ONLY valid JSON, no markdown or extra text"""

USER_PASS2 = """/no_think
Given the structural analysis below, determine sentence relationships.

**Text ID**: {text_id}

## Sentences:
{sentences}

## Structural Analysis (from Pass 1):
{pass1_result}

Now output ONLY the sentence_pairs:
{{
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
                "options": {"temperature": temperature, "num_predict": 4096}
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
    text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
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
    user_msg = sample["messages"][1]["content"]
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
    print(f"Strategy: 2-Pass (Pass1=Role+Main, Pass2=Relationships)")

    samples = []
    with open(TEST_PATH) as f:
        for line in f:
            samples.append(json.loads(line))
    samples = samples[:MAX_SAMPLES]
    print(f"Evaluating {len(samples)} samples...\n")

    # Metrics
    json_ok_p1 = json_ok_p2 = 0
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

        text_id = sample["text_id"]
        sentences_text = format_sentences(sample)

        # ===== PASS 1: Sentence Analysis =====
        user_msg1 = USER_PASS1.format(text_id=text_id, sentences=sentences_text)
        messages1 = [
            {"role": "system", "content": SYSTEM_PASS1},
            {"role": "user", "content": user_msg1},
        ]
        response1 = query_ollama(messages1)
        pred1 = parse_json_response(response1)

        if pred1 is None:
            role_total += len(true_roles)
            level_total += len(true_levels)
            main_fn += len(true_mains)
            rel_total += len(true_pairs)
            snippet = response1[:150].replace('\n', '\\n') if response1 else "(empty)"
            print(f"  [{i+1}/{len(samples)}] Pass1 FAIL | text_id={text_id}")
            print(f"    Response: {snippet}")
            continue

        json_ok_p1 += 1

        # Evaluate Pass 1: Role
        pred_roles = {}
        if "sentence_analysis" in pred1:
            for s in pred1["sentence_analysis"]:
                sid = s.get("sentence_id")
                if sid is not None:
                    pred_roles[sid] = s.get("structural_role", "")

        for sid, true_role in true_roles.items():
            role_total += 1
            pred_role = pred_roles.get(sid, "MISSING")
            if pred_role == true_role:
                role_correct += 1
            role_confusion[true_role][pred_role] += 1

        # Evaluate Pass 1: Level
        pred_levels = {}
        if "sentence_analysis" in pred1:
            for s in pred1["sentence_analysis"]:
                sid = s.get("sentence_id")
                if sid is not None:
                    pred_levels[sid] = s.get("hierarchical_level", "")

        for sid, true_level in true_levels.items():
            level_total += 1
            if pred_levels.get(sid, "") == true_level:
                level_correct += 1

        # Evaluate Pass 1: Main
        pred_mains = set(pred1.get("main_sentence_ids", []))
        main_tp += len(true_mains & pred_mains)
        main_fp += len(pred_mains - true_mains)
        main_fn += len(true_mains - pred_mains)

        # ===== PASS 2: Relationships =====
        # Format Pass 1 result as context
        pass1_summary = json.dumps({
            "sentence_analysis": pred1.get("sentence_analysis", []),
            "main_sentence_ids": pred1.get("main_sentence_ids", [])
        }, ensure_ascii=False)

        user_msg2 = USER_PASS2.format(
            text_id=text_id,
            sentences=sentences_text,
            pass1_result=pass1_summary
        )
        messages2 = [
            {"role": "system", "content": SYSTEM_PASS2},
            {"role": "user", "content": user_msg2},
        ]
        response2 = query_ollama(messages2)
        pred2 = parse_json_response(response2)

        if pred2 is None:
            rel_total += len(true_pairs)
            r_acc = role_correct / role_total * 100 if role_total else 0
            l_acc = level_correct / level_total * 100 if level_total else 0
            snippet = response2[:150].replace('\n', '\\n') if response2 else "(empty)"
            print(f"  [{i+1}/{len(samples)}] Pass2 FAIL | Role:{r_acc:.1f}% Level:{l_acc:.1f}% | text_id={text_id}")
            print(f"    Response: {snippet}")
            continue

        json_ok_p2 += 1

        # Evaluate Pass 2: Relationships
        pred_pairs = {}
        if "sentence_pairs" in pred2:
            for p in pred2["sentence_pairs"]:
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
        rel_acc = rel_correct / rel_total * 100 if rel_total else 0
        print(f"  [{i+1}/{len(samples)}] Role:{r_acc:.1f}% Level:{l_acc:.1f}% Rel:{rel_acc:.1f}% | text_id={text_id}")

    # Results
    total = len(samples)
    print("\n" + "=" * 60)
    print(f"RESULTS: {MODEL} + 2-Pass Prompt")
    print("=" * 60)

    print(f"\n1. JSON Parse: Pass1={json_ok_p1}/{total} Pass2={json_ok_p2}/{total}")

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
        "model": MODEL, "prompt": "2pass",
        "total": total,
        "json_parse_pass1": json_ok_p1/total,
        "json_parse_pass2": json_ok_p2/total,
        "role_accuracy": role_correct/role_total if role_total else 0,
        "level_accuracy": level_correct/level_total if level_total else 0,
        "main_f1": mf,
        "rel_accuracy": rel_correct/rel_total if rel_total else 0,
        "role_confusion": {k: dict(v) for k, v in role_confusion.items()},
        "rel_confusion": {k: dict(v) for k, v in rel_confusion.items()},
    }
    safe = MODEL.replace(":", "_").replace("/", "_")
    outfile = f"/home/code/structural_labeling/eval_{safe}_2pass_{total}.json"
    with open(outfile, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {outfile}")


if __name__ == "__main__":
    main()

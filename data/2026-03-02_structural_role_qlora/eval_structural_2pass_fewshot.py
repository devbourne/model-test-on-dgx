#!/usr/bin/env python3
"""
2-Pass + Few-Shot Structural Role Analysis Evaluation via Ollama.
Improvements over base 2-pass:
  - Few-shot example in both passes for in-context learning
  - Refined prompts with stronger disambiguation rules

Usage: python eval_structural_2pass_fewshot.py <model> [max_samples]
"""
import json, re, sys, requests, time
from collections import Counter, defaultdict

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-oss:120b"
MAX_SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 10
TEST_PATH = "/home/code/structural_labeling/training_data/structural_test.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"

# ========================================
# Few-Shot Example (text_id=42941, 6 sentences, 6 roles)
# ========================================
FEWSHOT_SENTENCES = """[1] Perceived distance of objects that are far away from the observer is often assumed to be subject to some global limitation in the sense that the moon, the stars, and the sun are all perceived at the "sky": that is, at about the same distance.
    (관찰자로부터 멀리 떨어져 있는 물체의 지각된 거리는 달, 별, 그리고 태양이 모두 '하늘'에서 지각된다는 점에서 어떤 광범위한 제한을 받는다고 종종 가정되는데, 즉 대략 같은 거리에서 그렇다는 것이다.)
[2] This observation is related to the idea that visual space is not open but ends at visible surfaces or, indeed, the sky.
    (이 관찰은 시각적 공간이 열려 있는 것이 아니라 보이는 표면이나 사실상 하늘에서 끝난다는 생각과 관련이 있다.)
[3] Uexkull and Kriszat (1934) suggested that this is realized as a hard limit, which they call the "farthest plane."
    (Uexkul과 Kriszat(1934)는 이것이 엄연한 한계로 실현된다고 제안했는데, 그들은 이를 '가장 먼 평면'이라고 부른다.)
[4] If an observed person or object would walk beyond this farthest plane, it would no longer be perceived as moving further away, but rather as shrinking in size.
    (만약 관찰된 사람이나 물체가 이 가장 먼 평면을 넘어 걷는다면, 더 이상 더 멀리 움직이는 것이 아니라, 오히려 크기가 줄어드는 것으로 지각될 것이다.)
[5] This observation is actually quite common; if looking down from a high tower, for example, cars or even houses on the ground below may appear as if they were toys: that is, shrunk, presumably because they are perceived at the distance of the farthest plane while subtending a visual angle that corresponds to a larger distance.
    (이런 관찰은 사실 꽤 흔한데, 예를 들어 높은 탑에서 내려다볼 때, 아래 지면에 있는 자동차나 심지어 집도 마치 장난감인 것처럼 보일 수도 있는데, 즉 그것들은 아마 더 먼 거리와 일치하는 시각에 대(對)하면서 가장 먼 평면의 거리에서 지각되기 때문에 줄어든 것으로 보인다.)
[6] The farthest plane would thus mark the limit of the perception of size constancy.
    (따라서 가장 먼 평면은 크기의 불변성에 대한 지각의 한계를 나타낼 것이다.)"""

FEWSHOT_PASS1_OUTPUT = """{
  "text_id": 42941,
  "sentence_analysis": [
    {"sentence_id": 1, "structural_role": "Background", "hierarchical_level": "Intro", "signal_words": ["often assumed", "that is", "about the same distance"]},
    {"sentence_id": 2, "structural_role": "Explanation", "hierarchical_level": "Intro", "signal_words": ["This observation is related to the idea", "not open", "ends at"]},
    {"sentence_id": 3, "structural_role": "Main Claim", "hierarchical_level": "Main", "signal_words": ["suggested", "hard limit", "the \\"farthest plane\\""]},
    {"sentence_id": 4, "structural_role": "Consequence", "hierarchical_level": "Support", "signal_words": ["If", "beyond this farthest plane", "no longer", "but rather"]},
    {"sentence_id": 5, "structural_role": "Illustration", "hierarchical_level": "Support", "signal_words": ["actually quite common", "for example", "appear as if"]},
    {"sentence_id": 6, "structural_role": "Conclusion", "hierarchical_level": "Addition", "signal_words": ["thus", "would mark the limit"]}
  ],
  "main_sentence_ids": [3]
}"""

FEWSHOT_PASS2_OUTPUT = """{
  "sentence_pairs": [
    {"src_sentence_id": 2, "dst_sentence_id": 3, "relationship": "contextualizes", "confidence": "high"},
    {"src_sentence_id": 3, "dst_sentence_id": 4, "relationship": "extends", "confidence": "high"},
    {"src_sentence_id": 3, "dst_sentence_id": 5, "relationship": "exemplifies", "confidence": "high"},
    {"src_sentence_id": 3, "dst_sentence_id": 6, "relationship": "concludes", "confidence": "high"},
    {"src_sentence_id": 4, "dst_sentence_id": 5, "relationship": "exemplifies", "confidence": "high"}
  ]
}"""

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

### Critical Disambiguation Rules:
- Explanation vs Evidence: Explanation = abstract reasoning ("because..."); Evidence = concrete data ("studies show...", numbers/stats)
- Explanation vs Illustration: Explanation = general elaboration; Illustration = specific named example/story/scenario
- Evidence vs Illustration: Evidence = research/data with numbers; Illustration = narrative/anecdote
- Consequence vs Conclusion: Consequence = causal result within the argument; Conclusion = passage-ending summary/restatement
- Background vs Definition: Background = situational context; Definition = explicit term explanation ("X is defined as...")
- Background vs Explanation: Background = BEFORE Main Claim (setup); Explanation = AFTER Main Claim (elaboration)

## Hierarchical Levels:
- Intro: Background, Definition
- Main: Main Claim
- Support: Explanation, Evidence, Illustration, Comparison, Contrast
- Addition: Consequence, Conclusion, Evaluation

RULES:
1. Every passage has exactly ONE Main Claim (rarely two)
2. Main Claim is usually in the first 3 sentences
3. Assign hierarchical_level strictly based on the role-level mapping above
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
- contrasts: dst presents an opposing view TO src ("however", "but")
- compares: dst draws a parallel TO src ("similarly", "just as")
- contextualizes: dst provides background/setup FOR src (scene-setting before main point)
- concludes: dst summarizes/wraps up src (final restatement)
- evaluates: dst makes a judgment ABOUT src (author's assessment)
- extends: dst shows a consequence/result OF src ("therefore", "as a result")
- defines: dst defines a term mentioned IN src

## Direction Rules (CRITICAL):
- src = the sentence being supported/explained/exemplified
- dst = the sentence doing the supporting/explaining/exemplifying
- The Main Claim is typically src (other sentences relate TO it)

## Common Patterns:
- Background → Main Claim: contextualizes (Background=dst, Main=src)
- Main Claim → Explanation: explains (Main=src, Explanation=dst)
- Main Claim → Evidence: supports (Main=src, Evidence=dst)
- Main Claim → Illustration: exemplifies (Main=src, Illustration=dst)
- Main Claim → Contrast: contrasts (Main=src, Contrast=dst)
- Main Claim → Consequence: extends (Main=src, Consequence=dst)
- Main Claim → Conclusion: concludes (Main=src, Conclusion=dst)
- Support → Support: e.g., Illustration exemplifies Explanation

## Key Rules:
1. NOT every pair of sentences has a relationship — only create meaningful structural ones
2. A sentence can be dst in one relationship and src in another
3. Typically 4-8 relationships per passage (not N-1 for N sentences)
4. Output ONLY valid JSON, no markdown or extra text"""

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


def query_ollama(messages, temperature=0, num_predict=4096):
    for attempt in range(3):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": num_predict}
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


def build_pass1_messages(text_id, sentences_text):
    """Build Pass 1 messages with few-shot example."""
    # Few-shot example
    fewshot_user = USER_PASS1.format(text_id=42941, sentences=FEWSHOT_SENTENCES)
    # Actual query
    actual_user = USER_PASS1.format(text_id=text_id, sentences=sentences_text)

    return [
        {"role": "system", "content": SYSTEM_PASS1},
        {"role": "user", "content": fewshot_user},
        {"role": "assistant", "content": FEWSHOT_PASS1_OUTPUT},
        {"role": "user", "content": actual_user},
    ]


def build_pass2_messages(text_id, sentences_text, pass1_summary):
    """Build Pass 2 messages with few-shot example."""
    # Few-shot example
    fewshot_pass1 = FEWSHOT_PASS1_OUTPUT
    fewshot_user = USER_PASS2.format(
        text_id=42941, sentences=FEWSHOT_SENTENCES, pass1_result=fewshot_pass1
    )
    # Actual query
    actual_user = USER_PASS2.format(
        text_id=text_id, sentences=sentences_text, pass1_result=pass1_summary
    )

    return [
        {"role": "system", "content": SYSTEM_PASS2},
        {"role": "user", "content": fewshot_user},
        {"role": "assistant", "content": FEWSHOT_PASS2_OUTPUT},
        {"role": "user", "content": actual_user},
    ]


def main():
    print(f"Model: {MODEL}")
    print(f"Strategy: 2-Pass + Few-Shot (Pass1=Role+Main, Pass2=Relationships)")
    print(f"Few-shot: text_id=42941 (6 sentences, 6 roles, 5 relationships)\n")

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
    start_time = time.time()

    for i, sample in enumerate(samples):
        true_output = json.loads(sample["messages"][2]["content"])
        true_roles = {s["sentence_id"]: s["structural_role"] for s in true_output["sentence_analysis"]}
        true_levels = {s["sentence_id"]: s["hierarchical_level"] for s in true_output["sentence_analysis"]}
        true_mains = set(true_output["main_sentence_ids"])
        true_pairs = {(p["src_sentence_id"], p["dst_sentence_id"]): p["relationship"]
                      for p in true_output["sentence_pairs"]}

        text_id = sample["text_id"]
        sentences_text = format_sentences(sample)
        t0 = time.time()

        # ===== PASS 1: Sentence Analysis =====
        messages1 = build_pass1_messages(text_id, sentences_text)
        response1 = query_ollama(messages1, num_predict=4096)
        pred1 = parse_json_response(response1)

        if pred1 is None:
            role_total += len(true_roles)
            level_total += len(true_levels)
            main_fn += len(true_mains)
            rel_total += len(true_pairs)
            snippet = response1[:150].replace('\n', '\\n') if response1 else "(empty)"
            print(f"  [{i+1}/{len(samples)}] Pass1 FAIL | text_id={text_id} ({time.time()-t0:.0f}s)")
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
        pass1_summary = json.dumps({
            "sentence_analysis": pred1.get("sentence_analysis", []),
            "main_sentence_ids": pred1.get("main_sentence_ids", [])
        }, ensure_ascii=False)

        messages2 = build_pass2_messages(text_id, sentences_text, pass1_summary)
        response2 = query_ollama(messages2, num_predict=4096)
        pred2 = parse_json_response(response2)

        if pred2 is None:
            rel_total += len(true_pairs)
            r_acc = role_correct / role_total * 100 if role_total else 0
            l_acc = level_correct / level_total * 100 if level_total else 0
            snippet = response2[:150].replace('\n', '\\n') if response2 else "(empty)"
            print(f"  [{i+1}/{len(samples)}] Pass2 FAIL | Role:{r_acc:.1f}% Level:{l_acc:.1f}% | text_id={text_id} ({time.time()-t0:.0f}s)")
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
        print(f"  [{i+1}/{len(samples)}] Role:{r_acc:.1f}% Level:{l_acc:.1f}% Rel:{rel_acc:.1f}% | text_id={text_id} ({time.time()-t0:.0f}s)")

    elapsed = time.time() - start_time

    # Results
    total = len(samples)
    print("\n" + "=" * 70)
    print(f"RESULTS: {MODEL} + 2-Pass + Few-Shot")
    print("=" * 70)

    print(f"\n1. JSON Parse: Pass1={json_ok_p1}/{total} Pass2={json_ok_p2}/{total}")

    if role_total:
        print(f"\n2. Structural Role: {role_correct}/{role_total} ({role_correct/role_total*100:.1f}%)")
        for role in sorted(role_confusion.keys()):
            preds = role_confusion[role]
            t = sum(preds.values())
            c = preds.get(role, 0)
            top_misclass = [(k, v) for k, v in preds.most_common(3) if k != role][:2]
            mis_str = ", ".join(f"{k}={v}" for k, v in top_misclass)
            print(f"     {role:20s}: {c:3d}/{t:3d} = {c/t*100:5.1f}%  {f'  ← misclass: {mis_str}' if mis_str else ''}")

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
            top_misclass = [(k, v) for k, v in preds.most_common(3) if k != rel][:2]
            mis_str = ", ".join(f"{k}={v}" for k, v in top_misclass)
            print(f"     {rel:20s}: {c:3d}/{t:3d} = {c/t*100:5.1f}%  {f'  ← misclass: {mis_str}' if mis_str else ''}")

    print(f"\nElapsed: {elapsed:.0f}s ({elapsed/total:.0f}s/sample)")

    # Comparison with baseline
    print("\n" + "=" * 70)
    print("COMPARISON WITH BASELINE (previous 10-sample results)")
    print("=" * 70)
    print(f"{'Metric':<25s} {'QLoRA':>8s} {'1-pass':>8s} {'2p+fs':>8s}")
    print("-" * 55)
    r_pct = role_correct/role_total*100 if role_total else 0
    l_pct = level_correct/level_total*100 if level_total else 0
    rel_pct = rel_correct/rel_total*100 if rel_total else 0
    print(f"{'Structural Role':<25s} {'53.5%':>8s} {'57.7%':>8s} {f'{r_pct:.1f}%':>8s}")
    print(f"{'Hierarchical Level':<25s} {'83.1%':>8s} {'81.7%':>8s} {f'{l_pct:.1f}%':>8s}")
    print(f"{'Main Sentence F1':<25s} {'0.636':>8s} {'0.667':>8s} {f'{mf:.3f}':>8s}")
    print(f"{'Relationship':<25s} {'7.2%':>8s} {'26.1%':>8s} {f'{rel_pct:.1f}%':>8s}")

    # Save
    out = {
        "model": MODEL, "prompt": "2pass_fewshot",
        "total": total,
        "json_parse_pass1": json_ok_p1/total,
        "json_parse_pass2": json_ok_p2/total,
        "role_accuracy": role_correct/role_total if role_total else 0,
        "level_accuracy": level_correct/level_total if level_total else 0,
        "main_f1": mf,
        "rel_accuracy": rel_correct/rel_total if rel_total else 0,
        "role_confusion": {k: dict(v) for k, v in role_confusion.items()},
        "rel_confusion": {k: dict(v) for k, v in rel_confusion.items()},
        "elapsed_seconds": elapsed,
    }
    safe = MODEL.replace(":", "_").replace("/", "_")
    outfile = f"/home/code/structural_labeling/eval_{safe}_2pass_fewshot_{total}.json"
    with open(outfile, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {outfile}")


if __name__ == "__main__":
    main()

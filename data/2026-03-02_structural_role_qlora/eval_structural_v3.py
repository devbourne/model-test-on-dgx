#!/usr/bin/env python3
"""
v3 Structural Role Analysis Evaluation — Optimized for gpt-oss:120b

Key changes from v2 (2pass_fewshot):
  - Concise system prompts: Pass1 ~250 tok (-55%), Pass2 ~200 tok (-60%)
  - 2 few-shot examples (42941 + 43266) covering more relationship patterns
  - Pass2 output simplified: src/dst/rel only (no confidence/reasoning)
  - "Generate ALL relationships" + quantity guide (N-2 to N+2)
  - Removed "NOT every pair" warning that caused MISSING relationships

Usage: python eval_structural_v3.py <model> [max_samples]
"""
import json, re, sys, requests, time
from collections import Counter, defaultdict

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-oss:120b"
MAX_SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 10
TEST_PATH = "/home/code/structural_labeling/training_data/structural_test.jsonl"
OLLAMA_URL = "http://localhost:11434/api/chat"

# ========================================
# Few-Shot Example 1: text_id=42941 (6 sentences)
# Roles: Background→Explanation→Main Claim→Consequence→Illustration→Conclusion
# Relationships: contextualizes, extends, exemplifies, concludes
# ========================================
FEWSHOT1_SENTENCES = """[1] Perceived distance of objects that are far away from the observer is often assumed to be subject to some global limitation in the sense that the moon, the stars, and the sun are all perceived at the "sky": that is, at about the same distance.
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

FEWSHOT1_PASS1_OUTPUT = """{
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

FEWSHOT1_PASS2_OUTPUT = """{
  "sentence_pairs": [
    {"src": 2, "dst": 3, "rel": "contextualizes"},
    {"src": 3, "dst": 4, "rel": "extends"},
    {"src": 3, "dst": 5, "rel": "exemplifies"},
    {"src": 3, "dst": 6, "rel": "concludes"},
    {"src": 4, "dst": 5, "rel": "exemplifies"}
  ]
}"""

# ========================================
# Few-Shot Example 2: text_id=43266 (7 sentences)
# Roles: Background→Explanation→Main Claim→Explanation→Contrast→Main Claim→Consequence
# Relationships: contextualizes, explains, contrasts, extends
# ========================================
FEWSHOT2_SENTENCES = """[1] Humans are unique in the realm of living beings in knowing there is a future.
    (인간은 미래가 있다는 것을 안다는 점에서 생물의 영역에서 고유하다.)
[2] If people experience worry and hope, it is because they realize the future exists, that it can be better or worse, and that the outcome depends to some extent on them.
    (사람들이 걱정과 희망을 경험한다면, 그것은 그들이 미래가 존재하고, 그것이 더 좋거나 나쁠 수 있고, 그 결과가 어느 정도 자신에게 달려 있다는 것을 깨닫기 때문이다.)
[3] But having this knowledge does not imply that they know what to do with it.
    (하지만 이것을 알고 있다는 것이 그들이 그것으로 무엇을 해야 하는지 알고 있다는 것을 의미하지는 않는다.)
[4] People often repress their awareness of the future because thinking about it distorts the comfort of the now, which tends to be more powerful than the future because it is present and because it is certain.
    (사람들은 미래에 대한 인식을 억누르는 경우가 많고, 그 이유는 미래에 대해 생각하는 것이 현재의 안락함을 왜곡하기 때문인데, 그것은 존재하고 있고 확실하기 때문에 미래보다 더 강력한 경향이 있다.)
[5] The future, on the other hand, must be imagined in advance and, for that very reason, is always uncertain.
    (반면에 미래는 미리 상상 되어야 하며, 바로 그 이유 때문에 항상 불확실하다.)
[6] Getting along with the future is not an easy task, nor is it one in which instinct prevents us from blunders.
    (미래와 잘 지내는 것은 쉬운 일이 아니며, 본능이 우리가 큰 실수를 저지르지 않게 막아 주는 그런 일도 아니다.)
[7] That is why we so often have a poor relationship with the future and are either more fearful than we need to be or allow ourselves to hope against all evidence; we worry excessively or not enough; we fail to predict the future or to shape it as much as we are able.
    (그것이 우리가 매우 자주 미래와 좋지 않은 관계를 가지게 되고, 그럴 필요가 있는 것보다 더 두려워하거나 모든 증거에 반하여 희망을 갖게 되는 이유인데, 우리는 과도하게 또는 충분치 않게 걱정하며, 우리가 할 수 있는 만큼 미래를 예측하거나 만들어 내지 못한다.)"""

FEWSHOT2_PASS1_OUTPUT = """{
  "text_id": 43266,
  "sentence_analysis": [
    {"sentence_id": 1, "structural_role": "Background", "hierarchical_level": "Intro", "signal_words": ["unique", "realm of living beings", "knowing there is a future"]},
    {"sentence_id": 2, "structural_role": "Explanation", "hierarchical_level": "Intro", "signal_words": ["If", "because", "worry and hope", "future exists"]},
    {"sentence_id": 3, "structural_role": "Main Claim", "hierarchical_level": "Main", "signal_words": ["But", "does not imply", "know what to do with it"]},
    {"sentence_id": 4, "structural_role": "Explanation", "hierarchical_level": "Support", "signal_words": ["often repress", "because", "comfort of the now"]},
    {"sentence_id": 5, "structural_role": "Contrast", "hierarchical_level": "Support", "signal_words": ["on the other hand", "must be imagined", "always uncertain"]},
    {"sentence_id": 6, "structural_role": "Main Claim", "hierarchical_level": "Main", "signal_words": ["not an easy task", "nor", "instinct", "blunders"]},
    {"sentence_id": 7, "structural_role": "Consequence", "hierarchical_level": "Addition", "signal_words": ["That is why", "poor relationship", "fail to predict"]}
  ],
  "main_sentence_ids": [3, 6]
}"""

FEWSHOT2_PASS2_OUTPUT = """{
  "sentence_pairs": [
    {"src": 1, "dst": 3, "rel": "contextualizes"},
    {"src": 2, "dst": 3, "rel": "contextualizes"},
    {"src": 3, "dst": 4, "rel": "explains"},
    {"src": 3, "dst": 5, "rel": "explains"},
    {"src": 3, "dst": 7, "rel": "extends"},
    {"src": 4, "dst": 5, "rel": "contrasts"},
    {"src": 6, "dst": 7, "rel": "extends"}
  ]
}"""

# ========================================
# Pass 1: Concise System Prompt (~250 tokens)
# ========================================
SYSTEM_PASS1 = """You analyze English passages (수능 영어) structurally.

For each sentence, assign exactly ONE role:
- Main Claim: core thesis (핵심 주장)
- Background: setup before main point (배경)
- Definition: defines a term (정의) — "X is/means/refers to..."
- Explanation: elaborates HOW/WHY (설명) — abstract reasoning
- Evidence: concrete data/research (증거) — numbers, studies, statistics
- Illustration: specific example/story (예시) — named case, anecdote
- Comparison: parallel case (비교) — "similarly", "likewise"
- Contrast: opposing view (대조) — "however", "but", "on the other hand"
- Evaluation: author's judgment (평가) — value assessment
- Consequence: causal result (결과) — "as a result", "therefore"
- Conclusion: final summary (결론) — restates main point at end

Hierarchical level by role:
- Intro: Background, Definition
- Main: Main Claim
- Support: Explanation, Evidence, Illustration, Comparison, Contrast
- Addition: Consequence, Conclusion, Evaluation

Rules: One Main Claim per passage (rarely two). Output JSON only."""

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
# Pass 2: Concise System Prompt (~200 tokens)
# ========================================
SYSTEM_PASS2 = """Given a passage with structural roles already assigned, identify ALL meaningful relationships between sentences.

Relationship types:
- supports: evidence/proof for a claim
- exemplifies: concrete example of an idea
- explains: clarifies/elaborates HOW or WHY
- contrasts: opposing view
- compares: parallel case
- contextualizes: provides background/setup
- concludes: summarizes/wraps up
- evaluates: judges/assesses
- extends: shows consequence/result
- defines: defines a term

Direction (src → dst):
- contextualizes: Background(src) → Main(dst) — background leads to main point
- explains/supports/exemplifies: Main(src) → Support(dst)
- extends/concludes: Main(src) → Addition(dst)
- contrasts: either direction depending on passage flow
Follow the examples carefully for direction conventions.

IMPORTANT: Generate ALL meaningful relationships. For N sentences, expect N-2 to N+2 relationships.
Do NOT omit obvious connections — contextualizes, explains, supports are common."""

USER_PASS2 = """/no_think
Given the structural analysis below, determine sentence relationships.

**Text ID**: {text_id}

## Sentences:
{sentences}

## Structural Analysis (from Pass 1):
{pass1_result}

Output JSON with ALL relationships:
{{
  "sentence_pairs": [
    {{"src": <int>, "dst": <int>, "rel": "<type>"}}
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
    """Build Pass 1 messages with 2 few-shot examples."""
    # Few-shot example 1
    fs1_user = USER_PASS1.format(text_id=42941, sentences=FEWSHOT1_SENTENCES)
    # Few-shot example 2
    fs2_user = USER_PASS1.format(text_id=43266, sentences=FEWSHOT2_SENTENCES)
    # Actual query
    actual_user = USER_PASS1.format(text_id=text_id, sentences=sentences_text)

    return [
        {"role": "system", "content": SYSTEM_PASS1},
        {"role": "user", "content": fs1_user},
        {"role": "assistant", "content": FEWSHOT1_PASS1_OUTPUT},
        {"role": "user", "content": fs2_user},
        {"role": "assistant", "content": FEWSHOT2_PASS1_OUTPUT},
        {"role": "user", "content": actual_user},
    ]


def build_pass2_messages(text_id, sentences_text, pass1_summary):
    """Build Pass 2 messages with 2 few-shot examples."""
    # Few-shot example 1
    fs1_user = USER_PASS2.format(
        text_id=42941, sentences=FEWSHOT1_SENTENCES,
        pass1_result=FEWSHOT1_PASS1_OUTPUT
    )
    # Few-shot example 2
    fs2_user = USER_PASS2.format(
        text_id=43266, sentences=FEWSHOT2_SENTENCES,
        pass1_result=FEWSHOT2_PASS1_OUTPUT
    )
    # Actual query
    actual_user = USER_PASS2.format(
        text_id=text_id, sentences=sentences_text,
        pass1_result=pass1_summary
    )

    return [
        {"role": "system", "content": SYSTEM_PASS2},
        {"role": "user", "content": fs1_user},
        {"role": "assistant", "content": FEWSHOT1_PASS2_OUTPUT},
        {"role": "user", "content": fs2_user},
        {"role": "assistant", "content": FEWSHOT2_PASS2_OUTPUT},
        {"role": "user", "content": actual_user},
    ]


def normalize_rel_pair(pair):
    """Extract (src, dst, rel) from either v2 or v3 format."""
    src = pair.get("src") or pair.get("src_sentence_id")
    dst = pair.get("dst") or pair.get("dst_sentence_id")
    rel = pair.get("rel") or pair.get("relationship", "")
    return src, dst, rel


def main():
    print(f"Model: {MODEL}")
    print(f"Strategy: v3 — 2-Pass + 2 Few-Shot + Concise Prompts")
    print(f"Few-shot: text_id=42941 (6 sent) + text_id=43266 (7 sent)")
    print(f"Pass2 output: compact (src/dst/rel only)\n")

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
    rel_missing = rel_extra = 0
    role_confusion = defaultdict(Counter)
    rel_confusion = defaultdict(Counter)
    start_time = time.time()

    for i, sample in enumerate(samples):
        true_output = json.loads(sample["messages"][2]["content"])
        true_roles = {s["sentence_id"]: s["structural_role"] for s in true_output["sentence_analysis"]}
        true_levels = {s["sentence_id"]: s["hierarchical_level"] for s in true_output["sentence_analysis"]}
        true_mains = set(true_output["main_sentence_ids"])
        true_pairs = {}
        for p in true_output["sentence_pairs"]:
            src, dst, rel = normalize_rel_pair(p)
            true_pairs[(src, dst)] = rel

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
            rel_missing += len(true_pairs)
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
            rel_missing += len(true_pairs)
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
                src, dst, rel = normalize_rel_pair(p)
                if src is not None and dst is not None:
                    pred_pairs[(src, dst)] = rel

        # Count MISSING and matches
        for (src, dst), true_rel in true_pairs.items():
            rel_total += 1
            pred_rel = pred_pairs.get((src, dst), "MISSING")
            if pred_rel == true_rel:
                rel_correct += 1
            if pred_rel == "MISSING":
                rel_missing += 1
            rel_confusion[true_rel][pred_rel] += 1

        # Count EXTRA (predicted but not in ground truth)
        for (src, dst) in pred_pairs:
            if (src, dst) not in true_pairs:
                rel_extra += 1

        r_acc = role_correct / role_total * 100 if role_total else 0
        l_acc = level_correct / level_total * 100 if level_total else 0
        rel_acc = rel_correct / rel_total * 100 if rel_total else 0
        n_pred = len(pred_pairs)
        n_true = len(true_pairs)
        print(f"  [{i+1}/{len(samples)}] Role:{r_acc:.1f}% Level:{l_acc:.1f}% Rel:{rel_acc:.1f}% (pred={n_pred}/true={n_true}) | text_id={text_id} ({time.time()-t0:.0f}s)")

    elapsed = time.time() - start_time

    # Results
    total = len(samples)
    print("\n" + "=" * 70)
    print(f"RESULTS: {MODEL} + v3 (2-Pass + 2 Few-Shot + Concise Prompts)")
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
        missing_pct = rel_missing / rel_total * 100
        print(f"\n5. Relationship: {rel_correct}/{rel_total} ({rel_correct/rel_total*100:.1f}%)")
        print(f"   MISSING: {rel_missing}/{rel_total} ({missing_pct:.1f}%) — target: <30%")
        print(f"   EXTRA (predicted but not in GT): {rel_extra}")
        for rel in sorted(rel_confusion.keys()):
            preds = rel_confusion[rel]
            t = sum(preds.values())
            c = preds.get(rel, 0)
            m = preds.get("MISSING", 0)
            top_misclass = [(k, v) for k, v in preds.most_common(4) if k != rel][:3]
            mis_str = ", ".join(f"{k}={v}" for k, v in top_misclass)
            print(f"     {rel:20s}: {c:3d}/{t:3d} = {c/t*100:5.1f}%  (MISSING={m})  {f'  ← {mis_str}' if mis_str else ''}")

    print(f"\nElapsed: {elapsed:.0f}s ({elapsed/total:.0f}s/sample)")

    # Comparison
    print("\n" + "=" * 70)
    print("COMPARISON (10-sample baselines)")
    print("=" * 70)
    r_pct = role_correct/role_total*100 if role_total else 0
    l_pct = level_correct/level_total*100 if level_total else 0
    rel_pct = rel_correct/rel_total*100 if rel_total else 0
    print(f"{'Metric':<25s} {'1-pass':>8s} {'2p+fs':>8s} {'v3':>8s} {'Target':>8s}")
    print("-" * 60)
    print(f"{'Structural Role':<25s} {'57.7%':>8s} {'66.2%':>8s} {f'{r_pct:.1f}%':>8s} {'68%+':>8s}")
    print(f"{'Hierarchical Level':<25s} {'81.7%':>8s} {'71.8%':>8s} {f'{l_pct:.1f}%':>8s} {'78%+':>8s}")
    print(f"{'Main Sentence F1':<25s} {'0.667':>8s} {'0.571':>8s} {f'{mf:.3f}':>8s} {'0.65+':>8s}")
    print(f"{'Relationship':<25s} {'26.1%':>8s} {'23.2%':>8s} {f'{rel_pct:.1f}%':>8s} {'35%+':>8s}")
    if rel_total:
        print(f"{'Rel MISSING %':<25s} {'--':>8s} {'54%':>8s} {f'{missing_pct:.0f}%':>8s} {'<30%':>8s}")

    # Save
    out = {
        "model": MODEL, "prompt": "v3_2pass_2fewshot_concise",
        "total": total,
        "json_parse_pass1": json_ok_p1/total,
        "json_parse_pass2": json_ok_p2/total,
        "role_accuracy": role_correct/role_total if role_total else 0,
        "level_accuracy": level_correct/level_total if level_total else 0,
        "main_f1": mf,
        "rel_accuracy": rel_correct/rel_total if rel_total else 0,
        "rel_missing_pct": rel_missing/rel_total if rel_total else 0,
        "rel_extra": rel_extra,
        "role_confusion": {k: dict(v) for k, v in role_confusion.items()},
        "rel_confusion": {k: dict(v) for k, v in rel_confusion.items()},
        "elapsed_seconds": elapsed,
    }
    safe = MODEL.replace(":", "_").replace("/", "_")
    outfile = f"/home/code/structural_labeling/eval_{safe}_v3_{total}.json"
    with open(outfile, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {outfile}")


if __name__ == "__main__":
    main()

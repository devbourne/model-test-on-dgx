# Structural Role Analysis 평가 보고서

**작성일**: 2026-03-02
**작성 환경**: DGX Spark GB10 (128GB LPDDR5X), Ollama 0.17.4

---

## 1. 프로젝트 개요

수능 영어 지문의 문장별 구조적 역할 분석(Structural Role Analysis)을 위한 모델 성능 평가.

### 태스크 정의
하나의 영어 지문(평균 7~8문장)에 대해:
1. **Sentence Analysis**: 각 문장에 11종 structural_role + 4종 hierarchical_level 부여
2. **Main Sentence ID**: 핵심 주장 문장 식별
3. **Sentence Pairs**: 문장 간 10종 structural relationship 매핑 (src→dst)

### 이전 태스크(담화 관계)와의 차이

| 항목 | 이전: 담화 관계 (Discourse Relation) | 현재: 구조적 역할 (Structural Role) |
|------|------|------|
| **단위** | 인접 문장 쌍 1개 | 지문 전체 (7~8문장) |
| **출력** | 단일 레이블 1개 (11종 중 택1) | 복합 JSON (sentence_analysis + main_ids + sentence_pairs) |
| **관계 유형** | elaboration, sequence, result, contrast 등 11종 | explains, exemplifies, supports, contextualizes 등 10종 |
| **출력 토큰** | ~10 토큰 (단어 1개) | ~1,000~3,000 토큰 (복합 JSON) |
| **학습 데이터** | 6,947 문장쌍 (단순 분류) | 1,112 지문 (복합 생성) |
| **평가 방식** | 정확도(Accuracy) 1개 | 5개 메트릭 (JSON파싱, Role, Level, Main F1, Relationship) |

**핵심 차이**: 담화 관계는 "문장 A→B 관계가 뭐야?" → "elaboration" 같은 **단순 분류(classification)** 태스크.
구조적 역할 분석은 지문 전체를 읽고 **구조화된 JSON을 생성(generation)** 하는 훨씬 복잡한 태스크.

---

## 2. 평가 대상 모델 3종

### 2-1. QLoRA Fine-tuned (Qwen3-30B-A3B + LoRA)
- **베이스**: Qwen3-30B-A3B (MoE, 30B total / 3B active params)
- **학습**: 4-bit NF4 QLoRA, r=8, alpha=16, targets=[q_proj, v_proj]
- **데이터**: 889 train / 111 val 지문, MAX_SEQ_LENGTH=2048
- **학습 결과**: 1 epoch, 112 steps, eval_loss=0.4290
- **학습 곡선**:
  ```
  Step 10:  loss=1.443
  Step 20:  loss=1.185
  Step 30:  loss=1.017
  Step 40:  loss=0.828
  Step 50:  loss=0.641  eval_loss=0.532
  Step 60:  loss=0.499
  Step 70:  loss=0.459
  Step 80:  loss=0.457
  Step 90:  loss=0.435
  Step 100: loss=0.439  eval_loss=0.429 ← best
  Step 110: loss=0.445
  ```

### 2-2. qwen3:30b + Compact Prompt (프롬프트 튜닝)
- **모델**: Qwen3-30B-A3B 원본 (학습 없음)
- **프롬프트**: Refined Compact Prompt (role disambiguation 규칙 포함)
- **옵션**: /no_think, temperature=0, num_predict=8192

### 2-3. gpt-oss:120b + Compact Prompt (프롬프트 튜닝)
- **모델**: GPT-OSS 120B 원본 (학습 없음)
- **프롬프트**: 동일한 Refined Compact Prompt
- **옵션**: temperature=0, num_predict=8192

---

## 3. 평가 결과 (10-sample test set)

### 3-1. 종합 비교

| 메트릭 | QLoRA Fine-tuned | qwen3:30b Prompt | gpt-oss:120b Prompt |
|--------|:---:|:---:|:---:|
| **JSON Parse Rate** | **100%** | 90% | **100%** |
| **Structural Role Accuracy** | 53.5% | **66.2%** | 57.7% |
| **Hierarchical Level Accuracy** | **83.1%** | 78.9% | 81.7% |
| **Main Sentence F1** | 0.636 | **0.700** | 0.667 |
| **Relationship Accuracy** | 7.2% | 24.6% | **26.1%** |

### 3-2. Structural Role 세부 (11종)

| Role | 빈도 | QLoRA | qwen3:30b Prompt | gpt-oss:120b Prompt |
|------|:---:|:---:|:---:|:---:|
| Illustration | 13 | 76.9% (10/13) | **100%** (13/13) | 84.6% (11/13) |
| Explanation | 12 | 58.3% (7/12) | **100%** (12/12) | 50.0% (6/12) |
| Main Claim | 9~11 | 63.6% (7/11) | **77.8%** (7/9) | 63.6% (7/11) |
| Background | 8~9 | **77.8%** (7/9) | 75.0% (6/8) | 66.7% (6/9) |
| Evidence | 7~10 | 30.0% (3/10) | 0% (0/7) | **40.0%** (4/10) |
| Consequence | 4 | 25.0% (1/4) | 25.0% (1/4) | **75.0%** (3/4) |
| Conclusion | 4 | 25.0% (1/4) | **75.0%** (3/4) | 25.0% (1/4) |
| Contrast | 3 | 66.7% (2/3) | **100%** (3/3) | 66.7% (2/3) |
| Evaluation | 2 | 0% (0/2) | **50.0%** (1/2) | 0% (0/2) |
| Comparison | 2 | 0% (0/2) | **50.0%** (1/2) | **50.0%** (1/2) |
| Definition | 1 | 0% (0/1) | 0% (0/1) | 0% (0/1) |

### 3-3. Relationship 세부 (10종)

| Relationship | 빈도 | QLoRA | qwen3:30b Prompt | gpt-oss:120b Prompt |
|------|:---:|:---:|:---:|:---:|
| explains | 16~17 | 0% (0/17) | **37.5%** (6/16) | 23.5% (4/17) |
| exemplifies | 13 | 15.4% (2/13) | **46.2%** (6/13) | **53.8%** (7/13) |
| supports | 9~11 | 0% (0/11) | 0% (0/9) | **18.2%** (2/11) |
| contextualizes | 8~10 | 10.0% (1/10) | **50.0%** (4/8) | 20.0% (2/10) |
| extends | 6 | 0% (0/6) | 0% (0/6) | **33.3%** (2/6) |
| contrasts | 4~5 | 20.0% (1/5) | 0% (0/4) | **20.0%** (1/5) |
| concludes | 4 | 25.0% (1/4) | **25.0%** (1/4) | 0% (0/4) |
| compares | 2 | 0% (0/2) | 0% (0/2) | 0% (0/2) |
| evaluates | 1 | 0% (0/1) | 0% (0/1) | 0% (0/1) |

### 3-4. QLoRA Confusion Matrix 주요 패턴

**Role confusion (QLoRA)**:
```
Evidence(10) → Explanation(4), Evidence(3), Contrast(1), Consequence(1), Illustration(1)
Conclusion(4) → Consequence(3), Conclusion(1)  ← Consequence와 혼동
Evaluation(2) → Explanation(2)                 ← 전부 Explanation으로 예측
Comparison(2) → Illustration(1), Explanation(1) ← 전부 오분류
```

**Relationship confusion (QLoRA)**:
```
explains(17) → exemplifies(10), MISSING(5)     ← 대부분 exemplifies로 오분류
supports(11) → exemplifies(6), MISSING(4)      ← exemplifies 과잉 예측
exemplifies(13) → illustrates(7), MISSING(4)   ← "illustrates" 존재하지 않는 라벨 생성
contextualizes(10) → MISSING(6), concludes(2)  ← 대부분 누락
```

---

## 4. 이전 담화 관계 QLoRA와의 비교

### 4-1. 담화 관계(Discourse) QLoRA 결과 (50-sample)

| 모델 | 태스크 | Accuracy |
|------|------|:---:|
| Qwen3-30B-A3B QLoRA | 담화 관계 분류 (11종) | **84.0%** |
| gpt-oss:120b prompt | 담화 관계 분류 (11종) | 62.0~64.0% |
| Qwen3-30B-A3B QLoRA (refined) | 담화 관계 분류 (11종) | 60.0% ← **과적합** |

### 4-2. 구조적 역할(Structural) QLoRA 결과 (10-sample)

| 모델 | Role Acc | Level Acc | Main F1 | Rel Acc |
|------|:---:|:---:|:---:|:---:|
| Qwen3-30B-A3B QLoRA | 53.5% | 83.1% | 0.636 | **7.2%** |
| qwen3:30b prompt | **66.2%** | 78.9% | **0.700** | 24.6% |
| gpt-oss:120b prompt | 57.7% | 81.7% | 0.667 | **26.1%** |

### 4-3. 핵심 관찰

**담화 관계 QLoRA**: 단순 분류(elaboration 등 1단어 출력)이므로 학습 효과 좋음 → 84% 정확도 달성
**구조적 역할 QLoRA**: 복합 JSON 생성 태스크인데 학습 모델이 프롬프트 튜닝보다 못함

---

## 5. QLoRA가 프롬프트 튜닝보다 못한 원인 분석

### 5-1. 치명적 원인: 토큰 제한에 의한 학습 데이터 절단 (Truncation)

**학습 데이터 크기 분석**:
```
총 문자 수 (system + user + assistant):
  평균:  10,115 chars ≈ 2,529 토큰
  중앙값: 10,013 chars ≈ 2,503 토큰
  최소:   7,546 chars ≈ 1,887 토큰
  최대:  19,911 chars ≈ 4,978 토큰
  p90:   11,518 chars ≈ 2,880 토큰
  p95:   12,248 chars ≈ 3,062 토큰

8,192 chars(≈2,048 토큰) 초과 샘플: 865/889 = 97.3%
```

**MAX_SEQ_LENGTH = 2048 토큰으로 학습했으므로, 97.3%의 샘플이 잘림.**

JSON 출력 구조:
```json
{
  "text_id": ...,
  "sentence_analysis": [...],   ← 앞부분 → 학습됨
  "main_sentence_ids": [...],   ← 중간 → 부분 학습
  "sentence_pairs": [...]       ← 뒷부분 → 대부분 잘려나감
}
```

**Assistant 출력만의 크기**: 평균 4,528 chars ≈ 1,132 토큰.
System(3,122 chars) + User(2,155 chars) = 약 1,319 토큰이 입력에 사용되므로,
**출력에 할당되는 토큰은 약 729개** → 실제 필요한 1,132 토큰의 **64%만 학습**.

결과:
- `sentence_analysis` (JSON 앞부분): 비교적 잘 학습됨 → Role 53.5%, Level 83.1%
- `sentence_pairs` (JSON 뒷부분): 거의 학습 안됨 → Relationship **7.2%**
- `main_sentence_ids` (중간): 절반정도 학습 → F1 0.636

### 5-2. 과적합 (Overfitting) 패턴

**Relationship에서 "exemplifies" 과잉 예측**:
- explains(17개) → exemplifies로 10개 오분류
- supports(11개) → exemplifies로 6개 오분류
- 학습 데이터에서 exemplifies가 18.3%로 빈도 높음 + 앞부분에 위치할 가능성 높음

**존재하지 않는 라벨 "illustrates" 생성**:
- exemplifies(13개) → "illustrates"로 7개 오분류
- Structural Role의 "Illustration"과 혼동하여 자체적으로 라벨 생성
- 학습이 불완전하여 role 라벨과 relationship 라벨이 섞인 것

### 5-3. 태스크 복잡도 차이

| 차원 | 담화 관계 | 구조적 역할 |
|------|------|------|
| 입력 복잡도 | 문장 2개 | 문장 7~8개 전체 |
| 출력 복잡도 | 1 토큰 | ~1,000+ 토큰 |
| 구조적 이해 | 지역적 (인접 쌍) | 전역적 (전체 지문) |
| JSON 구조 | 없음 | 중첩 구조 3계층 |
| 학습 효율 | 높음 (전체 출력 학습) | 극히 낮음 (64%만 학습) |

### 5-4. LoRA 구성의 한계

- **r=8, targets=[q_proj, v_proj]만**: OOM 때문에 k_proj, o_proj 제외
- 전체 파라미터의 매우 적은 부분만 학습 → 복잡한 구조 생성 능력 부족
- MoE 모델에서 전문가(expert) 게이트는 학습 안됨

### 5-5. 프롬프트 튜닝이 더 나은 이유

프롬프트 튜닝 (qwen3:30b, gpt-oss:120b)은:
- **토큰 제한 없음**: num_predict=8192로 전체 JSON 생성 가능
- **모든 파라미터 활용**: 베이스 모델의 전체 지식과 추론 능력 사용
- **Role Disambiguation 규칙**: 프롬프트에 명시적 구분 규칙 포함
- **사전학습 지식**: 영어 구조 분석에 대한 기존 지식 활용

---

## 6. 이전 담화 QLoRA의 과적합 문제 재확인

담화 관계에서도 QLoRA refined 버전이 60%로 급락한 사례가 있었음:

```
qwen3-30b-qlora (refined): 60% accuracy
  → elaboration: 30/30 = 100%  (다른 클래스 전부 elaboration으로 예측)
  → sequence: 0/9 = 0%
  → result: 0/3 = 0%
  → 모든 비-elaboration 클래스 = 0%
```

이것은 **완전한 mode collapse** — elaboration이 60%를 차지하는 데이터 불균형에 의해
모델이 "전부 elaboration이라고 하면 60%는 맞음"이라는 최적해에 수렴한 것.

현재 구조적 역할 QLoRA에서도 유사한 패턴:
- Relationship에서 exemplifies 과잉 (MISSING 다수 = 생성 자체를 포기)
- Role에서 Explanation 과잉 (Evidence/Evaluation을 Explanation으로 오분류)

---

## 7. 개선 방안

### 방안 A: 학습 데이터 최적화 (QLoRA 재학습)

**A-1. MAX_SEQ_LENGTH 확장** (가장 중요)
```
현재: 2048 → 목표: 4096 이상
```
- 97.3%가 잘리는 현재 상태는 학습 자체가 불가능
- DGX Spark 128GB에서 4096은 가능할 수 있음 (gradient_checkpointing + batch_size=1)
- 불가능하면 8192/4096 두 단계로 시도

**A-2. JSON 출력 압축**
sentence_pairs에서 reasoning/reasoning_ko 제거 → 토큰 40~50% 절약:
```json
// Before (per pair): ~80 tokens
{"src_sentence_id": 2, "dst_sentence_id": 1, "relationship": "contextualizes",
 "confidence": "high", "reasoning": "S1 provides background...",
 "reasoning_ko": "S1이 배경을 제공..."}

// After (per pair): ~20 tokens
{"src": 2, "dst": 1, "rel": "contextualizes", "conf": "high"}
```

**A-3. 태스크 분리 학습**
sentence_analysis와 sentence_pairs를 별도 모델/어댑터로 분리:
- Model A: sentence_analysis + main_sentence_ids (짧은 출력)
- Model B: sentence_pairs only (관계만 집중)

**A-4. LoRA 확장**
OOM 허용 범위 내에서:
- r=16, targets=[q_proj, k_proj, v_proj, o_proj]
- 또는 r=8 유지하면서 gate_proj, up_proj 추가

### 방안 B: 프롬프트 고도화 (학습 없이)

**B-1. Few-shot 예시 추가**
시스템 프롬프트에 1~2개 완전한 예시 포함:
```
## Example:
Input: [sentences]
Output: {complete JSON}
```
→ 모델이 정확한 출력 형태를 학습

**B-2. Role별 판별 기준 강화**
현재 프롬프트의 Role Disambiguation을 더 구체화:
```
Evidence vs Explanation 판별법:
- "연구에 따르면", "X%가", 수치 포함 → Evidence
- "왜냐하면", "이는 ~하기 때문" → Explanation
- 구체적 사람/기관 이름 → Evidence or Illustration
```

**B-3. 2-pass 생성**
1차: sentence_analysis + main_sentence_ids 생성
2차: 1차 결과를 입력에 포함시켜 sentence_pairs 생성
→ 각 단계가 더 짧은 출력으로 정확도 향상

**B-4. Relationship 지시 개선**
```
RELATIONSHIP 결정 순서:
1. main_sentence_ids의 문장이 src가 되는 관계를 먼저 찾아라
2. Background → Main Claim: "contextualizes"
3. Main Claim → Evidence/Illustration: "supports"/"exemplifies"
4. 같은 레벨의 문장끼리는 관계를 만들지 마라
```

### 방안 C: 하이브리드 (권장)

**1단계 (즉시 가능)**: 프롬프트 B-1 + B-3 적용 → gpt-oss:120b에서 평가
**2단계**: 프롬프트 결과가 좋으면, 그 출력을 "정제된 학습 데이터"로 사용
**3단계**: 압축된 JSON (A-2) + 확장 seq_length (A-1)로 QLoRA 재학습
**4단계**: QLoRA 모델과 프롬프트 모델을 앙상블 (다수결)

---

## 8. 우선순위 권장

| 순위 | 방안 | 기대 효과 | 난이도 | 소요 시간 |
|:---:|------|:---:|:---:|:---:|
| 1 | B-3: 2-pass 생성 | Role↑10%, Rel↑15% | 낮음 | 1시간 |
| 2 | B-1: Few-shot 예시 | Role↑5%, Rel↑10% | 낮음 | 1시간 |
| 3 | A-2: JSON 압축 + A-1: seq_length 확장 | 전체↑20% | 중간 | 4시간 (학습) |
| 4 | A-3: 태스크 분리 | Rel↑25% | 높음 | 8시간 |

**즉시 실행 권장**: B-3 (2-pass) + B-1 (few-shot)을 gpt-oss:120b에서 테스트
→ 현재 Rel 26.1%를 40%+ 목표

---

## 9. 데이터셋 통계 참고

### 구조적 역할 학습 데이터 (1,112 지문)
```
Structural Role 분포:
  Explanation:   1,866 (21.3%)
  Illustration:  1,461 (16.7%)
  Main Claim:    1,242 (14.2%)
  Background:    1,176 (13.4%)
  Evidence:      1,120 (12.8%)
  Consequence:     666 (7.6%)
  Contrast:        357 (4.1%)
  Definition:      269 (3.1%)
  Conclusion:      235 (2.7%)
  Evaluation:      217 (2.5%)
  Comparison:      148 (1.7%)

Relationship 분포:
  explains:       2,217 (26.3%)
  exemplifies:    1,547 (18.3%)
  supports:       1,464 (17.4%)
  contextualizes: 1,270 (15.1%)
  extends:          894 (10.6%)
  contrasts:        444 (5.3%)
  concludes:        237 (2.8%)
  defines:          178 (2.1%)
  evaluates:        111 (1.3%)
  compares:          72 (0.9%)
```

### 이전 담화 관계 학습 데이터 (6,947 쌍)
```
Discourse Relation 분포:
  elaboration:   3,327 (47.9%)  ← 압도적 다수
  result:        1,008 (14.5%)
  sequence:        932 (13.4%)
  contrast:        616 (8.9%)
  generalization:  330 (4.8%)
  cause:           266 (3.8%)
  restatement:     186 (2.7%)
  concession:      116 (1.7%)
  condition:        83 (1.2%)
  comparison:       62 (0.9%)
  none:             21 (0.3%)
```

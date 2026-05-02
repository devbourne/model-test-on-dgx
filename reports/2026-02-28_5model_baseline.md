# DGX Spark - Ollama LLM 모델 벤치마크 비교 보고서

**테스트 환경**
- Hardware: NVIDIA DGX Spark (GB10, 128GB 통합 메모리)
- GPU Driver: 580.126.09 / CUDA 13.0
- Architecture: aarch64
- Ollama: v0.17.4
- 테스트 일자: 2026-02-28

---

## 1. 테스트 모델 요약

| 순위 | 모델 | 크기 | 아키텍처 | 파라미터 | 활성 파라미터 |
|:----:|------|------|----------|----------|-------------|
| 1 | gpt-oss:120b | 65 GB (MXFP4) | MoE 128전문가 | 117B | 5.1B |
| 2 | qwen3:30b | 18 GB (Q4_K_M) | MoE | 30B | 3B |
| 3 | gemma3:27b | 17 GB (Q4_K_M) | Dense | 27B | 27B |
| 4 | mistral-large:123b | 73 GB (Q4_K_M) | Dense | 123B | 123B |
| 5 | deepseek-r1:70b-llama-distill-q8_0 | 74 GB (Q8_0) | Dense | 70B | 70B |

---

## 2. 기본 성능 테스트 (한국어 단답형)

**프롬프트**: "한국의 수도는 어디이며, 그 역사적 배경을 3문장으로 설명해주세요."

### gpt-oss:120b
- **응답**: 한국의 수도는 서울입니다. 한양(현재의 서울)은 조선 시대인 1394년에 새 왕조의 수도로 선정되어 약 500년간 정치·문화의 중심지 역할을 했으며, 일제 강점기에는 경성으로 개칭되어 근대 도시 기반이 확립되었습니다. 1945년 광복 이후와 1948년 대한민국 정부 수립을 거쳐 현재까지도 국가 행정·경제·문화의 핵심 도시로 자리하고 있습니다.
- **한국어 품질**: 자연스럽고 정확한 한국어

### deepseek-r1:70b q8_0
- **응답**: 한국의 수도는 서울입니다. 서울은 1392년 조선 대에 태종 이방원에 의해 한양으로 지명되었으며... 1897년 대한제국 시기에京城(경성)으로 이름을 바꾼 서울은 일제 강점기인 1945년 해방 이후 현대적인 수도として 재兴업되었습니다.
- **한국어 품질**: 한자(京城, として, 兴) 혼재, 일본어 혼입

### 성능 비교

| 지표 | gpt-oss:120b | deepseek-r1:70b |
|------|:-----------:|:---------------:|
| 모델 로드 | 32.4s | 1m 9s |
| 프롬프트 처리 | 305.89 tok/s | 31.08 tok/s |
| 생성 속도 | 42.73 tok/s | 2.57 tok/s |
| 총 소요 시간 | 36.8s | 3m 23.9s |
| 생성 토큰 수 | 168 | 344 (thinking 포함) |

---

## 3. 수능 영어 독해 분석 테스트 (핵심 비교)

### 테스트 지문
"Digital platforms have made a lot of work less sticky. As work becomes ever more modularised, commoditised and standardised, and as markets for digital work are created, ties between service work and particular places can be disconnected. While the business process of outsourcing that emerged in the 1990s allowed large companies to take advantage of a 'global reserve army' by moving their call centres to cheap and distant labour markets, cloudwork changes the volume and granularity at which geographically non-proximate work can take place. A small business in New York can hire a freelance transcriber in Nairobi one day and New Delhi the next. No offices or factories need to be built, no local regulations are observed, and in most cases no local taxes are paid. The switch in the production network of work happens by simply sending some emails or clicking some buttons on a digital work platform. And, in this way, the employer leaves behind no material traces in the places where it was once an employer."

### 프롬프트
8개 분석 항목 (주제, 요지, 제목, 논리 구조, 핵심 어휘 10개, 빈칸 추론, 선지 함정, 한 줄 요약)을 한국어로 작성하도록 지시.

---

### 3-1. gpt-oss:120b 분석 결과

**1. 주제**: 디지털 플랫폼이 노동을 '끈끈함(sticky)'에서 탈피시키며, 지리적·제도적 제약 없이 '클라우드워크' 형태로 전 세계에 '비물질적 고용 관계'를 만든다.

**2. 요지**: 디지털 플랫폼을 통한 '클라우드워크'는 업무를 모듈화·표준화·상품화시켜, 기업이 물리적 사무실·공장·현지 규제·세금을 거치지 않고 언제든 전 세계 프리랜서를 고용할 수 있게 함으로써 고용주의 지역적 흔적을 완전히 사라지게 만든다.

**3. 제목**:
1) "디지털 플랫폼이 만든 무형의 글로벌 고용 네트워크"
2) "클라우드워크: 지리적 제약을 초월한 노동의 새 패러다임"

**4. 논리 구조**: 7단계 표 형식 (도입→현상→과거→전환→예시→결과→결론)

**5. 핵심 어휘**: 10개 완벽 제시 (sticky, modularised, commoditised, global reserve army, cloudwork, granularity, freelance transcriber, local regulations, material traces, production network)

**6. 빈칸 추론**:
- "work becomes ever more **modularised**..." → 모듈화·상품화·표준화 연속 어휘
- "no local **taxes** are paid" → 나열 구조의 문맥적 답

**7. 선지 함정**:
1. 'sticky'의 물리적 의미 오해 (접착제 → 실제는 '고정된' 비유)
2. 'global reserve army' ≠ 'global workforce' (마르크스적 용어)
3. 'material traces' ≠ 'financial traces' (물리적 흔적)

**8. 한 줄 요약**: 디지털 플랫폼의 '클라우드워크'는 업무를 모듈화·표준화해 전 세계 어디서든 클릭만으로 고용할 수 있게 함으로써, 기업이 지역적 물리·제도적 흔적을 완전히 없애는 새로운 고용 패러다임을 제시한다.

---

### 3-2. qwen3:30b 분석 결과

**1. 주제**: 디지털 플랫폼을 통한 작업의 지리적 연결 해체와 글로벌 클라우드 워크의 확산으로 인한 기업의 물리적 흔적 소멸.

**2. 요지**: 디지털 플랫폼이 작업을 모듈화·상품화·표준화시켜 지리적 제약을 해소하고, 기업이 현지 규제·세금·물리적 시설 없이 글로벌 프리랜서와 연결되며 과거 고용자로서의 물리적 흔적을 남기지 않는 구조적 전환을 이끌고 있음을 강조한다.

**3. 제목**:
1) "디지털 플랫폼과 글로벌 클라우드 워크: 지리적 고정성의 해체"
2) "무형의 작업 네트워크: 디지털 시대의 기업 구조 변화"

**4. 논리 구조**: 5단계 상세 분석 (문제 제시→역사적 비교→구체적 예시→장점 강조→결론)

**5. 핵심 어휘**: 10개 완벽 제시 (modularised, commoditised, geographically non-proximate, global reserve army, freelance, transcriber, material traces, production network, standardised, outsource)

**6. 빈칸 추론**:
- "work becomes ever more **modularised**..." → 형용사 의미 일치 유형
- "work can take place **geographically non-proximate**" → 복합어 의미 추론

**7. 선지 함정**:
1. "global reserve army" = 실제 군대 (오답: 노동력 예비 풀 은유)
2. "cloudwork" = 클라우드 컴퓨팅 (오답: 디지털 플랫폼 기반 작업)
3. "material traces" = 기업의 재무적 흔적 (오답: 물리적 시설)

**8. 한 줄 요약**: 디지털 플랫폼은 작업을 모듈화·상품화·표준화시켜 지리적 제약을 해소하고, 기업이 현지 규제·세금 없이 글로벌 프리랜서와 연결되며 과거 고용자로서의 물리적 흔적을 남기지 않는 구조적 변화를 초래한다.

---

### 3-3. gemma3:27b 분석 결과

**1. 주제**: 디지털 플랫폼의 발전으로 인해 노동 시장과 고용 방식이 변화하는 현상.

**2. 요지**: 디지털 플랫폼은 노동을 더욱 세분화하고 표준화하여, 기업이 지리적 제약 없이 전 세계의 노동력을 활용할 수 있도록 만들고 있으며, 이는 전통적인 고용 방식의 변화와 더불어 지역 경제에 미치는 영향에 대한 고찰을 필요로 한다.

**3. 제목**:
1) "디지털 플랫폼과 노동 시장의 재편"
2) "보이지 않는 고용: 디지털 플랫폼 시대의 노동 변화"

**4. 논리 구조**: 3단계 분석 (현상 소개→아웃소싱과의 차이→물리적 흔적 부재 결론)

**5. 핵심 어휘**: 10개 제시 (sticky, modularised, commoditised, non-proximate, granularity, reserve army, material traces, outsourcing, cloudwork, **frictionless**)
- **주의**: 'frictionless'는 원문에 없는 어휘 (환각/hallucination). "문맥상 추론 가능"이라고 부연했으나, 실제 지문에는 등장하지 않음.

**6. 빈칸 추론**:
- "the employer leaves behind no **material traces**..." → 물리적 흔적 부재 강조
- "cloudwork changes the **volume and granularity**..." → 변화의 양/정도 표현

**7. 선지 함정**: 내용 수준(content-level) 함정 분석이 특징적
1. '디지털 플랫폼은 노동의 질을 향상시킨다' (오답: 노동 방식 변화만 다룸)
2. '아웃소싱과 클라우드워크는 동일 개념' (오답: 규모와 정교함의 차이)
3. '디지털 플랫폼은 지역 경제 활성화에 기여' (오답: 물리적 흔적 감소 → 부정적 암시)

**8. 한 줄 요약**: 디지털 플랫폼은 노동 시장을 지리적으로 분산시키고, 기업의 고용 방식을 변화시켜, 전통적인 고용 관계와 지역 경제에 새로운 영향을 미치고 있다.

---

### 3-4. mistral-large:123b 분석 결과

**1. 주제**: 디지털 플랫폼의 등장이 일의 위치와 성격에 미치는 변화.

**2. 요지**: 디지털 플랫폼이 일의 모듈화, 상품화, 표준화를 촉진하여 특정 장소와의 연결을 약화시키고, 글로벌 노동 시장에서 더 작은 규모와 세분화된 방식으로 일을 수행할 수 있게 했다. 또한, 지역적인 규제나 세금 문제를 피하고 물리적인 흔적을 남기지 않게 만든다.

**3. 제목**:
1) "디지털 플랫폼과 일의 장소적 분리"
2) "글로벌 노동 시장에서의 디지털 플랫폼의 영향"

**4. 논리 구조**: 5단계 문장별 분석 (주제 제시→모듈화 설명→아웃소싱 비교→예시→결론)

**5. 핵심 어휘**: 10개 제시 (modularised, commoditised, standardised, disconnected, outsourcing, global reserve army, granularity, geographically non-proximate, material traces, employer)
- **주의**: 'disconnected', 'employer'는 기본 어휘로 수능 출제 가능성 낮음. 'sticky', 'cloudwork', 'production network' 등 핵심 어휘 누락.

**6. 빈칸 추론**: 매우 약함
- "...hire a freelance transcriber in Nairobi one day and **New Delhi** the next" → 원문에 이미 있는 답을 제시 (빈칸 추론의 의도 미흡)
- "**Manila**" → 근거 없는 추측

**7. 선지 함정**:
1. 어휘 혼동: modularised/commoditised/standardised 차이
2. 문맥적 해석 오류: 'global reserve army'를 군사적 예비군으로 오해
3. 세부적인 내용 무시: 'material traces'를 디지털 데이터로 오해

**8. 한 줄 요약**: 디지털 플랫폼은 일의 모듈화와 상품화를 통해 특정 장소와의 연결을 약화시키고, 글로벌 노동력을 유연하게 활용할 수 있게 만든다.

---

### 3-5. deepseek-r1:70b q8_0 분석 결과

**응답 언어**: 영어 (한국어 지시 무시)

**1. Theme**: The passage explores how digital platforms have made work less location-dependent.

**2. Main Idea**: Digital platforms allow businesses to hire anyone worldwide, increasing efficiency and reducing costs by eliminating the need for physical offices.

**3~4**: 제목 없음, 논리 구조 1문장 요약

**5. Vocabulary**: 3개만 제시 (Modularised, Commoditised, Granularity)

**6. Blank Filling**: "Less sticky" and "global reserve army" (근거 미흡)

**7. Common Mistakes**: 3개 간략 제시

**8. Summary**: Digital platforms have transformed work into a flexible, global endeavor.

---

## 4. 종합 성능 비교표

### 4-1. 추론 속도

| 지표 | gpt-oss:120b | qwen3:30b | gemma3:27b | mistral-large:123b | deepseek-r1:70b |
|------|:-----------:|:---------:|:----------:|:-----------------:|:---------------:|
| 프롬프트 처리 (tok/s) | 305.89 | **1,987.46** | 806.16 | 135.03 | 31.08 |
| 생성 속도 (tok/s) | 42.73 | **75.28** | 11.48 | 2.02 | 2.57 |
| 수능 분석 총 시간 | ~47s | **~58s** | ~2m 6s | ~14m 26s | ~10분+ |
| 모델 로드 | 32.4s | 18.3s | 8.8s | 1m 31s | 1m 9s |

### 4-2. 분석 품질 평가 (5점 만점)

| 평가 항목 | gpt-oss:120b | qwen3:30b | gemma3:27b | mistral-large:123b | deepseek-r1:70b |
|-----------|:-----------:|:---------:|:----------:|:-----------------:|:---------------:|
| 한국어 지시 준수 | 5 | 5 | 5 | 5 | 2 |
| 8개 항목 완성도 | 5 | 5 | 5 | 5 | 2 |
| 핵심 어휘 (10개) | 5 (10개) | 5 (10개) | 4 (10개, 1개 환각) | 3 (10개, 기본 어휘 혼재) | 1 (3개) |
| 논리 구조 분석 | 5 (7단계) | 5 (5단계) | 4 (3단계) | 4 (5단계) | 1 (1문장) |
| 빈칸 추론 근거 | 5 | 5 | 5 | 2 (원문 답 반복) | 2 |
| 선지 함정 분석 | 5 | 5 | 5 | 4 | 3 |
| 제목 제시 | 5 (2개) | 5 (2개) | 5 (2개) | 4 (2개, 다소 평범) | 0 (없음) |
| 한국어 자연스러움 | 5 | 5 | 5 | 4 (합니다체) | 0 (영어 출력) |
| **평균** | **5.0** | **5.0** | **4.75** | **3.9** | **1.4** |

### 4-3. 효율성 비교

| 지표 | gpt-oss:120b | qwen3:30b | gemma3:27b | mistral-large:123b | deepseek-r1:70b |
|------|:-----------:|:---------:|:----------:|:-----------------:|:---------------:|
| 모델 크기 | 65 GB | **18 GB** | 17 GB | 73 GB | 74 GB |
| 품질/GB 효율 | 0.077 | **0.278** | 0.279 | 0.053 | 0.019 |
| 속도 (tok/s) | 42.73 | **75.28** | 11.48 | 2.02 | 2.57 |
| 속도/GB 효율 | 0.66 | **4.18** | 0.68 | 0.028 | 0.035 |

---

## 5. 모델별 특장점 요약

### gpt-oss:120b (OpenAI)
- **강점**: 최고 수준의 한국어 자연스러움, 'sticky' 비유적 의미 해석, 마르크스적 용어('global reserve army') 학술적 설명, MoE 아키텍처로 빠른 추론
- **약점**: 65GB로 다른 대형 모델과 동시 로드 제한적
- **적합 용도**: 범용 한국어 대화, 학술 분석, 수능 영어 분석

### qwen3:30b (Alibaba)
- **강점**: 18GB로 가장 가벼우면서 최고 품질, 생성 속도 75 tok/s로 최빠, 119개 언어 지원, thinking 모드 전환 가능, 'geographically non-proximate' 복합어 분석 우수
- **약점**: thinking 토큰이 포함되어 총 토큰 수 많음
- **적합 용도**: 다국어 분석, 수능 영어 분석, 논리 추론, 실시간 대화

### gemma3:27b (Google)
- **강점**: 17GB로 가장 가벼움, 한국어 지시 완벽 준수, 8개 항목 모두 완성, 내용 수준(content-level) 선지 함정 분석이 독창적, 128K 긴 컨텍스트 지원
- **약점**: 생성 속도 11.48 tok/s로 MoE 모델 대비 느림 (Dense 아키텍처), 'frictionless' 환각 어휘 포함 (원문에 없는 단어), 논리 구조 분석 3단계로 다소 단순
- **적합 용도**: 다국어 분석, 긴 문서 처리, 한국어 수능 분석 (준수한 품질)

### mistral-large:123b (Mistral AI)
- **강점**: 한국어 지시 준수, 8개 항목 모두 완성, Dense 123B의 높은 파라미터 수, 프롬프트 처리 135 tok/s
- **약점**: 생성 속도 2.02 tok/s로 최하위, 73GB 대형, 14분+ 소요, 빈칸 추론에서 원문 답 반복, 기본 어휘(disconnected, employer) 선정, 핵심 어휘(sticky, cloudwork) 누락
- **적합 용도**: 지시 따르기(Instruction following) 태스크 (단, DGX Spark에서는 속도 제약으로 비실용적)

### deepseek-r1:70b q8_0 (DeepSeek)
- **강점**: Chain-of-Thought 추론, 수학/코딩 특화
- **약점**: 한국어 지시 무시 (영어 출력), 2.57 tok/s 극도로 느림, 74GB 대형, 한자·일본어 혼입
- **적합 용도**: 수학 문제 풀이, 코딩 태스크 (한국어 태스크에는 부적합)

---

## 6. 종합 순위 (수능 영어 분석 태스크 기준)

| 순위 | 모델 | 품질 | 속도 | 효율 | 총평 |
|:----:|------|:----:|:----:|:----:|------|
| **1** | **qwen3:30b** | ★★★★★ | ★★★★★ | ★★★★★ | 가성비 최강, 모든 지표 최상위 |
| **2** | **gpt-oss:120b** | ★★★★★ | ★★★★☆ | ★★★☆☆ | 품질 최상, 크기 대비 효율 아쉬움 |
| **3** | **gemma3:27b** | ★★★★☆ | ★★★☆☆ | ★★★★☆ | 가벼운 크기, 준수한 품질, 속도 아쉬움 |
| **4** | mistral-large:123b | ★★★★☆ | ★☆☆☆☆ | ★☆☆☆☆ | 한국어 준수하나 극도로 느림, 비효율 |
| **5** | deepseek-r1:70b | ★★☆☆☆ | ★☆☆☆☆ | ★☆☆☆☆ | 한국어 태스크 부적합 |

---

*보고서 생성: 2026-02-28 | DGX Spark GB10 | Ollama v0.17.4*
*최종 업데이트: 5개 모델 벤치마크 완료 (gpt-oss:120b, qwen3:30b, gemma3:27b, mistral-large:123b, deepseek-r1:70b)*

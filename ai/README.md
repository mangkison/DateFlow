# DateFlow — AI Agent Pipeline

커플 데이트 코스 자동 생성 시스템의 **AI 에이전트 파트**입니다.

> 한국외국어대학교 컴퓨터공학부 졸업논문 캡스톤 프로젝트 

---

## 📌 한 줄 소개

> 사용자가 메인 이벤트를 선택하면, **역추론 설계**와 **더블체크 구조**로 시간대별 데이트 코스를 자동 생성하는 Deep Agent 시스템.

---

## 🎯 연구 동기

- 기존 데이트 정보 서비스는 **'단일 스팟 검색'**에 머물러, 예산·이동시간·두 사람 취향 교집합을 고려한 코스 단위 제안을 제공하지 못함
- 사용자가 실제로 사용하는 **'메인 이벤트를 먼저 결정하고, 그로부터 역산해서 코스를 구성하는'** 사고 과정을 시스템화하여 인지 부하 감소
- LLM의 할루시네이션 위험을 사실 검증 계층(check_hours 더블체크)에 **내재화**

---

## 🏗 시스템 구조 — 이단계 파이프라인

```
[입력: 자연어 + 통합 취향 + 날씨 + 크롤링 데이터]
            ↓
[Pipeline 1] 메인 이벤트 추천
   LLM → search_events → 3~5개 이벤트
            ↓
   👤 사용자가 메인 이벤트 선택
            ↓
[Pipeline 2] 코스 생성 (ReAct + 더블체크)
   LLM → search_places → get_place_info
        → check_hours ① → 코스 구성
        → check_hours ② (최종 재검증)
            ↓
[출력: 시간대별 데이트 코스 (A안 / B안)]
```

---

## 🔧 에이전트 툴

| 툴 | 데이터 소스 | 역할 |
|---|---|---|
| `search_events` | Kakao Local API | 공연·전시·팝업 등 메인 이벤트 검색 (`place_id`, `place_url` 포함) |
| `search_places` | Kakao Local API | 코스 주변 카페·식당·산책지 검색 (`place_id`, `place_url` 포함) |
| `get_place_info` | Kakao Local API | 주소·전화·카카오맵 링크 |
| `check_hours` | Kakao Map (Playwright) | 실시간 영업시간 검증 + 30분 TTL 캐시 |
| `search_rag` | (예정) FAISS + Google Embedding | 취향 벡터 기반 장소 검색 — 크롤링 데이터 입수 후 활성화 |

---

## ✨ 주요 설계 포인트

### 더블체크 구조
영업시간 검증을 두 번 수행 (`check_hours ①, ②`):
- ①: 코스 생성 직전 1차 검증
- ②: 코스 확정 직전 최종 재검증
- 2차 호출은 **30분 TTL 캐시 적중으로 0ms 응답** → 정확도 강화하면서도 추가 비용 사실상 0

### 관측성 (Observability)
세션 단위 JSONL 로그 (`logs/sessions/<session_id>.jsonl`)에
ReAct 루프의 모든 호출 시퀀스·응답 시간·결과 자동 기록

---

## 🚀 실행 방법

### 1. 가상환경 + 의존성 설치

### 2. API 키 설정
`.env.example`을 `.env`로 복사 후 실제 키 입력:
```bash
cp .env.example .env
```

필요한 키:
- `GOOGLE_API_KEY` — Gemini API
- `KAKAO_KEY` — 카카오 REST API



### 3. 실행

**백엔드 통합 시뮬레이션 (권장)** — FastAPI가 진입점 함수를 호출하는 흐름을 재현:
```bash
python -m examples.mock_backend
```
`examples/dummy_p1_request.json`, `dummy_p2_request.json`을 읽어
`recommend_events()` → `generate_course()`를 순차 호출하고 결과 dict를 출력합니다.

**진입점 단위 테스트**:
```bash
python -m tests.test_recommend_events   # Pipeline 1
python -m tests.test_generate_course    # Pipeline 2
```

**툴 단독 테스트**:
```bash
python -m tests.test_check_hours        # Playwright 크롤링
```

> 백엔드 연동 명세는 [`API_SPEC.md`](./API_SPEC.md) 참고.

---

## 📂 폴더 구조

```
ai/
├── agents/
│   ├── shared.py                  # LLM 공통 초기화 (Gemini 2.5 Flash)
│   ├── pipeline1.py               # 메인 이벤트 추천 + recommend_events() 진입점
│   └── pipeline2.py               # 코스 생성 + generate_course() 진입점
│
├── tools/
│   ├── search.py                  # search_places (카카오 로컬)
│   ├── event.py                   # search_events (카카오 로컬)
│   ├── hours.py                   # get_place_info (카카오 로컬)
│   ├── check_hours.py             # check_hours (Playwright 크롤링 + 30분 캐시)
│   ├── rag.py                     # search_rag (FAISS, 인덱스 데이터 입수 후 활성화)
│   └── logger.py                  # 세션 로깅 데코레이터 (@log_tool)
│
├── examples/                      # 백엔드 통합 시뮬레이션
│   ├── mock_backend.py            # FastAPI 엔드포인트 시뮬레이션
│   ├── dummy_p1_request.json      # Pipeline 1 요청 예시
│   └── dummy_p2_request.json      # Pipeline 2 요청 예시
│
├── tests/
│   ├── test_recommend_events.py   # Pipeline 1 진입점 테스트
│   ├── test_generate_course.py    # Pipeline 2 진입점 테스트
│   └── test_check_hours.py        # check_hours 단독 테스트
│
├── logs/sessions/                 # 세션별 JSONL 로그 (자동 생성)
│
├── API_SPEC.md                    # 백엔드 연동 명세 (입출력 스키마)
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📚 기술 스택

- **LLM**: Gemini 2.5 Flash
- **Agent Framework**: deepagents (LangChain + LangGraph 기반)
- **크롤링**: Playwright (Chromium headless)
- **API**: 카카오 로컬·Map
- **언어**: Python 3.12

---

## 📈 현재 상태

- ✅ MVP 동작 (`test_pipeline2`로 통합 검증됨)
- ✅ ReAct 루프 + 더블체크 구조 구현
- ⬜ RAG (FAISS + ko-sroberta-multitask) — 크롤링 데이터 입수 후 구현 예정
- ⬜ 사용자 평가 / Ablation study — 향후 진행

---

## 📄 졸업논문

본 파이프라인을 다룬 졸업논문은 **2026년 6월 초** 공개 예정입니다.

---

## ⚠️ 주의

- `.env`에 API 키 들어가니 절대 git에 커밋하지 마세요 (`.gitignore`에 포함됨)
- `check_hours`는 카카오맵 페이지를 크롤링하므로, 과도한 호출 시 IP 제한 위험이 있습니다 (30분 캐시로 완화 중)

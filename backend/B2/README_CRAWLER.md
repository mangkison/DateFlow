# DateFlow — 안전한 웹 정보 수집 모듈

## 법적·윤리적 제약

| 항목 | 내용 |
|------|------|
| robots.txt | 모든 요청 전 `/robots.txt` 준수 확인 |
| 요청 간격 | 도메인별 최소 1초 (robots.txt `Crawl-delay` 우선) |
| 응답 크기 | 500 KB 초과 시 자동 중단 |
| User-Agent | `DateFlowBot/1.0` 명시 + 연락처 포함 |
| 개인정보 | 이메일·전화번호 자동 치환 후 저장 |
| 상업적 플랫폼 | 네이버·카카오·인스타그램 등 → 공식 API 사용 권장 |
| 완전 차단 | 쿠팡·배달의민족 등 ToS 명시 금지 도메인 |

## 파일 구조

```
app/
├── routers/
│   └── crawl_router.py        # POST /crawl/check-source, /fetch, /analyze-url
├── services/
│   ├── safe_crawler.py        # httpx 비동기 수집 + rate limiting
│   ├── source_policy.py       # robots.txt 체크 + 도메인 정책
│   ├── content_cleaner.py     # HTML → 정제 텍스트, 개인정보 제거
│   └── freshness_checker.py   # 발행일 추출 + 신선도 점수
└── schemas/
    └── crawl_schema.py        # Pydantic 요청/응답 모델
```

## API 엔드포인트

### `POST /crawl/check-source`
실제 페이지를 가져오지 않고 수집 가능 여부만 확인한다.

```json
// Request
{ "url": "https://example.com/article/123" }

// Response
{
  "url": "https://example.com/article/123",
  "status": "allowed",
  "reason": "수집 허용",
  "crawl_delay_seconds": 1.0
}
```

### `POST /crawl/fetch`
정책 검사 → 수집 → 정제 → 신선도 평가를 순차 실행한다.

```json
// Request
{ "url": "https://example.com/article/123", "max_length": 500 }

// Response
{
  "url": "...",
  "title": "맛집 추천 — 홍대 카페",
  "summary": "정제된 본문 500자...",
  "freshness": { "level": "recent", "score": 1.0, "published_at": "2025-04-01T..." },
  "fetched_at": "2026-05-06T...",
  "content_length_bytes": 42000
}
```

### `POST /crawl/analyze-url`
check-source + fetch를 한 번에 실행한다. 정책 위반 시에도 HTTP 200을 반환하고 `policy.status`로 구분한다.

## FastAPI 앱에 등록하는 방법

```python
# app/main.py
from fastapi import FastAPI
from app.routers.crawl_router import router as crawl_router

app = FastAPI()
app.include_router(crawl_router)
```

## 신선도 기준

| 레벨 | 조건 | 점수 |
|------|------|------|
| `recent` | 90일 이내 | 1.0 |
| `moderate` | 91~180일 | 0.7 |
| `old` | 181~365일 | 0.4 |
| `very_old` | 365일 초과 | 0.1 |
| `unknown` | 날짜 미확인 | 0.5 |

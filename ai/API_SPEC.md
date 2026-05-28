# DateFlow AI Agent — API 명세서

> 버전 v0.1 (회의 협의용 초안) · 2026-05-20

AI 서브시스템이 노출하는 두 진입점 함수의 입출력 명세입니다.
백엔드가 `import` 후 직접 호출하며, 통신은 모두 Python `dict`로 이루어집니다.

---

## 1. 통합 흐름

```
[Frontend]                  [Backend B1]              [AI Subsystem]
   ↓ "추천해줘"
                              recommend_events() ────► Pipeline 1
                              ◄──── { events: [...] }
   ◄── 카드 3~5개

   👤 사용자가 카드 1개 선택

   ↓ "이걸로 코스 만들어줘"
                              generate_course() ──────► Pipeline 2
                              ◄──── { courses: [A안/B안] }
   ◄── 코스 표시
```

→ 백엔드는 AI를 **두 번** 호출합니다. 그 사이에 사용자 선택이 들어갑니다.

---

## 2. 진입점 ① — `recommend_events()`

메인 이벤트 3~5개를 추천합니다 (Pipeline 1).

### 임포트
```python
from agents.pipeline1 import recommend_events
```

### 시그니처
```python
recommend_events(
    natural_language: str,
    merged_preferences: dict = None,
    weather: dict = None,
    area: str = None,
    visit_date: str = None,
) -> dict
```

### 입력 명세

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `natural_language` | str | ✓ | 사용자 자연어 요청 |
| `merged_preferences` | dict | △ | 두 사람 통합 취향 (아래 스키마) |
| `weather` | dict | △ | 날씨 정보 |
| `area` | str | △ | 지역명 (예: "성수동") |
| `visit_date` | str | △ | YYYY-MM-DD |

**`merged_preferences` 스키마**
```json
{
  "atmospheres": ["감성적", "조용한"],
  "categories": ["카페", "전시"],
  "areas_preferred": ["성수", "홍대"],
  "budget_max": 100000
}
```

**`weather` 스키마**
```json
{
  "condition": "rain",
  "temp_celsius": 18
}
```

### 출력 명세 (성공)

> ⚠️ Phase 1: 구조화는 다음 단계. 현재는 `events_raw` 마크다운 텍스트로 반환되며, 백엔드는 그대로 프론트에 전달 가능.

```json
{
  "session_id": "abc-123-...",
  "events_raw": "1. OO 갤러리 〈도시의 빛〉 전시\n  - 감성 공간 ...\n2. ...",
  "events": []
}
```

**Phase 2 (협의 후) 목표 출력**
```json
{
  "session_id": "...",
  "events": [
    {
      "name": "성수 갤러리 카페 전시",
      "place_id": "kakao:145791269",
      "category": "전시",
      "reason": "두 분 다 좋아하시는 감성 공간",
      "address": "서울 성동구 ...",
      "place_url": "http://place.map.kakao.com/145791269"
    }
  ]
}
```

### 출력 명세 (실패)

```json
{
  "session_id": "...",
  "error": "TypeError: ...",
  "events": []
}
```

---

## 3. 진입점 ② — `generate_course()`

선택된 메인 이벤트를 중심으로 시간대별 코스를 생성합니다 (Pipeline 2).

### 임포트
```python
from agents.pipeline2 import generate_course
```

### 시그니처
```python
generate_course(
    selected_event: dict,
    merged_preferences: dict = None,
    weather: dict = None,
    visit_date: str = None,
) -> dict
```

### 입력 명세

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `selected_event` | dict | ✓ | Pipeline 1의 `events[i]` 객체 |
| `merged_preferences` | dict | △ | Pipeline 1과 동일 |
| `weather` | dict | △ | Pipeline 1과 동일 |
| `visit_date` | str | △ | YYYY-MM-DD |

**`selected_event` 예시**
```json
{
  "name": "성수 갤러리 카페 전시",
  "place_id": "kakao:145791269",
  "category": "전시",
  "time": "13:00"
}
```

### 출력 명세 (성공)

> ⚠️ Phase 1: `courses_raw` 마크다운 그대로 반환.

```json
{
  "session_id": "...",
  "courses_raw": "**A안**\n* 11:30 어니언 성수\n* 13:00 ...",
  "courses": [],
  "hours_check": []
}
```

**Phase 2 (협의 후) 목표 출력**
```json
{
  "session_id": "...",
  "courses": [
    {
      "name": "A안",
      "theme": "여유로운 오후 데이트",
      "places": [
        {
          "order": 1,
          "time": "11:30",
          "duration_min": 60,
          "name": "어니언 성수",
          "category": "카페",
          "is_main": false,
          "address": "...",
          "phone": "...",
          "place_url": "...",
          "memo": "감성 카페, 빵과 커피"
        }
      ]
    }
  ],
  "hours_check": [
    {"name": "어니언 성수", "saturday_hours": "09:00-22:00", "status": "ok"}
  ]
}
```

---

## 4. 응답 시간

| 함수 | 평균 | 비고 |
|---|---|---|
| `recommend_events` | ~10초 | 검색 위주 |
| `generate_course` | ~30초 | `check_hours` Playwright 포함 |

→ 백엔드는 동기 호출, 프론트는 로딩 인디케이터 권장.

---

## 5. 에러 처리

- 함수는 **예외를 throw하지 않음** — 항상 `dict` 반환
- 실패 시 `error` 필드 + `events: []` / `courses: []`
- 백엔드 분기:
  ```python
  result = recommend_events(...)
  if "error" in result:
      # 에러 처리
  ```


## 6. 변경 이력

| 날짜 | 버전 | 변경 |
|---|---|---|
| 2026-05-20 | v0.1 | 초안 (Phase 1, 회의 협의용) |

import json
import re

from deepagents import create_deep_agent
from agents.shared import get_llm
from tools.search import search_places
from tools.hours import get_place_info
from tools.check_hours import check_hours
from tools.logger import new_session, end_session

SYSTEM_PROMPT = """당신은 선택된 메인 이벤트를 중심으로 데이트 코스를 설계하는 전문가입니다.

[입력으로 받는 정보]
- 선택된 메인 이벤트 (이름, 장소, 시간 등)
- 사용자의 통합 취향 (가능한 경우)
- 지역, 날씨, 방문 날짜 (가능한 경우)

[당신의 역할]
1. search_places 툴로 메인 이벤트 주변의 카페, 식당, 산책 코스 등을 검색한다.
2. get_place_info 툴로 후보 장소의 상세 정보(주소, 전화, 카카오맵 링크)를 확인한다.
3. 메인 이벤트를 중심으로 시간대별 코스를 구성한다.
4. 코스를 확정하기 직전, 최종 장소들에 대해 반드시 check_hours 툴을 호출하여
   방문 예정 요일/시간에 실제로 영업하는지 확인한다.
5. 만약 휴무이거나 영업시간이 맞지 않는 장소가 있으면 search_places로 대체 장소를 찾아 교체한다.

[출력 형식 — 반드시 준수]
최종 응답은 아래 JSON 형식으로만 출력하라. 자연어 설명·마크다운은 절대 포함하지 말 것.
JSON 외 어떠한 추가 텍스트도 허용되지 않는다.

{
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
          "address": "서울 성동구 ...",
          "phone": "070-...",
          "place_url": "http://place.map.kakao.com/...",
          "is_main": false,
          "memo": "감성 카페, 빵과 커피로 시작"
        }
      ]
    },
    {
      "name": "B안",
      "theme": "전시 후 맛집 탐방",
      "places": [...]
    }
  ],
  "hours_check": [
    {
      "name": "어니언 성수",
      "visit_day": "토요일",
      "hours": "09:00 ~ 22:00",
      "status": "ok"
    }
  ]
}

규칙:
- 정확히 2개의 코스(A안 / B안) 생성
- 메인 이벤트는 두 코스 모두에 포함하고 is_main: true
- status는 "ok" / "closed" / "outside_hours" 중 하나
- 모르는 값은 빈 문자열 ""
- 응답 전체가 위 JSON 객체 하나여야 한다 (배열 X, 코드블록 X)
"""


def build_pipeline2_agent():
    llm = get_llm()
    return create_deep_agent(
        model=llm,
        tools=[search_places, get_place_info, check_hours],
        system_prompt=SYSTEM_PROMPT,
    )


def _compose_pipeline2_message(selected_event, merged_preferences, weather, visit_date) -> str:
    """입력 dict들을 자연어 메시지로 합친다."""
    parts = []
    ev_name = selected_event.get("name", "")
    ev_cat = selected_event.get("category", "")
    ev_time = selected_event.get("time", "")
    parts.append(f"선택된 메인 이벤트: {ev_name} ({ev_cat}, 예상 시간 {ev_time})")
    parts.append("이 이벤트를 중심으로 시간대별 데이트 코스를 짜주세요.")

    if visit_date:
        parts.append(f"방문 예정일: {visit_date}")
    if weather:
        cond = weather.get("condition", "")
        temp = weather.get("temp_celsius", "")
        if cond or temp != "":
            parts.append(f"날씨: {cond} {temp}도")
    if merged_preferences:
        atms = ", ".join(merged_preferences.get("atmospheres", []))
        cats = ", ".join(merged_preferences.get("categories", []))
        areas = ", ".join(merged_preferences.get("areas_preferred", []))
        budget = merged_preferences.get("budget_max")
        if atms:
            parts.append(f"통합 취향 분위기: {atms}")
        if cats:
            parts.append(f"통합 취향 카테고리: {cats}")
        if areas:
            parts.append(f"선호 지역: {areas}")
        if budget:
            parts.append(f"1인 예산 상한: {budget:,}원")
    return "\n".join(parts)


def _parse_json_output(text: str) -> dict:
    """LLM 응답에서 JSON 객체를 추출해 코스/영업시간 검증 결과를 분리한다.

    추출 경로(_parse_status)는 디버그용으로 함께 반환:
    - "empty"             : 응답 텍스트가 비어 있음
    - "codeblock_ok"      : ```json``` 블록 안의 JSON 파싱 성공
    - "brace_ok"          : 텍스트에서 { ... } 추출해 파싱 성공
    - "json_failed"       : JSON 후보를 찾았지만 파싱 실패 (잘못된 JSON)
    - "no_json_found"     : JSON 후보 자체가 없음 (마크다운 응답)
    """
    if not text:
        return {"courses": [], "hours_check": [], "_parse_status": "empty"}

    # 1) ```json ... ``` 코드블록 우선 추출
    code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            return {
                "courses": data.get("courses", []),
                "hours_check": data.get("hours_check", []),
                "_parse_status": "codeblock_ok",
            }
        except json.JSONDecodeError:
            return {"courses": [], "hours_check": [], "_parse_status": "json_failed"}

    # 2) 텍스트 안에서 가장 외곽의 { ... } 추출
    brace = re.search(r"\{[\s\S]*\}", text)
    if not brace:
        return {"courses": [], "hours_check": [], "_parse_status": "no_json_found"}

    try:
        data = json.loads(brace.group(0))
        return {
            "courses": data.get("courses", []),
            "hours_check": data.get("hours_check", []),
            "_parse_status": "brace_ok",
        }
    except json.JSONDecodeError:
        return {"courses": [], "hours_check": [], "_parse_status": "json_failed"}


def _extract_final_text(result) -> str:
    """에이전트 응답의 마지막 메시지에서 텍스트를 추출한다."""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        content = getattr(msg, "content", None)
        if not content:
            continue
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
                elif isinstance(item, str):
                    texts.append(item)
            if texts:
                return "\n".join(texts)
    return ""


def generate_course(
    selected_event: dict,
    merged_preferences: dict = None,
    weather: dict = None,
    visit_date: str = None,
) -> dict:
    """Pipeline 2 진입점 — 선택된 메인 이벤트 기반으로 A안/B안 코스를 생성한다.

    API_SPEC.md §3 참조.

    Args:
        selected_event: Pipeline 1 응답의 events[i] 객체 (필수)
        merged_preferences: 두 사람 통합 취향
        weather: 날씨 정보 (condition, temp_celsius)
        visit_date: YYYY-MM-DD

    Returns:
        dict — 성공 시 {session_id, courses_raw, courses, hours_check},
               실패 시 {session_id, error, courses}
    """
    sid = new_session()

    if not selected_event:
        end_session("failed", note="selected_event 누락")
        return {
            "session_id": sid,
            "error": "selected_event is required",
            "courses": [],
        }

    try:
        agent = build_pipeline2_agent()
        user_msg = _compose_pipeline2_message(
            selected_event, merged_preferences, weather, visit_date
        )

        result = agent.invoke({"messages": [{"role": "user", "content": user_msg}]})
        text = _extract_final_text(result)
        parsed = _parse_json_output(text)

        end_session("success")
        return {
            "session_id": sid,
            "courses_raw": text,                       # 원본 마크다운/JSON 백업
            "courses": parsed["courses"],              # 파싱된 코스 리스트
            "hours_check": parsed["hours_check"],      # 파싱된 영업시간 검증
            "_parse_status": parsed["_parse_status"],  # 디버그: 파싱 경로
        }
    except Exception as e:
        end_session("failed", note=str(e))
        return {
            "session_id": sid,
            "error": f"{type(e).__name__}: {e}",
            "courses": [],
        }

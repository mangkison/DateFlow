"""Pipeline 1 진입점 — recommend_events() TDD 테스트 (RED 단계).

이 테스트는 RED 단계: recommend_events() 함수가 아직 없으므로
ImportError 또는 AttributeError가 발생해야 정상이다.
함수 구현 후 GREEN 단계에서 통과하게 된다.

명세: API_SPEC.md §2
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")


# 백엔드가 보낼 더미 입력 (API_SPEC.md 기준)
DUMMY_INPUT = {
    "natural_language": "성수동에서 토요일 데이트 코스 짜줘",
    "merged_preferences": {
        "atmospheres": ["감성적", "조용한"],
        "categories": ["카페", "전시"],
        "areas_preferred": ["성수"],
        "budget_max": 100000,
    },
    "weather": {"condition": "cloudy", "temp_celsius": 18},
    "area": "성수동",
    "visit_date": "2025-05-24",
}


def test_recommend_events():
    """recommend_events() — 명세 dict in/out 계약 검증."""
    from agents.pipeline1 import recommend_events

    print("\n=== Pipeline 1 — recommend_events() 테스트 ===")
    print("\n[입력 더미 dict]")
    print(json.dumps(DUMMY_INPUT, ensure_ascii=False, indent=2))

    result = recommend_events(**DUMMY_INPUT)

    # ── 명세 검증 ──
    assert isinstance(result, dict), "반환값은 dict여야 함"
    assert "session_id" in result, "session_id 필드 누락"

    # Phase 1: events_raw / events / error 중 최소 하나는 존재
    has_events = "events" in result or "events_raw" in result
    has_error = "error" in result
    assert has_events or has_error, "events / events_raw / error 중 하나는 있어야 함"

    # ── 결과 출력 ──
    print("\n[응답 dict]")
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output[:3000] + ("..." if len(output) > 3000 else ""))

    print(f"\n✓ session_id: {result.get('session_id')}")
    if "error" in result:
        print(f"✗ error: {result['error']}")
    else:
        print("✓ 명세 계약 통과")


if __name__ == "__main__":
    test_recommend_events()

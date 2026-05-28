"""Pipeline 2 진입점 — generate_course() TDD 테스트 (RED 단계).

이 테스트는 RED 단계: generate_course() 함수가 아직 없으므로
ImportError 또는 AttributeError가 발생해야 정상이다.

명세: API_SPEC.md §3
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")


# 백엔드가 보낼 더미 입력 (Pipeline 1의 events[i]를 사용자가 골랐다고 가정)
DUMMY_INPUT = {
    "selected_event": {
        "name": "성수 갤러리 카페 전시",
        "place_id": "kakao:145791269",
        "category": "전시",
        "time": "13:00",
    },
    "merged_preferences": {
        "atmospheres": ["감성적", "조용한"],
        "categories": ["카페", "전시"],
        "areas_preferred": ["성수"],
        "budget_max": 100000,
    },
    "weather": {"condition": "cloudy", "temp_celsius": 18},
    "visit_date": "2025-05-24",
}


def test_generate_course():
    """generate_course() — 명세 dict in/out 계약 검증."""
    from agents.pipeline2 import generate_course

    print("\n=== Pipeline 2 — generate_course() 테스트 ===")
    print("\n[입력 더미 dict]")
    print(json.dumps(DUMMY_INPUT, ensure_ascii=False, indent=2))

    result = generate_course(**DUMMY_INPUT)

    # ── 명세 검증 ──
    assert isinstance(result, dict), "반환값은 dict여야 함"
    assert "session_id" in result, "session_id 필드 누락"

    has_courses = "courses" in result or "courses_raw" in result
    has_error = "error" in result
    assert has_courses or has_error, "courses / courses_raw / error 중 하나는 있어야 함"

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
    test_generate_course()

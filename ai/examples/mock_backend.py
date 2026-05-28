"""백엔드(FastAPI) 호출 시뮬레이션.

실제 FastAPI 엔드포인트는 아래 두 함수와 동일한 방식으로 동작한다.
JSON 본문을 파싱해 AI 진입점 함수에 그대로 전달하기만 하면 된다.

실행:
    python -m examples.mock_backend
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from agents.pipeline1 import recommend_events
from agents.pipeline2 import generate_course


_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_request(filename: str) -> dict:
    """예시 JSON 파일을 dict로 로드."""
    path = os.path.join(_HERE, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# === FastAPI 엔드포인트 시뮬레이션 ====================================
# 실제 FastAPI에서는 아래 함수가 라우터의 핸들러가 된다.
# @app.post("/api/events/recommend")
# def post_recommend(body: dict):
#     return recommend_events(**body)

def mock_endpoint_recommend(request_body: dict) -> dict:
    """POST /api/events/recommend 시뮬레이션."""
    return recommend_events(**request_body)


def mock_endpoint_generate(request_body: dict) -> dict:
    """POST /api/courses/generate 시뮬레이션."""
    return generate_course(**request_body)


# === 메인 시연 =======================================================

def run():
    print("=" * 70)
    print("[1] POST /api/events/recommend  ── Pipeline 1")
    print("=" * 70)

    body_p1 = _load_request("dummy_p1_request.json")
    print("\n[요청 본문]")
    print(json.dumps(body_p1, ensure_ascii=False, indent=2))

    response_p1 = mock_endpoint_recommend(body_p1)

    print("\n[응답]")
    print(f"session_id    : {response_p1.get('session_id')}")
    print(f"_parse_status : {response_p1.get('_parse_status')}")
    print(f"events count  : {len(response_p1.get('events', []))}")
    if response_p1.get("events"):
        print("\n[첫 번째 이벤트]")
        print(json.dumps(response_p1["events"][0], ensure_ascii=False, indent=2))
    if "error" in response_p1:
        print(f"error: {response_p1['error']}")

    print("\n")
    print("=" * 70)
    print("[2] POST /api/courses/generate  ── Pipeline 2")
    print("=" * 70)

    body_p2 = _load_request("dummy_p2_request.json")
    print("\n[요청 본문]")
    print(json.dumps(body_p2, ensure_ascii=False, indent=2))

    response_p2 = mock_endpoint_generate(body_p2)

    print("\n[응답]")
    print(f"session_id        : {response_p2.get('session_id')}")
    print(f"_parse_status     : {response_p2.get('_parse_status')}")
    print(f"courses count     : {len(response_p2.get('courses', []))}")
    print(f"hours_check count : {len(response_p2.get('hours_check', []))}")
    if response_p2.get("courses"):
        print("\n[A안 코스 첫 장소]")
        first_course = response_p2["courses"][0]
        if first_course.get("places"):
            print(json.dumps(first_course["places"][0], ensure_ascii=False, indent=2))
    if "error" in response_p2:
        print(f"error: {response_p2['error']}")


if __name__ == "__main__":
    run()

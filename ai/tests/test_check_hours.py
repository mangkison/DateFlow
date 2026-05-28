import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from tools.check_hours import check_hours
from tools.logger import new_session, end_session


TEST_PLACES = [
    "블루보틀 성수",
    "어니언 성수",
]


def run():
    sid = new_session()
    print(f"[session] {sid}")
    print("=" * 60)

    try:
        # 1차 호출 — 실제 페이지 방문
        for name in TEST_PLACES:
            print(f"\n--- 1차 호출: {name} ---")
            result = check_hours.invoke({
                "place_name": name,
                "visit_date": "2025-05-23 토요일",
            })
            print(result)

        # 2차 호출 — 캐시 적중 검증
        print("\n" + "=" * 60)
        print("캐시 동작 검증")
        print("=" * 60)
        for name in TEST_PLACES:
            print(f"\n--- 2차 호출: {name} ---")
            result = check_hours.invoke({"place_name": name})
            print(result)

        end_session("success")
    except Exception as e:
        end_session("failed", note=str(e))
        raise


if __name__ == "__main__":
    run()

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from agents.pipeline2 import build_pipeline2_agent
from tools.logger import new_session, end_session


DUMMY_EVENT = {
    "name": "성수 갤러리 카페 전시",
    "category": "전시",
    "area": "성수동",
    "time": "13:00",
}


def run():
    agent = build_pipeline2_agent()

    sid = new_session()
    print(f"[session] {sid}")
    print("=" * 60)

    user_input = (
        f"선택된 메인 이벤트: {DUMMY_EVENT['name']} ({DUMMY_EVENT['category']}, "
        f"{DUMMY_EVENT['area']}, {DUMMY_EVENT['time']})\n"
        f"이 이벤트 중심으로 데이트 코스를 짜줘. "
        f"두 사람 다 감성적인 공간과 맛집을 좋아해."
    )
    print(f"[input]\n{user_input}")
    print("-" * 60)

    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        end_session("success")

        for msg in result.get("messages", []):
            role = getattr(msg, "type", None) or msg.__class__.__name__
            content = getattr(msg, "content", str(msg))
            print(f"\n[{role}]")
            print(content)
    except Exception as e:
        end_session("failed", note=str(e))
        raise


if __name__ == "__main__":
    run()

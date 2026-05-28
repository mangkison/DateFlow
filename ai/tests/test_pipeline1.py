import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from agents.pipeline1 import build_pipeline1_agent
from tools.logger import new_session, end_session


def run():
    agent = build_pipeline1_agent()

    sid = new_session()
    print(f"[session] {sid}")
    print("=" * 60)

    user_input = "성수동에서 2025년5월23일토요일 데이트 할만한 거 추천해줘"
    print(f"[input] {user_input}")
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

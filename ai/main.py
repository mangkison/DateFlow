from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os
from tools.hours import get_place_info
from tools.search import search_places
from tools.event import search_events
from tools.logger import new_session, end_session
import sys
load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')
llm = init_chat_model(
     "google_genai:gemini-2.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY")
)
agent = create_deep_agent(
    model=llm, 
    tools=[search_places, get_place_info,search_events],
    system_prompt="당신은 데이트 코스 추천 AI입니다. "
    )

session_id = new_session()
print(f"[session] {session_id}")

try:
    result = agent.invoke({
        "messages": [{"role": "user", "content": " 26년 5월 20일 서울에서 할만한거"}]
    })
    end_session("success")
    print(result)
except Exception as e:
    end_session("failed", note=str(e))
    raise
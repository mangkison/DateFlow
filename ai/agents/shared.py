import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()


def get_llm():
    return init_chat_model(
        "google_genai:gemini-2.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

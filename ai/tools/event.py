from langchain_core.tools import tool
import requests
import os
from dotenv import load_dotenv
from tools.logger import log_tool

load_dotenv()


@tool
@log_tool
def search_events(query: str) -> str:
    """카카오 로컬 API로 공연·전시·팝업 등 메인 이벤트를 검색합니다.

    각 결과에 name, 주소, 전화, place_id, place_url을 포함하여 반환합니다.
    """
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_KEY')}"}
    params = {"query": query, "size": 5}

    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        items = res.json().get("documents", [])
    except Exception as e:
        return f"이벤트 검색 실패: {type(e).__name__}: {e}"

    if not items:
        return "검색 결과 없음"

    lines = []
    for item in items:
        place_url = item.get("place_url", "")
        place_id = place_url.rsplit("/", 1)[-1] if place_url else ""
        lines.append(
            f"{item['place_name']} ({item.get('category_name', '')})\n"
            f"  주소: {item.get('road_address_name') or item.get('address_name', '')}\n"
            f"  전화: {item.get('phone', '')}\n"
            f"  place_id: kakao:{place_id}\n"
            f"  place_url: {place_url}"
        )

    return "\n\n".join(lines)

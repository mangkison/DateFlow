# tools/hours.py
from langchain_core.tools import tool
import requests
import os
from tools.logger import log_tool

@tool
@log_tool
def get_place_info(place_name: str) -> str:
    """장소의 주소, 전화번호, 카카오맵 링크를 검색합니다."""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_KEY')}"}
    params = {"query": place_name, "size": 1}

    res = requests.get(url, headers=headers, params=params)
    items = res.json().get('documents', [])

    if not items:
        return "장소 정보 없음"

    item = items[0]
    return f"{item['place_name']} / 주소: {item['road_address_name']} / 전화: {item['phone']} / 링크: {item['place_url']}"
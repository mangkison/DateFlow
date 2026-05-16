"""네이버 지역검색·블로그 검색 API 클라이언트.

검색 결과에서 장소 기본 정보(이름·주소·좌표·전화·카테고리)를 가져온다.
운영시간은 제공하지 않으므로 보조 크롤링으로 보완한다.
"""
import re

import httpx

from app.core.config import settings

SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_coord(val: str) -> float | None:
    """네이버 좌표는 10^7 배 정수 문자열로 반환된다."""
    try:
        return float(val) / 1e7
    except (TypeError, ValueError):
        return None


async def search_places(query: str, display: int = 5) -> list[dict]:
    """키워드로 장소를 검색하고 정규화된 딕셔너리 리스트를 반환한다.

    Args:
        query: 검색어 (예: '홍대 카페', '강남 레스토랑')
        display: 반환할 결과 수 (최대 5)
    """
    if not settings.NAVER_CLIENT_ID or not settings.NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 미설정")

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": min(display, 5),
        "sort": "comment",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(SEARCH_URL, headers=headers, params=params)
        resp.raise_for_status()

    return [_normalize(item) for item in resp.json().get("items", [])]


async def search_blog(query: str, display: int = 3) -> list[dict]:
    """블로그 검색으로 장소 후기 URL 목록을 반환한다.

    Returns:
        [{"title": ..., "link": ..., "description": ..., "postdate": ...}, ...]
    """
    if not settings.NAVER_CLIENT_ID or not settings.NAVER_CLIENT_SECRET:
        return []

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": min(display, 10), "sort": "sim"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(BLOG_SEARCH_URL, headers=headers, params=params)
        resp.raise_for_status()

    return [
        {
            "title": _strip_tags(item.get("title", "")),
            "link": item.get("link", ""),
            "description": _strip_tags(item.get("description", "")),
            "postdate": item.get("postdate", ""),
        }
        for item in resp.json().get("items", [])
        if item.get("link")
    ]


def _normalize(item: dict) -> dict:
    return {
        "source": "naver",
        "name": _strip_tags(item.get("title", "")),
        "category": item.get("category", ""),
        "description": _strip_tags(item.get("description", "")),
        "phone": item.get("telephone", ""),
        "address": item.get("address", ""),
        "road_address": item.get("roadAddress", ""),
        "latitude": _parse_coord(item.get("mapy")),
        "longitude": _parse_coord(item.get("mapx")),
        "place_url": item.get("link", ""),
        "naver_id": None,
    }

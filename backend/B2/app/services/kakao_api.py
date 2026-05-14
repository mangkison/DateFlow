"""카카오 로컬 API 클라이언트.

키워드 검색과 카테고리 검색을 지원한다.
장소 기본 정보(이름·주소·좌표·전화·카테고리·URL)를 제공한다.
"""
import httpx

from app.core.config import settings

KEYWORD_URL  = "https://dapi.kakao.com/v2/local/search/keyword.json"
CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"

# 카카오 카테고리 그룹 코드
CATEGORY_CODES: dict[str, str] = {
    "카페":    "CE7",
    "음식점":  "FD6",
    "문화시설": "CT1",  # 영화관·박물관·미술관·공연장 포함
    "관광명소": "AT4",  # 공원·놀이공원·아쿠아리움·야경 명소 포함
    "숙박":    "AD5",
    "마트":    "MT1",
    "편의점":  "CS2",
}


def _headers() -> dict[str, str]:
    if not settings.KAKAO_REST_API_KEY:
        raise RuntimeError("KAKAO_REST_API_KEY 미설정")
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}


async def search_by_keyword(query: str, size: int = 15) -> list[dict]:
    """키워드로 장소를 검색한다.

    Args:
        query: 검색어 (예: '홍대 카페', '이태원 맛집')
        size: 반환할 결과 수 (최대 45)
    """
    params = {"query": query, "size": min(size, 45)}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(KEYWORD_URL, headers=_headers(), params=params)
        resp.raise_for_status()
    return [_normalize(doc) for doc in resp.json().get("documents", [])]


async def search_by_category(
    category: str,
    longitude: float,
    latitude: float,
    radius_m: int = 1000,
    size: int = 15,
) -> list[dict]:
    """특정 좌표 주변의 카테고리 장소를 검색한다.

    Args:
        category: CATEGORY_CODES 키 (예: '카페', '음식점')
        longitude: 중심 경도
        latitude: 중심 위도
        radius_m: 검색 반경 (미터, 최대 20000)
        size: 반환할 결과 수
    """
    code = CATEGORY_CODES.get(category, category)
    params = {
        "category_group_code": code,
        "x": longitude,
        "y": latitude,
        "radius": min(radius_m, 20000),
        "size": min(size, 45),
        "sort": "accuracy",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(CATEGORY_URL, headers=_headers(), params=params)
        resp.raise_for_status()
    return [_normalize(doc) for doc in resp.json().get("documents", [])]


def _normalize(item: dict) -> dict:
    raw_category = item.get("category_name", "")
    # '음식점 > 한식 > 국밥' → '국밥'
    leaf_category = raw_category.split(">")[-1].strip() if raw_category else ""

    return {
        "source": "kakao",
        "name": item.get("place_name", ""),
        "category": leaf_category,
        "category_group": item.get("category_group_name", ""),
        "description": "",
        "phone": item.get("phone", ""),
        "address": item.get("address_name", ""),
        "road_address": item.get("road_address_name", ""),
        "latitude": float(item["y"]) if item.get("y") else None,
        "longitude": float(item["x"]) if item.get("x") else None,
        "place_url": item.get("place_url", ""),
        "kakao_id": item.get("id", ""),
    }

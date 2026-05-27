"""네이버 플레이스 URL 보완 서비스.

booking_page_url=NULL인 장소를 대상으로 네이버 Local Search API로
네이버 플레이스 링크를 찾아 booking_page_url에 저장한다.
네이버 플레이스 페이지에는 예약 버튼이 포함되어 있다.
"""
import math
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.place import Place
from app.services import naver_api

_MATCH_DISTANCE_M = 200


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _normalize(name: str) -> str:
    return re.sub(r"\s+", "", name).lower()


def _addr_region(addr: str) -> str:
    for suffix in ("읍", "면", "동"):
        m = re.search(rf"[가-힣]+{suffix}", addr)
        if m:
            return m.group(0)
    m = re.search(r"[가-힣]+(?:구|군|시)", addr)
    return m.group(0) if m else ""


def _is_naver_map_url(url: str) -> bool:
    """네이버 지도/플레이스 URL인지 확인한다.
    - map.naver.com, place.map.naver.com: 일반 플레이스 URL
    - naver.me: 네이버 지도 단축 URL (map.naver.com으로 리다이렉트)
    """
    return (
        "map.naver.com" in url
        or "place.map.naver.com" in url
        or url.startswith("https://naver.me/")
        or url.startswith("http://naver.me/")
    )


async def _find_naver_url(place: Place) -> str | None:
    """네이버 API로 장소의 map.naver.com 플레이스 URL을 찾는다.

    map.naver.com 도메인이 아닌 링크(인스타그램·홈페이지 등)는 무시한다.

    매칭 우선순위:
      1. 이름 완전 일치
      2. 좌표 200m 이내
      3. 이름 포함 관계
    """
    addr = place.road_address or place.address or ""
    region = _addr_region(addr)
    query = f"{place.name} {region}" if region else place.name

    try:
        results = await naver_api.search_places(query, display=5)
    except Exception:
        return None

    # map.naver.com URL을 가진 결과만 대상으로 매칭
    naver_map_results = [r for r in results if _is_naver_map_url(r.get("place_url", ""))]

    for r in naver_map_results:
        pn = _normalize(place.name)
        rn = _normalize(r["name"])

        # 1. 이름 완전 일치
        if pn == rn:
            return r["place_url"]

        # 2. 좌표 200m 이내
        if (place.latitude and place.longitude
                and r.get("latitude") and r.get("longitude")):
            dist = _haversine_m(
                float(place.latitude), float(place.longitude),
                r["latitude"], r["longitude"],
            )
            if dist <= _MATCH_DISTANCE_M:
                return r["place_url"]

        # 3. 이름 포함 관계
        if pn in rn or rn in pn:
            return r["place_url"]

    return None


async def enrich_booking_urls(
    db: AsyncSession,
    limit: int = 100,
) -> dict:
    """booking_page_url=NULL 장소에 네이버 플레이스 URL을 일괄 채운다.

    Returns:
        {"total": int, "enriched": int, "skipped": int}
    """
    stmt = (
        select(Place)
        .where(
            Place.is_active == True,
            Place.booking_page_url.is_(None),
        )
        .order_by(Place.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    places = result.scalars().all()

    enriched = 0
    skipped = 0
    for place in places:
        url = await _find_naver_url(place)
        if url:
            place.booking_page_url = url
            enriched += 1
        else:
            skipped += 1

    await db.commit()
    return {"total": len(places), "enriched": enriched, "skipped": skipped}

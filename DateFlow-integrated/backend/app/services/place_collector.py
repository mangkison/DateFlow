"""장소 수집 오케스트레이터.

수집 우선순위:
  1순위 — 카카오 로컬 API  (구조화된 정보: 좌표·전화·카테고리)
  2순위 — 네이버 지역검색 API (설명문 보완)
  3순위 — 웹 크롤링 (운영시간·분위기 텍스트 등 API 미제공 정보 보조 확인)

중복 제거: 좌표 50m 이내 또는 이름 완전 일치 → 같은 장소로 판단하여 병합.
"""
import asyncio
import math
import re
import uuid
from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.place import Place, PlaceOperatingHour
from app.services import kakao_api, naver_api
from app.services.safe_crawler import safe_fetch
from app.services.vector_store import upsert_place_vector
from app.core.config import settings
from app.services.source_policy import check_source_policy
from app.schemas.crawl_schema import PolicyStatus

# 중복 판단 거리 기준 (미터)
_DEDUP_DISTANCE_M = 50


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 사이의 거리를 미터로 반환한다."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name).lower()


def _is_duplicate(a: dict, b: dict) -> bool:
    """이름 일치 또는 좌표 50m 이내이면 같은 장소로 본다."""
    if _normalize_name(a["name"]) == _normalize_name(b["name"]):
        return True
    if all(v is not None for v in [a.get("latitude"), a.get("longitude"),
                                    b.get("latitude"), b.get("longitude")]):
        dist = _haversine_m(a["latitude"], a["longitude"],
                            b["latitude"], b["longitude"])
        return dist <= _DEDUP_DISTANCE_M
    return False


def _merge(primary: dict, secondary: dict) -> dict:
    """primary(카카오) 데이터를 기준으로 secondary(네이버) 빈 필드를 보완한다."""
    merged = dict(primary)
    for key in ("description", "phone", "address", "road_address", "website_url"):
        if not merged.get(key) and secondary.get(key):
            merged[key] = secondary[key]
    return merged


def _deduplicate(items: list[dict]) -> list[dict]:
    result: list[dict] = []
    for item in items:
        for i, existing in enumerate(result):
            if _is_duplicate(existing, item):
                # kakao가 primary이므로 kakao 결과 유지, naver로 빈 필드 보완
                if item["source"] == "naver":
                    result[i] = _merge(existing, item)
                else:
                    result[i] = _merge(item, existing)
                break
        else:
            result.append(item)
    return result


async def _crawl_supplement(place_url: str, place_name: str = "") -> dict:
    """웹 크롤링으로 운영시간·설명 등 API 미제공 정보를 보조 수집한다.

    1단계: place_url이 크롤링 가능하면 직접 수집
    2단계: 불가능하면 네이버 블로그 검색으로 후기 텍스트 수집
    실패해도 빈 dict를 반환하여 메인 파이프라인에 영향을 주지 않는다.
    """
    # 1단계: place_url 직접 크롤링
    if place_url:
        try:
            policy = await check_source_policy(place_url)
            if policy.status == PolicyStatus.allowed:
                result = await safe_fetch(place_url, max_length=1000)
                return {
                    "crawled_summary": result.summary,
                    "crawled_title": result.title,
                    "freshness_score": result.freshness.score,
                }
        except Exception:
            pass

    # 2단계: 네이버 블로그 검색 fallback
    if not place_name:
        return {}
    try:
        blog_items = await naver_api.search_blog(f"{place_name} 후기", display=3)
        for item in blog_items:
            link = item.get("link", "")
            if not link:
                continue
            try:
                fetch_url = re.sub(r"https?://blog\.naver\.com/", "https://m.blog.naver.com/", link)
                policy = await check_source_policy(fetch_url)
                if policy.status != PolicyStatus.allowed:
                    continue
                result = await safe_fetch(fetch_url, max_length=1000)
                if result.summary:
                    return {
                        "crawled_summary": result.summary,
                        "crawled_title": result.title,
                        "freshness_score": result.freshness.score,
                        "blog_source": link,
                    }
            except Exception:
                continue
    except Exception:
        pass

    return {}


def _parse_operating_hours(raw: str) -> list[dict]:
    """크롤링 텍스트에서 운영시간 패턴을 추출한다.

    예: '월~금 11:00 - 22:00', '토,일 휴무'
    반환: [{day_of_week: int, open_time: str, close_time: str, is_closed: bool}]
    """
    DAY_MAP = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    results = []

    # '월~금 11:00 - 22:00' 패턴
    range_pattern = re.compile(
        r"([월화수목금토일])[~\-~]([월화수목금토일])\s*(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})"
    )
    for m in range_pattern.finditer(raw):
        start_day = DAY_MAP[m.group(1)]
        end_day   = DAY_MAP[m.group(2)]
        for d in range(start_day, end_day + 1):
            results.append({
                "day_of_week": d,
                "open_time": m.group(3),
                "close_time": m.group(4),
                "is_closed": False,
            })

    # '토,일 휴무' 패턴
    closed_pattern = re.compile(r"([월화수목금토일,]+)\s*휴무")
    for m in closed_pattern.finditer(raw):
        for ch in m.group(1):
            if ch in DAY_MAP:
                results.append({"day_of_week": DAY_MAP[ch], "is_closed": True})

    return results


async def collect_and_save(
    query: str,
    db: AsyncSession,
    area: str = "",
    crawl_supplement: bool = True,
) -> list[Place]:
    """키워드로 장소를 수집하고 PostgreSQL에 저장한다.

    Args:
        query: 검색어 (예: '홍대 카페')
        db: 비동기 DB 세션
        area: 지역명 (로깅용)
        crawl_supplement: True이면 API 데이터 부족 시 웹 크롤링으로 보완
    Returns:
        저장된 Place 객체 리스트
    """
    # ── 1. 카카오 + 네이버 동시 호출 ──────────────────────────────
    kakao_task = kakao_api.search_by_keyword(query)
    naver_task = naver_api.search_places(query)

    kakao_results, naver_results = await asyncio.gather(
        kakao_task, naver_task, return_exceptions=True
    )

    raw: list[dict] = []
    if isinstance(kakao_results, list):
        raw.extend(kakao_results)
    if isinstance(naver_results, list):
        raw.extend(naver_results)

    if not raw:
        return []

    # ── 2. 중복 제거 (카카오 우선) ────────────────────────────────
    # 카카오 먼저 처리되도록 정렬
    raw.sort(key=lambda x: 0 if x["source"] == "kakao" else 1)
    unique = _deduplicate(raw)

    # ── 3. 보조 크롤링 (운영시간·설명 보완) ──────────────────────
    if crawl_supplement:
        crawl_tasks = [
            _crawl_supplement(p.get("place_url", ""), p.get("name", ""))
            for p in unique
        ]
        supplements = await asyncio.gather(*crawl_tasks)
    else:
        supplements = [{} for _ in unique]

    # ── 4. PostgreSQL 저장 ────────────────────────────────────────
    saved: list[Place] = []
    for item, supplement in zip(unique, supplements):
        place = await _upsert_place(item, supplement, db)
        if place:
            saved.append(place)

    await db.commit()

    # ── 5. Qdrant 벡터 저장 (OPENAI_API_KEY 있을 때만) ───────────
    if settings.OPENAI_API_KEY:
        vector_tasks = [_sync_vector(p, db) for p in saved]
        await asyncio.gather(*vector_tasks, return_exceptions=True)
        await db.commit()

    # ── 6. description 없는 장소 보완 (블로그 크롤링 + GPT 요약) ────
    from app.services.description_enricher import enrich_single_place
    needs_enrich = [p for p in saved if not p.description]
    if needs_enrich:
        enrich_results = await asyncio.gather(
            *[enrich_single_place(p, db) for p in needs_enrich],
            return_exceptions=True,
        )
        if any(r is True for r in enrich_results):
            await db.commit()

    return saved


async def _upsert_place(item: dict, supplement: dict, db: AsyncSession) -> Place | None:
    """이름+도로명 주소 기준으로 upsert한다."""
    name = item.get("name", "").strip()
    road_address = item.get("road_address", "") or item.get("address", "")
    if not name:
        return None

    # 기존 장소 조회
    stmt = select(Place).where(Place.name == name)
    if road_address:
        stmt = stmt.where(Place.road_address == road_address)
    result = await db.execute(stmt)
    place = result.scalar_one_or_none()

    description = (
        item.get("description")
        or supplement.get("crawled_summary")
        or ""
    )

    # 카카오 링크 → website_url (지도), 네이버 링크 → booking_page_url (예약)
    source = item.get("source", "")
    kakao_url = (item.get("place_url") or None) if source == "kakao" else None
    naver_url = (item.get("place_url") or None) if source == "naver" else None

    if place is None:
        place = Place(
            name=name,
            category=_map_category(item.get("category") or item.get("category_group", "기타")),
            description=description or None,
            phone=item.get("phone") or None,
            address=item.get("address") or None,
            road_address=road_address or None,
            latitude=Decimal(str(item["latitude"])) if item.get("latitude") else None,
            longitude=Decimal(str(item["longitude"])) if item.get("longitude") else None,
            website_url=kakao_url,
            booking_page_url=naver_url,
        )
        db.add(place)
        await db.flush()
    else:
        # 빈 필드만 보완
        if not place.phone and item.get("phone"):
            place.phone = item["phone"]
        if not place.description and description:
            place.description = description
        if not place.road_address and road_address:
            place.road_address = road_address
        if not place.website_url and kakao_url:
            place.website_url = kakao_url
        if not place.booking_page_url and naver_url:
            place.booking_page_url = naver_url

    # 운영시간 파싱 (크롤링 텍스트에서)
    if supplement.get("crawled_summary"):
        await _upsert_operating_hours(
            place, _parse_operating_hours(supplement["crawled_summary"]), db
        )

    return place


async def _upsert_operating_hours(
    place: Place, hours: list[dict], db: AsyncSession
) -> None:
    for h in hours:
        stmt = select(PlaceOperatingHour).where(
            PlaceOperatingHour.place_id == place.id,
            PlaceOperatingHour.day_of_week == h["day_of_week"],
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        def _to_time(s: str | None) -> time | None:
            if not s:
                return None
            parts = s.split(":")
            return time(int(parts[0]), int(parts[1]))

        if existing is None:
            db.add(PlaceOperatingHour(
                place_id=place.id,
                day_of_week=h["day_of_week"],
                open_time=_to_time(h.get("open_time")),
                close_time=_to_time(h.get("close_time")),
                is_closed=h.get("is_closed", False),
            ))
        else:
            existing.open_time  = _to_time(h.get("open_time")) or existing.open_time
            existing.close_time = _to_time(h.get("close_time")) or existing.close_time
            existing.is_closed  = h.get("is_closed", existing.is_closed)


async def _sync_vector(place: Place, db: AsyncSession) -> None:
    if not place.description:
        return
    try:
        point_id = await upsert_place_vector(
            place_id=place.id,
            summary=place.description,
            metadata={
                "name": place.name,
                "category": place.category,
                "area": place.address or "",
                "atmosphere_tags": place.atmosphere_tags or [],
            },
        )
        place.qdrant_id = point_id
    except Exception:
        pass


_CATEGORY_MAP = {
    # 카페/디저트
    "카페": "카페", "커피": "카페", "디저트": "카페", "베이커리": "카페",
    "브런치": "카페", "루프탑카페": "카페", "티룸": "카페", "버블티": "카페",
    "아이스크림": "카페", "와플": "카페", "크레페": "카페",
    # 음식점
    "음식점": "레스토랑", "한식": "레스토랑", "일식": "레스토랑",
    "중식": "레스토랑", "양식": "레스토랑", "맛집": "레스토랑",
    "베트남": "레스토랑", "태국": "레스토랑", "인도": "레스토랑",
    "고기": "레스토랑", "구이": "레스토랑", "회": "레스토랑",
    "분식": "레스토랑", "치킨": "레스토랑", "피자": "레스토랑",
    "삼겹살": "레스토랑", "갈비": "레스토랑", "냉면": "레스토랑",
    "국밥": "레스토랑", "라멘": "레스토랑", "스시": "레스토랑",
    "오마카세": "레스토랑", "이탈리안": "레스토랑", "파스타": "레스토랑",
    "스테이크": "레스토랑", "샤브샤브": "레스토랑", "해산물": "레스토랑",
    "이자카야": "레스토랑", "포장마차": "레스토랑",
    # 문화/전시
    "문화시설": "문화", "전시": "문화", "공연": "문화", "박물관": "문화",
    "미술관": "문화", "영화관": "문화", "극장": "문화", "갤러리": "문화",
    "복합문화공간": "문화", "팝업스토어": "문화", "팝업": "문화",
    "전망대": "문화", "아트센터": "문화", "콘서트홀": "문화",
    # 액티비티
    "놀이공원": "액티비티", "테마파크": "액티비티", "아쿠아리움": "액티비티",
    "수족관": "액티비티", "동물원": "액티비티", "식물원": "액티비티",
    "수목원": "액티비티", "체험": "액티비티", "방탈출": "액티비티",
    "볼링": "액티비티", "당구": "액티비티", "노래방": "액티비티",
    "vr": "액티비티", "게임": "액티비티", "클라이밍": "액티비티",
    "서핑": "액티비티", "스키": "액티비티", "스케이트": "액티비티",
    "아이스링크": "액티비티", "보드게임": "액티비티",
    "방방": "액티비티", "짚라인": "액티비티", "번지점프": "액티비티",
    "카약": "액티비티", "패들보드": "액티비티", "래프팅": "액티비티",
    # 체험/공방
    "공방": "체험", "도자기": "체험", "캔들": "체험", "가죽": "체험",
    "쿠킹클래스": "체험", "플라워": "체험", "사진관": "체험",
    "인생네컷": "체험", "포토": "체험", "네컷": "체험",
    # 관광/자연
    "관광명소": "관광", "공원": "관광", "명소": "관광", "해변": "관광",
    "야경": "관광", "한강": "관광", "수변": "관광", "산책": "관광",
    "캠핑": "관광", "글램핑": "관광", "드라이브": "관광",
    "등산": "관광", "해안": "관광", "섬": "관광", "폭포": "관광",
    # 힐링/스파
    "스파": "힐링", "찜질방": "힐링", "온천": "힐링", "마사지": "힐링",
    "사우나": "힐링", "목욕탕": "힐링",
    # 바/펍
    "술집": "바/펍", "바": "바/펍", "펍": "바/펍",
    "와인바": "바/펍", "칵테일바": "바/펍", "루프탑바": "바/펍",
    "호프": "바/펍", "맥주": "바/펍",
    # 숙박
    "숙박": "숙박", "호텔": "숙박", "펜션": "숙박", "게스트하우스": "숙박",
    "리조트": "숙박", "풀빌라": "숙박", "모텔": "숙박",
    # 쇼핑
    "쇼핑": "쇼핑", "백화점": "쇼핑", "아울렛": "쇼핑",
    "복합쇼핑몰": "쇼핑", "전통시장": "쇼핑", "시장": "쇼핑",
}


def _map_category(raw: str) -> str:
    raw_lower = raw.lower()
    # 긴 키를 먼저 검사해야 "방탈출카페"가 "카페" 대신 "방탈출"에 매칭됨
    for key, mapped in sorted(_CATEGORY_MAP.items(), key=lambda x: -len(x[0])):
        if key in raw_lower:
            return mapped
    return "기타"

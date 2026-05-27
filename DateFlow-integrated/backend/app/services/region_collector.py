"""지역 기반 데이트 장소 전체 수집 서비스 (3-Track 파이프라인).

Track 1 — Kakao 카테고리 검색: CE7·FD6·CT1·AT4·AD5·MT1
Track 2 — Kakao 키워드 검색: 카카오 카테고리에 없는 액티비티·공방·스파 등
Track 3 — 블로그 크롤링: '데이트 코스' 계열 쿼리로 트렌드·신규 장소 발굴
"""
import asyncio
import math
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.place import Place
from app.services import kakao_api
from app.services.place_collector import _map_category, _upsert_place
from app.services.web_collector import collect_by_crawl

# Track 2: 카카오 카테고리에 전용 코드가 없는 데이트 액티비티
ACTIVITY_KEYWORDS = [
    # 실내 액티비티
    "방탈출",
    "볼링장",
    "노래방",
    "VR방",
    "당구장",
    "보드게임카페",
    "아이스링크",
    "실내클라이밍",
    # 체험/공방
    "도자기공방",
    "캔들공방",
    "가죽공방",
    "쿠킹클래스",
    "플라워클래스",
    "사진관",
    "인생네컷",
    # 힐링/스파
    "스파",
    "찜질방",
    "온천",
    # 실외 액티비티
    "서핑",
    "카약",
    "패들보드",
    "짚라인",
    "번지점프",
    # 쇼핑
    "복합쇼핑몰",
    "전통시장",
]

# Track 3: 블로그에서 큐레이션된 데이트 장소 발굴
_BLOG_QUERY_TEMPLATES = [
    "{region} 데이트 코스",
    "{region} 커플 데이트",
    "{region} 데이트 장소 추천",
    "{region} 핫플레이스",
]

_DEDUP_DISTANCE_M = 50


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _save_kakao_items(items: list[dict], db: AsyncSession) -> list[Place]:
    saved: list[Place] = []
    for item in items:
        place = await _upsert_place(item, {}, db)
        if place:
            saved.append(place)
    return saved


async def _track1_category(
    latitude: float,
    longitude: float,
    radius_m: int,
    db: AsyncSession,
) -> list[Place]:
    """Kakao 카테고리 코드 6개를 병렬로 검색한다."""
    tasks = [
        kakao_api.search_by_category(
            category=code,
            longitude=longitude,
            latitude=latitude,
            radius_m=radius_m,
            size=15,  # 카테고리 검색 API 최대값
        )
        for code in kakao_api.CATEGORY_CODES
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: list[dict] = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    return await _save_kakao_items(all_items, db)


async def _track2_keyword(
    region: str,
    latitude: float,
    longitude: float,
    radius_m: int,
    db: AsyncSession,
) -> list[Place]:
    """ACTIVITY_KEYWORDS × Kakao 키워드 검색을 병렬로 수행한다."""
    async def _search_one(keyword: str) -> list[dict]:
        try:
            results = await kakao_api.search_by_keyword(
                query=f"{keyword} {region}",
                size=15,
            )
            # 반경 내 결과만 필터
            if latitude and longitude:
                results = [
                    r for r in results
                    if r.get("latitude") and r.get("longitude")
                    and _haversine_m(latitude, longitude, r["latitude"], r["longitude"]) <= radius_m
                ]
            return results
        except Exception:
            return []

    tasks = [_search_one(kw) for kw in ACTIVITY_KEYWORDS]
    results = await asyncio.gather(*tasks)

    all_items: list[dict] = []
    for r in results:
        all_items.extend(r)

    return await _save_kakao_items(all_items, db)


async def _track3_blog(region: str, db: AsyncSession) -> list[Place]:
    """블로그 크롤링으로 데이트 코스 장소를 발굴한다."""
    queries = [tmpl.format(region=region) for tmpl in _BLOG_QUERY_TEMPLATES]

    all_saved: list[Place] = []
    for query in queries:
        try:
            places = await collect_by_crawl(
                query=query,
                db=db,
                blog_display=5,
                category="기타",
            )
            all_saved.extend(places)
        except Exception:
            continue

    return all_saved


async def collect_by_region(
    region: str,
    latitude: float,
    longitude: float,
    radius_m: int,
    db: AsyncSession,
) -> dict:
    """3-Track으로 지역 내 데이트 장소를 전체 수집한다.

    Args:
        region: 지역명 (예: '홍대', '강남', '용인')
        latitude: 중심 위도
        longitude: 중심 경도
        radius_m: 검색 반경 (미터)
        db: 비동기 DB 세션
    Returns:
        {
            "total": int,
            "by_track": {"category": int, "keyword": int, "blog": int},
            "places": list[Place],
        }
    """
    # Track 1, 2는 같은 DB 세션을 쓰므로 순차 실행 (동시 실행 시 세션 충돌)
    try:
        track1_places = await _track1_category(latitude, longitude, radius_m, db)
    except Exception as e:
        import traceback, logging
        logging.error(f"Track1 오류: {e}\n{traceback.format_exc()}")
        track1_places = []
    await db.commit()

    try:
        track2_places = await _track2_keyword(region, latitude, longitude, radius_m, db)
    except Exception as e:
        import traceback, logging
        logging.error(f"Track2 오류: {e}\n{traceback.format_exc()}")
        track2_places = []
    await db.commit()

    # Track 3 (블로그 크롤링) — 순차 실행 (내부에서 commit 포함)
    track3_places = await _track3_blog(region, db)

    all_places = list(track1_places) + list(track2_places) + list(track3_places)

    # description 없는 장소 enrichment (OpenAI 없으면 크롤링 원문 저장, 있으면 GPT 요약 + 임베딩)
    from app.services.description_enricher import enrich_single_place
    needs_enrich = [p for p in all_places if not p.description]
    if needs_enrich:
        enrich_results = await asyncio.gather(
            *[enrich_single_place(p, db) for p in needs_enrich],
            return_exceptions=True,
        )
        if any(r is True for r in enrich_results):
            await db.commit()

    # Computed 컬럼(trust_score 등)을 DB에서 재로드
    for p in all_places:
        try:
            await db.refresh(p)
        except Exception:
            pass

    return {
        "total": len(all_places),
        "by_track": {
            "category": len(track1_places),
            "keyword": len(track2_places),
            "blog": len(track3_places),
        },
        "places": all_places,
    }

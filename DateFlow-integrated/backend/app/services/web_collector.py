"""웹 크롤링 전용 장소 수집기.

네이버 블로그 검색 API로 후기 글을 찾고, 본문을 크롤링하여
장소 이름·주소·전화번호를 추출해 DB에 저장한다.
저장 후 Kakao API로 검증하여 이름 수정 또는 삭제를 수행한다.
"""
import asyncio
import math
import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.place import Place
from app.schemas.crawl_schema import PolicyStatus
from app.services import naver_api, kakao_api
from app.services.safe_crawler import safe_fetch
from app.services.source_policy import check_source_policy
from app.core.config import settings

_VERIFY_DISTANCE_M = 200  # 같은 장소로 볼 좌표 거리 기준


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

_ADDR_PATTERN = re.compile(
    r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
    r"[^\s]*\s+[가-힣\d\s\-]+(?:로|길|동|읍|면|리)\s*\d*[-\d]*"
)
_PHONE_PATTERN = re.compile(r"0\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{4}")
_STORE_NAME_PATTERN = re.compile(
    r"(?:상호명|가게명|식당명|업체명|매장명)\s*[:：]\s*([가-힣a-zA-Z0-9\s]{2,30}?)(?:\s+(?:주소|전화|영업|위치|문의|휴무|가격)|$)"
)


def _extract_address(text: str) -> str | None:
    m = _ADDR_PATTERN.search(text)
    return m.group(0).strip() if m else None


def _extract_phone(text: str) -> str | None:
    m = _PHONE_PATTERN.search(text)
    return re.sub(r"[\s.]", "-", m.group(0)) if m else None


def _extract_store_name(text: str) -> str | None:
    m = _STORE_NAME_PATTERN.search(text)
    return m.group(1).strip() if m else None


def _to_mobile_url(url: str) -> str:
    """blog.naver.com → m.blog.naver.com (정적 HTML 제공)."""
    return re.sub(r"https?://blog\.naver\.com/", "https://m.blog.naver.com/", url)


async def _fetch_blog(url: str, max_length: int = 800) -> dict | None:
    """블로그 URL을 크롤링하여 요약·주소·전화를 추출한다."""
    try:
        fetch_url = _to_mobile_url(url)
        policy = await check_source_policy(fetch_url)
        if policy.status != PolicyStatus.allowed:
            return None
        result = await safe_fetch(fetch_url, max_length=max_length)
        if not result.summary:
            return None
        return {
            "summary": result.summary,
            "title": result.title or "",
            "address": _extract_address(result.summary),
            "phone": _extract_phone(result.summary),
            "store_name": _extract_store_name(result.summary),
            "freshness_score": result.freshness.score,
            "source_url": fetch_url,
        }
    except Exception:
        return None


async def _upsert_from_crawl(
    place_name: str,
    crawl_data: dict,
    category: str,
    db: AsyncSession,
) -> Place | None:
    """크롤링 데이터로 장소를 upsert한다."""
    name = place_name.strip()
    if not name:
        return None

    stmt = select(Place).where(Place.name == name)
    result = await db.execute(stmt)
    place = result.scalar_one_or_none()

    description = crawl_data.get("summary", "")[:500] or None
    address = crawl_data.get("address")
    phone = crawl_data.get("phone")

    if place is None:
        place = Place(
            name=name,
            category=category,
            description=description,
            phone=phone,
            address=address,
            road_address=address,
        )
        db.add(place)
        await db.flush()
    else:
        if not place.description and description:
            place.description = description
        if not place.phone and phone:
            place.phone = phone
        if not place.address and address:
            place.address = address

    return place


def _addr_region(addr: str) -> str:
    """주소에서 가장 세밀한 행정 단위(읍·면·동 우선)를 추출한다."""
    for suffix in ("읍", "면", "동"):
        m = re.search(rf"[가-힣]+{suffix}", addr)
        if m:
            return m.group(0)
    m = re.search(r"[가-힣]+(?:구|군|시)", addr)
    return m.group(0) if m else ""


async def _verify_and_fix(place: Place, db: AsyncSession) -> Place | None:
    """Kakao API로 장소 실존 여부를 검증하고 이름·좌표를 보정한다.

    매칭 기준 (우선순위 순):
      1. 좌표 200m 이내
      2. 도로명 포함 주소 일치 (로/길 포함 시)
      3. 같은 읍/면/동 내 Kakao 첫 번째 결과 (주소가 광역적일 때)
    매칭 안 되면 DB에서 삭제.
    """
    addr = place.road_address or place.address or ""
    region = _addr_region(addr)
    # 장소명 + 지역 단위만 사용 (주소 전체는 너무 길어서 Kakao 검색 실패)
    query = f"{place.name} {region}" if region else place.name

    try:
        results = await kakao_api.search_by_keyword(query, size=5)
    except Exception:
        return place  # API 오류 시 보존

    if not results:
        await db.delete(place)
        return None

    # 데이트 코스 관련 장소만 허용 (화이트리스트)
    _ALLOW_KEYWORDS = {
        # 음식/카페
        "카페", "음식점", "한식", "일식", "중식", "양식", "패스트푸드",
        "맥주", "호프", "바", "술집", "레스토랑", "베이커리", "디저트",
        "분식", "치킨", "피자", "버거", "국밥", "냉면", "브런치",
        "베트남", "태국", "인도", "고기", "구이", "회", "스시", "해산물",
        "삼겹살", "갈비", "라멘", "이자카야", "오마카세", "이탈리안", "스테이크",
        "와인바", "칵테일바", "루프탑바", "루프탑카페",
        # 문화/전시
        "문화시설", "공연", "전시", "관광", "박물관", "미술관", "갤러리",
        "영화관", "극장", "복합문화공간", "팝업", "아트센터", "전망대",
        # 액티비티
        "놀이공원", "테마파크", "아쿠아리움", "수족관", "동물원", "식물원",
        "수목원", "체험", "방탈출", "볼링", "노래방", "클라이밍", "서핑", "스키",
        "아이스링크", "보드게임", "vr", "짚라인", "번지점프",
        "카약", "패들보드", "래프팅",
        # 체험/공방
        "공방", "도자기공방", "캔들공방", "가죽공방", "쿠킹클래스", "플라워클래스",
        "사진관", "인생네컷", "포토스튜디오",
        # 힐링/스파
        "스파", "찜질방", "온천", "마사지", "사우나",
        # 자연/관광
        "공원", "야경", "해변", "캠핑", "글램핑", "드라이브코스",
        # 숙박
        "숙박", "호텔", "펜션", "리조트", "풀빌라", "글램핑",
        # 쇼핑
        "백화점", "아울렛", "복합쇼핑몰", "전통시장",
    }
    allowed = [
        r for r in results
        if any(kw in (r.get("category") or "") for kw in _ALLOW_KEYWORDS)
    ]
    # 허용 결과 없으면 원본 유지 (카테고리 정보 자체가 없는 경우 포함)
    results = allowed if allowed else [r for r in results if not r.get("category")]

    best: dict | None = None

    for r in results:
        kakao_addr = r.get("road_address") or r.get("address") or ""

        # 1. 좌표 거리 비교
        if (place.latitude and place.longitude
                and r.get("latitude") and r.get("longitude")):
            dist = _haversine_m(
                float(place.latitude), float(place.longitude),
                r["latitude"], r["longitude"],
            )
            if dist <= _VERIFY_DISTANCE_M:
                best = r
                break

        # 2. 도로명 포함 주소 일치 (주소에 로/길이 있을 때만 엄격히)
        if re.search(r"[가-힣]+(로|길)\s*\d", addr):
            road = re.search(r"[가-힣]+(로|길)[^\s]*", addr)
            if road and road.group(0) in kakao_addr:
                best = r
                break

        # 3. 같은 읍/면/동 내 첫 번째 결과 수용 (주소가 광역적일 때)
        if region and region in kakao_addr:
            best = r
            break

    if best is None:
        await db.delete(place)
        return None

    # 이름이 바뀌는 경우 기존 동명 장소와 중복 여부 확인
    new_name = best["name"]
    if new_name != place.name:
        dup_stmt = select(Place).where(Place.name == new_name, Place.id != place.id)
        dup_result = await db.execute(dup_stmt)
        existing = dup_result.scalar_one_or_none()
        if existing:
            # 기존 장소가 이미 있으면 현재 항목 삭제
            await db.delete(place)
            return None

    # 이름·좌표·전화·주소 보정
    place.name = best["name"]
    if best.get("latitude"):
        place.latitude = Decimal(str(best["latitude"]))
    if best.get("longitude"):
        place.longitude = Decimal(str(best["longitude"]))
    if not place.phone and best.get("phone"):
        place.phone = best["phone"]
    if best.get("road_address"):
        place.road_address = best["road_address"]
    if best.get("address"):
        place.address = best["address"]
    if best.get("category"):
        from app.services.place_collector import _map_category
        place.category = _map_category(best["category"])

    return place


async def collect_by_crawl(
    query: str,
    db: AsyncSession,
    blog_display: int = 5,
    category: str = "기타",
) -> list[Place]:
    """블로그 후기 크롤링만으로 장소를 수집·저장한다.

    Args:
        query: 검색어 (예: '용인 모현읍 맛집')
        db: 비동기 DB 세션
        blog_display: 블로그 검색 결과 수 (최대 10)
        category: 수집된 장소에 적용할 기본 카테고리
    Returns:
        저장된 Place 객체 리스트
    """
    # 1. 블로그 검색
    try:
        blog_items = await naver_api.search_blog(query, display=min(blog_display, 10))
    except Exception:
        return []

    if not blog_items:
        return []

    # 2. 병렬 크롤링
    crawl_tasks = [_fetch_blog(item["link"]) for item in blog_items]
    crawl_results = await asyncio.gather(*crawl_tasks)

    # 3. 저장
    saved: list[Place] = []
    for blog_item, crawl_data in zip(blog_items, crawl_results):
        if not crawl_data:
            continue

        # 장소명 우선순위: 본문 상호명 > 제목 따옴표 > 제목 키워드 파싱
        title = blog_item.get("title", "")
        store_name = crawl_data.get("store_name")
        if store_name:
            place_name = store_name
        else:
            name_match = re.search(r'[「『""\'](.*?)[」』""\']', title)
            if name_match:
                place_name = name_match.group(1).strip()
            else:
                # 검색어에서 추출한 키워드(맛집/카페/식당 등) 기준으로 앞뒤 장소명 파싱
                kw_terms = re.findall(r"[가-힣]{2,}", query)
                kw_pattern = "|".join(kw_terms) if kw_terms else "맛집"
                kw_match = re.search(
                    rf'(?:{kw_pattern})\s+([가-힣a-zA-Z0-9]+(?:\s[가-힣a-zA-Z0-9]+){{0,2}})', title
                )
                if not kw_match:
                    kw_match = re.search(
                        rf'([가-힣a-zA-Z0-9]+(?:\s[가-힣a-zA-Z0-9]+)?)\s+(?:{kw_pattern})', title
                    )
                place_name = kw_match.group(1).strip() if kw_match else title[:20].strip()

        if not place_name:
            continue

        place = await _upsert_from_crawl(place_name, crawl_data, category, db)
        if place:
            saved.append(place)

    if saved:
        await db.commit()

    # 4. Kakao 검증 — 이름 수정 or 삭제
    verified: list[Place] = []
    for place in saved:
        result = await _verify_and_fix(place, db)
        if result:
            verified.append(result)
    await db.commit()
    saved = verified

    # 5. description 보완 + 벡터 저장 (OpenAI 없으면 크롤링 원문 저장, 있으면 GPT 요약 + 임베딩)
    from app.services.description_enricher import enrich_single_place
    if saved:
        enrich_results = await asyncio.gather(
            *[enrich_single_place(p, db) for p in saved],
            return_exceptions=True,
        )
        if any(r is True for r in enrich_results):
            await db.commit()

    return saved

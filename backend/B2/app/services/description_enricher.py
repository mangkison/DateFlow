"""description 보완 파이프라인.

Kakao/Naver API 수집 장소 중 description=NULL인 것을 대상으로:
  1. 네이버 블로그 검색 → "{place_name} {region} 후기"
  2. 블로그 본문 크롤링 (mobile URL)
  3. OPENAI_API_KEY 있으면 gpt-4o-mini 요약, 없으면 원문 500자 저장
  4. text-embedding-3-small → Qdrant 저장

블로그를 찾지 못하거나 크롤링 실패 시 해당 장소는 건너뜀(qdrant_id=NULL 유지).
코스 추천 시 qdrant_id=NULL 장소는 카테고리+지역 DB 폴백으로 처리한다.
"""
import re

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.place import Place
from app.schemas.crawl_schema import PolicyStatus
from app.services import naver_api
from app.services.safe_crawler import safe_fetch
from app.services.source_policy import check_source_policy
from app.services.vector_store import upsert_place_vector

_openai_client: AsyncOpenAI | None = None

_GPT_MODEL = "gpt-4o-mini"
_GPT_MAX_TOKENS = 200
_CRAWL_MAX_LENGTH = 1500
_BATCH_DEFAULT = 50


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _to_mobile_url(url: str) -> str:
    return re.sub(r"https?://blog\.naver\.com/", "https://m.blog.naver.com/", url)


def _addr_region(addr: str) -> str:
    """주소에서 가장 세밀한 행정 단위(읍·면·동 우선)를 반환한다."""
    for suffix in ("읍", "면", "동"):
        m = re.search(rf"[가-힣]+{suffix}", addr)
        if m:
            return m.group(0)
    m = re.search(r"[가-힣]+(?:구|군|시)", addr)
    return m.group(0) if m else ""


async def _crawl_blog(url: str) -> str | None:
    """블로그 URL을 크롤링하여 본문 텍스트를 반환한다. 실패 시 None."""
    try:
        fetch_url = _to_mobile_url(url)
        policy = await check_source_policy(fetch_url)
        if policy.status != PolicyStatus.allowed:
            return None
        result = await safe_fetch(fetch_url, max_length=_CRAWL_MAX_LENGTH)
        return result.summary if result.summary else None
    except Exception:
        return None


async def _gpt_summarize(raw_text: str, place_name: str, category: str) -> str | None:
    """블로그 본문을 gpt-4o-mini로 요약한다. API 키 없거나 오류 시 None."""
    if not settings.OPENAI_API_KEY:
        return None
    prompt = (
        f"다음은 '{place_name}'({category})에 대한 블로그 후기입니다.\n"
        "이 장소의 핵심 특징을 2~3문장으로 요약해주세요.\n"
        "분위기, 추천 이유, 특별한 점을 포함하되 방문자의 개인 일상·감상은 제외하세요.\n\n"
        f"후기:\n{raw_text[:_CRAWL_MAX_LENGTH]}\n\n요약:"
    )
    try:
        resp = await _get_openai().chat.completions.create(
            model=_GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=_GPT_MAX_TOKENS,
            temperature=0.3,
        )
        text = resp.choices[0].message.content.strip()
        return text or None
    except Exception:
        return None


async def _embed_and_save(place: Place) -> None:
    """description을 임베딩하여 Qdrant에 저장하고 place.qdrant_id를 갱신한다."""
    if not settings.OPENAI_API_KEY or not place.description:
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


async def enrich_single_place(place: Place, db: AsyncSession) -> bool:
    """장소 1개의 description을 보완하고 Qdrant에 임베딩한다.

    description이 이미 있으면 임베딩만 재시도한다.

    Returns:
        True  - description이 채워짐 (기존 포함)
        False - 블로그를 찾지 못했거나 크롤링 전부 실패
    """
    # description 있으면 임베딩만 보완
    if place.description:
        if not place.qdrant_id:
            await _embed_and_save(place)
        return True

    # 블로그 검색 쿼리: 장소명 + 가장 세밀한 행정 단위
    addr = place.road_address or place.address or ""
    region = _addr_region(addr)
    query = f"{place.name} {region} 후기" if region else f"{place.name} 후기"

    blog_items = await naver_api.search_blog(query, display=3)
    if not blog_items:
        return False

    # 블로그 순서대로 크롤링, 첫 성공 사용
    raw_text: str | None = None
    for item in blog_items:
        raw_text = await _crawl_blog(item["link"])
        if raw_text:
            break

    if not raw_text:
        return False

    # GPT 요약 (키 없으면 원문 500자 저장)
    summary = await _gpt_summarize(raw_text, place.name, place.category)
    place.description = summary or raw_text[:500]

    await _embed_and_save(place)
    return True


async def enrich_missing_descriptions(
    db: AsyncSession,
    limit: int = _BATCH_DEFAULT,
) -> dict:
    """description=NULL 장소를 일괄 보완한다.

    Args:
        limit: 한 번에 처리할 최대 수 (API 비용 제어, 기본 50)
    Returns:
        {"total": int, "enriched": int, "skipped": int}
    """
    stmt = (
        select(Place)
        .where(
            Place.is_active == True,
            Place.description.is_(None),
        )
        .order_by(Place.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    places = result.scalars().all()

    enriched = 0
    skipped = 0
    for place in places:
        success = await enrich_single_place(place, db)
        if success:
            enriched += 1
        else:
            skipped += 1

    await db.commit()
    return {"total": len(places), "enriched": enriched, "skipped": skipped}

"""
크롤링 파이프라인 오케스트레이터.
CrawlTarget → safe_fetch → PostgreSQL(CrawlLog + Place) → Qdrant 순서로 처리.
"""
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl import CrawlLog, CrawlTarget
from app.models.place import Place
from app.schemas.crawl_schema import CrawlResult
from app.services.safe_crawler import safe_fetch
from app.services.vector_store import upsert_place_vector

_MAX_FAIL_COUNT = 3


async def run_crawl_target(target_id: uuid.UUID, db: AsyncSession) -> CrawlLog:
    result = await db.execute(
        select(CrawlTarget).where(CrawlTarget.id == target_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise ValueError(f"CrawlTarget {target_id} 없음")
    if not target.is_active:
        raise ValueError(f"CrawlTarget {target_id} 비활성화 상태")

    started_at = datetime.now(tz=timezone.utc)
    start_mono = time.monotonic()

    log = CrawlLog(
        crawl_target_id=target.id,
        started_at=started_at,
        status="running",
    )
    db.add(log)
    await db.flush()

    try:
        crawl_result = await _fetch_with_cache(target)
        duration_ms = int((time.monotonic() - start_mono) * 1000)

        parsed = _build_parsed_data(crawl_result)
        place = await _upsert_place(target, parsed, db)

        log.status = "success"
        log.parsed_data = parsed
        log.raw_data = {"url": crawl_result.url, "content_length_bytes": crawl_result.content_length_bytes}
        log.records_count = 1
        log.http_status_code = 200
        log.duration_ms = duration_ms
        log.ended_at = datetime.now(tz=timezone.utc)

        target.last_crawled_at = started_at
        target.fail_count = 0

        # Qdrant 벡터 저장 (요약이 있고 OPENAI_API_KEY가 설정된 경우)
        if place and crawl_result.summary:
            await _sync_vector(place, crawl_result.summary, db)

    except Exception as exc:
        duration_ms = int((time.monotonic() - start_mono) * 1000)
        log.status = "failed"
        log.error_message = str(exc)
        log.duration_ms = duration_ms
        log.ended_at = datetime.now(tz=timezone.utc)

        target.fail_count = (target.fail_count or 0) + 1
        if target.fail_count >= _MAX_FAIL_COUNT:
            target.is_active = False

    await db.commit()
    await db.refresh(log)
    return log


async def _fetch_with_cache(target: CrawlTarget) -> CrawlResult:
    """ETag/Last-Modified 캐시 헤더를 활용해 불필요한 수집을 건너뛴다."""
    import httpx
    from app.services.source_policy import check_source_policy
    from app.schemas.crawl_schema import PolicyStatus

    policy = await check_source_policy(target.target_url)
    if policy.status != PolicyStatus.allowed:
        raise ValueError(f"수집 불가: {policy.reason}")

    # 조건부 요청 헤더 구성
    extra_headers: dict[str, str] = {}
    if target.etag:
        extra_headers["If-None-Match"] = target.etag
    if target.last_modified:
        extra_headers["If-Modified-Since"] = target.last_modified.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

    # 캐시 헤더가 있으면 HEAD 먼저 확인
    if extra_headers:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.head(target.target_url, headers=extra_headers)
            if resp.status_code == 304:
                raise ValueError("304 Not Modified — 콘텐츠 변경 없음, 수집 스킵")
            # 새 캐시 헤더 갱신
            if "ETag" in resp.headers:
                target.etag = resp.headers["ETag"]

    return await safe_fetch(target.target_url)


def _build_parsed_data(result: CrawlResult) -> dict:
    return {
        "title": result.title,
        "summary": result.summary,
        "freshness": {
            "level": result.freshness.level.value,
            "score": result.freshness.score,
            "published_at": result.freshness.published_at.isoformat()
            if result.freshness.published_at
            else None,
        },
        "fetched_at": result.fetched_at.isoformat(),
        "content_length_bytes": result.content_length_bytes,
    }


async def _upsert_place(
    target: CrawlTarget, parsed: dict, db: AsyncSession
) -> Place | None:
    if target.crawl_type not in ("place_info", "reviews"):
        return None

    if target.place_id:
        result = await db.execute(select(Place).where(Place.id == target.place_id))
        place = result.scalar_one_or_none()
        if place is None:
            return None
        _apply_parsed_to_place(place, parsed, target.source, target.crawl_type)
    else:
        # 신규 장소 생성
        place = Place(
            name=parsed.get("title") or "이름 미상",
            category="기타",
        )
        _apply_parsed_to_place(place, parsed, target.source, target.crawl_type)
        db.add(place)
        await db.flush()
        target.place_id = place.id

    return place


def _apply_parsed_to_place(
    place: Place, parsed: dict, source: str, crawl_type: str
) -> None:
    if crawl_type == "place_info":
        if parsed.get("title"):
            place.name = parsed["title"]
        if parsed.get("summary"):
            place.description = parsed["summary"]

    if crawl_type == "reviews":
        rating_val = parsed.get("rating")
        if rating_val is not None:
            rating = Decimal(str(rating_val))
            if source == "naver":
                place.naver_rating = rating
            elif source == "kakao":
                place.kakao_rating = rating
            elif source == "google":
                place.google_rating = rating


async def _sync_vector(place: Place, summary: str, db: AsyncSession) -> None:
    from app.core.config import settings
    if not settings.OPENAI_API_KEY:
        return

    try:
        point_id = await upsert_place_vector(
            place_id=place.id,
            summary=summary,
            metadata={
                "name": place.name,
                "category": place.category,
                "area": place.area,
                "atmosphere_tags": place.atmosphere_tags or [],
            },
        )
        place.qdrant_id = point_id
    except Exception:
        pass  # 벡터 저장 실패는 크롤 성공에 영향 없음

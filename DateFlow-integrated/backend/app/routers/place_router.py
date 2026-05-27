from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.place import Place
from app.schemas.place_schema import (
    PlaceBookingEnrichResponse, PlaceCollectRequest, PlaceCollectResponse,
    PlaceEnrichResponse, PlaceListResponse, PlaceResult, RegionCollectRequest,
    RegionCollectResponse, TrackCountResponse, WebCollectRequest,
)
from app.services.booking_enricher import enrich_booking_urls
from app.services.description_enricher import enrich_missing_descriptions
from app.services.place_collector import collect_and_save
from app.services.region_collector import collect_by_region
from app.services.web_collector import collect_by_crawl

router = APIRouter(prefix="/places", tags=["places"])


@router.get(
    "",
    response_model=PlaceListResponse,
    summary="장소 목록 조회",
    description="DB에 저장된 장소를 카테고리·지역으로 필터링하여 조회합니다.",
)
async def list_places(
    category: Optional[str] = Query(None, description="카테고리 필터 (예: 카페, 레스토랑, 액티비티)"),
    area: Optional[str] = Query(None, description="지역 필터 — 주소에 포함된 문자열 (예: 모현읍, 강남)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 결과 수"),
    db: AsyncSession = Depends(get_db),
) -> PlaceListResponse:
    stmt = select(Place).where(Place.is_active == True)

    if category:
        stmt = stmt.where(Place.category == category)
    if area:
        stmt = stmt.where(
            (Place.road_address.ilike(f"%{area}%")) |
            (Place.address.ilike(f"%{area}%"))
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Place.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    places = result.scalars().all()

    return PlaceListResponse(
        total=total,
        page=page,
        size=size,
        places=[PlaceResult.model_validate(p) for p in places],
    )


@router.get(
    "/{place_id}",
    response_model=PlaceResult,
    summary="장소 상세 조회",
)
async def get_place(
    place_id: str,
    db: AsyncSession = Depends(get_db),
) -> PlaceResult:
    import uuid
    try:
        uid = uuid.UUID(place_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 ID 형식")

    result = await db.execute(select(Place).where(Place.id == uid))
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="장소를 찾을 수 없습니다")
    return PlaceResult.model_validate(place)


@router.post(
    "/enrich",
    response_model=PlaceEnrichResponse,
    summary="description 보완 — 블로그 크롤링 + GPT 요약 + 임베딩",
    description=(
        "description이 없는 장소를 대상으로 네이버 블로그를 검색·크롤링하여 설명을 채웁니다. "
        "OPENAI_API_KEY가 설정된 경우 gpt-4o-mini로 요약 후 Qdrant에 임베딩합니다. "
        "블로그를 찾지 못한 장소는 건너뛰며(skipped), "
        "코스 추천 시 이 장소들은 카테고리·지역 기반 DB 폴백으로 처리됩니다."
    ),
)
async def enrich_places(
    limit: int = Query(50, ge=1, le=200, description="한 번에 처리할 최대 장소 수 (API 비용 제어)"),
    db: AsyncSession = Depends(get_db),
) -> PlaceEnrichResponse:
    result = await enrich_missing_descriptions(db, limit=limit)
    return PlaceEnrichResponse(**result)


@router.post(
    "/enrich-booking",
    response_model=PlaceBookingEnrichResponse,
    summary="네이버 예약 링크 보완",
    description=(
        "booking_page_url이 없는 장소를 대상으로 네이버 Local Search API로 "
        "플레이스 URL을 찾아 저장합니다. "
        "네이버 플레이스 페이지에는 예약 버튼이 포함되어 있습니다."
    ),
)
async def enrich_booking(
    limit: int = Query(100, ge=1, le=500, description="한 번에 처리할 최대 장소 수"),
    db: AsyncSession = Depends(get_db),
) -> PlaceBookingEnrichResponse:
    result = await enrich_booking_urls(db, limit=limit)
    return PlaceBookingEnrichResponse(**result)


@router.post(
    "/collect-region",
    response_model=RegionCollectResponse,
    summary="지역 기반 데이트 장소 전체 수집 (3-Track)",
    description=(
        "지역 좌표 주변의 데이트 장소를 3가지 방법으로 수집합니다.\n"
        "- Track 1: Kakao 카테고리(카페·음식점·문화·관광·숙박·쇼핑) 반경 검색\n"
        "- Track 2: 방탈출·공방·스파 등 키워드 검색 (카카오 카테고리 미지원)\n"
        "- Track 3: '데이트 코스' 블로그 크롤링으로 트렌드·신규 장소 발굴"
    ),
)
async def collect_region(
    req: RegionCollectRequest,
    db: AsyncSession = Depends(get_db),
) -> RegionCollectResponse:
    try:
        result = await collect_by_region(
            region=req.region,
            latitude=req.latitude,
            longitude=req.longitude,
            radius_m=req.radius_m,
            db=db,
        )
        return RegionCollectResponse(
            region=req.region,
            total=result["total"],
            by_track=TrackCountResponse(**result["by_track"]),
            places=[PlaceResult.model_validate(p) for p in result["places"]],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"지역 수집 실패: {exc}",
        )


@router.post(
    "/collect",
    response_model=PlaceCollectResponse,
    summary="장소 수집 — Kakao·Naver API + 웹 크롤링 보조",
    description=(
        "카카오 로컬 API와 네이버 지역검색 API로 장소를 수집하여 PostgreSQL에 저장합니다. "
        "crawl_supplement=true이면 API에서 얻지 못한 운영시간·설명을 "
        "웹 크롤링으로 보조 수집합니다. "
        "중복 장소는 자동으로 병합됩니다."
    ),
)
async def collect_places(
    req: PlaceCollectRequest,
    db: AsyncSession = Depends(get_db),
) -> PlaceCollectResponse:
    try:
        places = await collect_and_save(
            query=req.query,
            db=db,
            crawl_supplement=req.crawl_supplement,
        )
        return PlaceCollectResponse(
            query=req.query,
            total=len(places),
            places=[PlaceResult.model_validate(p) for p in places],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"장소 수집 실패: {exc}",
        )


@router.post(
    "/collect-web",
    response_model=PlaceCollectResponse,
    summary="장소 수집 — 블로그 크롤링 전용",
    description=(
        "Kakao·Naver Place API 없이 네이버 블로그 검색 후기만을 크롤링하여 장소를 수집합니다. "
        "API 수집 대비 정확도는 낮지만, API 할당량 소모 없이 다양한 후기 텍스트를 확보합니다."
    ),
)
async def collect_places_web(
    req: WebCollectRequest,
    db: AsyncSession = Depends(get_db),
) -> PlaceCollectResponse:
    try:
        places = await collect_by_crawl(
            query=req.query,
            db=db,
            blog_display=req.blog_display,
            category=req.category,
        )
        return PlaceCollectResponse(
            query=req.query,
            total=len(places),
            places=[PlaceResult.model_validate(p) for p in places],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"크롤링 수집 실패: {exc}",
        )

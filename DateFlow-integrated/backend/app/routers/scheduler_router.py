"""스케줄러 관리 엔드포인트."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import scheduler as sched
from app.services.booking_enricher import enrich_booking_urls
from app.services.description_enricher import enrich_missing_descriptions

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class RegionEntry(BaseModel):
    name: str = Field(..., description="지역명 (예: '부천', '전주')")
    latitude: float = Field(..., description="중심 위도")
    longitude: float = Field(..., description="중심 경도")
    radius_m: int = Field(1500, ge=100, le=20000, description="검색 반경 (미터)")


# ── 스케줄러 상태 ─────────────────────────────────────────────

@router.get(
    "/status",
    summary="스케줄러 상태 조회",
    description="등록된 Job 목록과 다음 실행 시간, 마지막 결과를 반환합니다.",
)
async def get_status() -> dict:
    return sched.get_status()


# ── 스케줄 설정 ──────────────────────────────────────────────

@router.get(
    "/schedule",
    summary="스케줄 설정 조회",
    description="각 Job의 현재 실행 주기 설정을 반환합니다.",
)
async def get_schedule() -> dict:
    return sched.get_schedule()


@router.patch(
    "/schedule/{job_id}",
    summary="스케줄 변경",
    description=(
        "Job의 실행 주기를 변경합니다. 서버 재시작 후에도 유지됩니다.\n\n"
        "**interval 방식** (매 N시간):\n"
        "```json\n{\"type\": \"interval\", \"hours\": 3}\n```\n\n"
        "**cron 방식** (특정 요일·시각):\n"
        "```json\n{\"type\": \"cron\", \"day_of_week\": \"mon\", \"hour\": 2, \"minute\": 30}\n```\n\n"
        "`day_of_week`: mon/tue/wed/thu/fri/sat/sun (매일은 `*`)"
    ),
)
async def update_schedule(job_id: str, cfg: dict) -> dict:
    valid_ids = {"enrich_descriptions", "enrich_bookings", "collect_regions"}
    if job_id not in valid_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"유효한 job_id: {sorted(valid_ids)}",
        )
    if cfg.get("type") not in ("interval", "cron"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="type은 'interval' 또는 'cron'이어야 합니다.",
        )
    try:
        return sched.update_schedule(job_id, cfg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ── 지역 목록 CRUD ────────────────────────────────────────────

@router.get(
    "/regions",
    summary="수집 지역 목록 조회",
    description="스케줄러가 매주 수집할 지역 목록을 반환합니다.",
)
async def list_regions() -> list[dict]:
    return sched.get_regions()


@router.post(
    "/regions",
    summary="수집 지역 추가",
    description="지역을 추가합니다. 같은 이름이 이미 있으면 덮어씁니다.",
    status_code=status.HTTP_201_CREATED,
)
async def add_region(entry: RegionEntry) -> list[dict]:
    return sched.add_region(entry.model_dump())


@router.delete(
    "/regions/{name}",
    summary="수집 지역 삭제",
    description="지역명으로 수집 목록에서 삭제합니다.",
)
async def delete_region(name: str) -> list[dict]:
    before = sched.get_regions()
    after = sched.remove_region(name)
    if len(before) == len(after):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{name}' 지역을 찾을 수 없습니다.",
        )
    return after


# ── 즉시 실행 ─────────────────────────────────────────────────

@router.post(
    "/run/collect-regions",
    summary="전체 지역 수집 즉시 실행",
    description="스케줄을 기다리지 않고 전체 지역 수집 Job을 백그라운드로 즉시 실행합니다.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_collect_regions(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(sched._job_collect_regions)
    regions = sched.get_regions()
    return {
        "status": "accepted",
        "message": f"{len(regions)}개 지역 수집을 백그라운드로 시작했습니다.",
        "regions": [r["name"] for r in regions],
    }


@router.post(
    "/run/enrich-descriptions",
    summary="description 보완 즉시 실행",
)
async def run_enrich_descriptions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        result = await enrich_missing_descriptions(db, limit=limit)
        return {**result, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/run/enrich-bookings",
    summary="예약 링크 보완 즉시 실행",
)
async def run_enrich_bookings(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        result = await enrich_booking_urls(db, limit=limit)
        return {**result, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

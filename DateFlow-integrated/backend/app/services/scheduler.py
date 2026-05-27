"""주기적 백그라운드 작업 스케줄러 (APScheduler AsyncIOScheduler).

등록된 Job:
  - enrich_descriptions  : 매 1시간 — description 없는 장소에 블로그 크롤링 + GPT 요약
  - enrich_bookings      : 매 2시간 — booking_page_url 없는 장소에 네이버 지도 링크 보완
  - collect_regions      : 매주 일요일 03:00 — 전국 주요 지역 데이트 장소 수집
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import AsyncSessionLocal
from app.services.booking_enricher import enrich_booking_urls
from app.services.description_enricher import enrich_missing_descriptions
from app.services.region_collector import collect_by_region

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

_REGIONS_FILE = Path("regions.json")
_SCHEDULE_FILE = Path("schedule_config.json")

_DEFAULT_SCHEDULE: dict = {
    "enrich_descriptions": {"type": "interval", "hours": 1},
    "enrich_bookings":     {"type": "interval", "hours": 2},
    "collect_regions":     {"type": "cron", "day_of_week": "sun", "hour": 3},
}

_DEFAULT_REGIONS: list[dict] = [
    # 서울
    {"name": "홍대",   "latitude": 37.5563, "longitude": 126.9234, "radius_m": 1000},
    {"name": "강남",   "latitude": 37.4979, "longitude": 127.0276, "radius_m": 1500},
    {"name": "이태원", "latitude": 37.5340, "longitude": 126.9940, "radius_m": 1000},
    {"name": "신촌",   "latitude": 37.5551, "longitude": 126.9368, "radius_m": 800},
    {"name": "건대",   "latitude": 37.5403, "longitude": 127.0694, "radius_m": 1000},
    {"name": "성수",   "latitude": 37.5444, "longitude": 127.0557, "radius_m": 1000},
    {"name": "여의도", "latitude": 37.5219, "longitude": 126.9245, "radius_m": 1200},
    {"name": "인사동", "latitude": 37.5742, "longitude": 126.9862, "radius_m": 800},
    {"name": "합정",   "latitude": 37.5498, "longitude": 126.9137, "radius_m": 800},
    {"name": "종로",   "latitude": 37.5700, "longitude": 126.9820, "radius_m": 1000},
    # 경기·인천
    {"name": "수원",      "latitude": 37.2636, "longitude": 127.0286, "radius_m": 2000},
    {"name": "판교",      "latitude": 37.3948, "longitude": 127.1108, "radius_m": 1500},
    {"name": "일산",      "latitude": 37.6762, "longitude": 126.7671, "radius_m": 2000},
    {"name": "파주헤이리", "latitude": 37.7879, "longitude": 126.7103, "radius_m": 2000},
    {"name": "가평",      "latitude": 37.8314, "longitude": 127.5108, "radius_m": 3000},
    {"name": "인천송도",  "latitude": 37.3926, "longitude": 126.6480, "radius_m": 2000},
    {"name": "인천개항장", "latitude": 37.4745, "longitude": 126.6172, "radius_m": 1000},
    # 부산
    {"name": "해운대", "latitude": 35.1587, "longitude": 129.1604, "radius_m": 2000},
    {"name": "광안리", "latitude": 35.1531, "longitude": 129.1185, "radius_m": 1000},
    {"name": "서면",   "latitude": 35.1576, "longitude": 129.0593, "radius_m": 1000},
    {"name": "남포동", "latitude": 35.0978, "longitude": 129.0313, "radius_m": 800},
    # 대구
    {"name": "동성로", "latitude": 35.8714, "longitude": 128.5941, "radius_m": 1000},
    {"name": "수성못", "latitude": 35.8507, "longitude": 128.6296, "radius_m": 1000},
    # 광주
    {"name": "충장로", "latitude": 35.1482, "longitude": 126.9164, "radius_m": 800},
    {"name": "양림동", "latitude": 35.1384, "longitude": 126.9107, "radius_m": 800},
    # 대전
    {"name": "유성", "latitude": 36.3624, "longitude": 127.3564, "radius_m": 1500},
    {"name": "둔산", "latitude": 36.3510, "longitude": 127.3886, "radius_m": 1500},
    # 강원
    {"name": "춘천", "latitude": 37.8747, "longitude": 127.7340, "radius_m": 2000},
    {"name": "강릉", "latitude": 37.7519, "longitude": 128.8761, "radius_m": 2000},
    {"name": "속초", "latitude": 38.2070, "longitude": 128.5919, "radius_m": 2000},
    # 제주
    {"name": "제주시", "latitude": 33.4996, "longitude": 126.5312, "radius_m": 3000},
    {"name": "서귀포", "latitude": 33.2541, "longitude": 126.5600, "radius_m": 3000},
]

# 마지막 실행 결과 (상태 조회용)
_last_results: dict[str, dict] = {
    "enrich_descriptions": {},
    "enrich_bookings": {},
    "collect_regions": {},
}


# ── 지역 목록 관리 ────────────────────────────────────────────

def load_regions() -> list[dict]:
    """regions.json 로드. 파일이 없으면 기본값으로 생성 후 반환."""
    if _REGIONS_FILE.exists():
        try:
            return json.loads(_REGIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    save_regions(_DEFAULT_REGIONS)
    return list(_DEFAULT_REGIONS)


def save_regions(regions: list[dict]) -> None:
    _REGIONS_FILE.write_text(
        json.dumps(regions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── 스케줄 설정 관리 ──────────────────────────────────────────

def load_schedule() -> dict:
    """schedule_config.json 로드. 없으면 기본값으로 생성 후 반환."""
    if _SCHEDULE_FILE.exists():
        try:
            return json.loads(_SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    save_schedule(_DEFAULT_SCHEDULE)
    return dict(_DEFAULT_SCHEDULE)


def save_schedule(config: dict) -> None:
    _SCHEDULE_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _make_trigger(cfg: dict):
    if cfg["type"] == "interval":
        return IntervalTrigger(hours=cfg["hours"])
    return CronTrigger(
        day_of_week=cfg.get("day_of_week", "*"),
        hour=cfg.get("hour", 0),
        minute=cfg.get("minute", 0),
        timezone="Asia/Seoul",
    )


def update_schedule(job_id: str, cfg: dict) -> dict:
    """Job 하나의 스케줄을 변경하고 즉시 재등록한다."""
    config = load_schedule()
    config[job_id] = cfg
    save_schedule(config)

    job_funcs = {
        "enrich_descriptions": _job_enrich_descriptions,
        "enrich_bookings":     _job_enrich_bookings,
        "collect_regions":     _job_collect_regions,
    }
    job_names = {
        "enrich_descriptions": "description 보완 (블로그 크롤링 + GPT)",
        "enrich_bookings":     "예약 링크 보완 (네이버 지도)",
        "collect_regions":     "주요 지역 데이트 장소 수집 (주간)",
    }
    if job_id in job_funcs and scheduler.running:
        scheduler.reschedule_job(job_id, trigger=_make_trigger(cfg))
        logger.info(f"[스케줄러] {job_id} 스케줄 변경: {cfg}")

    return config


def get_schedule() -> dict:
    return load_schedule()


# ── 지역 목록 관리 ────────────────────────────────────────────

def get_regions() -> list[dict]:
    return load_regions()


def add_region(entry: dict) -> list[dict]:
    """지역을 추가하고 저장한다. 동일 name이 있으면 덮어쓴다."""
    regions = load_regions()
    regions = [r for r in regions if r["name"] != entry["name"]]
    regions.append(entry)
    save_regions(regions)
    return regions


def remove_region(name: str) -> list[dict]:
    """name으로 지역을 삭제하고 저장한다."""
    regions = [r for r in load_regions() if r["name"] != name]
    save_regions(regions)
    return regions


# ── 스케줄 Job 함수 ───────────────────────────────────────────

async def _job_enrich_descriptions() -> None:
    logger.info("[스케줄러] description 보완 시작")
    async with AsyncSessionLocal() as db:
        try:
            result = await enrich_missing_descriptions(db, limit=50)
            _last_results["enrich_descriptions"] = {
                **result,
                "ran_at": datetime.now().isoformat(),
            }
            logger.info(f"[스케줄러] description 보완 완료: {result}")
        except Exception as e:
            logger.error(f"[스케줄러] description 보완 오류: {e}")


async def _job_enrich_bookings() -> None:
    logger.info("[스케줄러] 예약 링크 보완 시작")
    async with AsyncSessionLocal() as db:
        try:
            result = await enrich_booking_urls(db, limit=100)
            _last_results["enrich_bookings"] = {
                **result,
                "ran_at": datetime.now().isoformat(),
            }
            logger.info(f"[스케줄러] 예약 링크 보완 완료: {result}")
        except Exception as e:
            logger.error(f"[스케줄러] 예약 링크 보완 오류: {e}")


async def _job_collect_regions() -> None:
    """전국 주요 지역 데이트 장소를 순차 수집한다."""
    regions = load_regions()
    logger.info(f"[스케줄러] 지역 수집 시작 — {len(regions)}개 지역")
    region_results = []

    for r in regions:
        name = r["name"]
        try:
            async with AsyncSessionLocal() as db:
                result = await collect_by_region(
                    region=name,
                    latitude=r["latitude"],
                    longitude=r["longitude"],
                    radius_m=r["radius_m"],
                    db=db,
                )
            region_results.append({"region": name, "total": result["total"]})
            logger.info(f"[스케줄러] {name} 수집 완료: {result['total']}개")
        except Exception as e:
            region_results.append({"region": name, "error": str(e)})
            logger.error(f"[스케줄러] {name} 수집 오류: {e}")

    total = sum(r.get("total", 0) for r in region_results)
    _last_results["collect_regions"] = {
        "regions": region_results,
        "total": total,
        "ran_at": datetime.now().isoformat(),
    }
    logger.info(f"[스케줄러] 지역 수집 완료 — 총 {total}개")


# ── 스케줄러 시작/종료 ────────────────────────────────────────

def start_scheduler() -> None:
    cfg = load_schedule()

    scheduler.add_job(
        _job_enrich_descriptions,
        trigger=_make_trigger(cfg["enrich_descriptions"]),
        id="enrich_descriptions",
        name="description 보완 (블로그 크롤링 + GPT)",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _job_enrich_bookings,
        trigger=_make_trigger(cfg["enrich_bookings"]),
        id="enrich_bookings",
        name="예약 링크 보완 (네이버 지도)",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _job_collect_regions,
        trigger=_make_trigger(cfg["collect_regions"]),
        id="collect_regions",
        name="주요 지역 데이트 장소 수집 (주간)",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    load_regions()  # 파일 없으면 기본값으로 초기화
    scheduler.start()
    logger.info(f"[스케줄러] 시작됨 — {cfg}")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[스케줄러] 중지됨")


def get_status() -> dict:
    """현재 스케줄러 상태와 Job 목록을 반환한다."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "last_result": _last_results.get(job.id, {}),
        })
    return {
        "running": scheduler.running,
        "jobs": jobs,
    }

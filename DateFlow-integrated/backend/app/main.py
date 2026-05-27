from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.db.qdrant import ensure_collection
from app.db.session import _engine as engine
from app.models.auth import LocalAuth  # noqa: F401 — 테이블 등록용
from app.models.base import Base
from app.routers.auth_router import router as auth_router
from app.routers.course_router import router as course_router
from app.routers.crawl_router import router as crawl_router
from app.routers.place_router import router as place_router
from app.routers.scheduler_router import router as scheduler_router
from app.routers.user_pref_router import router as user_pref_router
from app.routers.weather_router import router as weather_router
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # local_auth 테이블이 없으면 자동 생성
    async with engine.begin() as conn:
        await conn.run_sync(LocalAuth.__table__.create, checkfirst=True)
    await ensure_collection()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="DateFlow API",
    description="AI 데이트 코스 추천 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(crawl_router)
app.include_router(place_router)
app.include_router(scheduler_router)
app.include_router(weather_router)
app.include_router(user_pref_router)
app.include_router(course_router)

# 프론트엔드 정적 파일 서빙
_DIST = Path(__file__).parent.parent.parent / "frontend/dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(_DIST / "index.html")

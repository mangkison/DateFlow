from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.qdrant import ensure_collection
from app.routers.crawl_router import router as crawl_router
from app.routers.place_router import router as place_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_collection()
    yield


app = FastAPI(
    title="DateFlow API",
    description="AI 데이트 코스 추천 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(crawl_router)
app.include_router(place_router)

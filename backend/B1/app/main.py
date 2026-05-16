from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import user, course, weather
app = FastAPI(
    title="DateFlow API",
    description="AI 기반 데이트 플래닝 서비스",
    version="1.0.0"
)

# CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 연결
app.include_router(user.router, prefix="/user", tags=["사용자 취향"])
app.include_router(course.router, prefix="/course", tags=["코스 생성"])
app.include_router(weather.router, prefix="/weather", tags=["날씨"])

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "db": "connected"
    }
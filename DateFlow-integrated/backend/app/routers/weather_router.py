"""날씨 조회 엔드포인트 (기상청 초단기실황)."""
from fastapi import APIRouter

from app.services.weather import get_weather

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get(
    "",
    summary="위경도 기반 날씨 조회",
    description="위경도를 받아 기상청 초단기실황 API로 현재 날씨를 반환합니다.",
)
async def weather(lat: float, lon: float, region: str = "알 수 없음") -> dict:
    return await get_weather(lat, lon, region)

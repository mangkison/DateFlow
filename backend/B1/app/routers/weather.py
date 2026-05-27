from fastapi import APIRouter
from app.services.weather import get_weather

router = APIRouter()

@router.get("")
async def weather(lat: float, lon: float, region: str = "알 수 없음", target_date: str = None, target_time: str = None):
    result = await get_weather(lat, lon, region, target_date, target_time)
    return result
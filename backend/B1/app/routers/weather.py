from fastapi import APIRouter
from app.services.weather import get_weather

router = APIRouter()

@router.get("/")
async def weather(lat: float, lon: float, region: str = "알 수 없음"):
    result = await get_weather(lat, lon, region)
    return result
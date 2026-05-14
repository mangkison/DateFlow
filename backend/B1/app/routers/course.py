from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserPreference
from app.schemas.course import CourseRequest, CourseResponse, CourseItem, PlaceItem
from app.services.weather import get_weather
import uuid

router = APIRouter()

@router.post("/generate", response_model=CourseResponse)
async def generate_course(req: CourseRequest, db: Session = Depends(get_db)):

    # 1. 사용자 취향 조회
    prefs = db.query(UserPreference).filter(
        UserPreference.user_id == req.user_id
    ).first()

    mood   = prefs.mood   if prefs else "감성적"
    budget = prefs.budget if prefs else req.budget

    # 2. 예산 필터링
    if req.budget < 10000:
        raise HTTPException(status_code=400, detail="예산은 최소 10,000원 이상이어야 합니다.")

    cafe_budget      = int(budget * 0.15)   # 15%
    dinner_budget    = int(budget * 0.50)   # 50%
    bar_budget       = int(budget * 0.35)   # 35%

    # 3. 날씨 조회
    weather = await get_weather(req.lat, req.lon, req.region)
    is_outdoor = weather.get("is_outdoor_ok", True)

    # 4. 날씨 기반 장소 타입 조정
    cafe_type   = "루프탑 카페" if is_outdoor else "실내 감성 카페"
    dinner_type = "야외 레스토랑" if is_outdoor else "실내 레스토랑"

    # 5. 코스 생성 (AI 연동 전 Mock)
    mock_course = CourseItem(
        title=f"{mood} 코스 ({weather['description']})",
        total_price=cafe_budget + dinner_budget + bar_budget,
        places=[
            PlaceItem(
                name=f"{req.region} {cafe_type}",
                category="카페",
                region=req.region,
                time=req.start_time,
                price=cafe_budget,
                is_open=True,
            ),
            PlaceItem(
                name=f"{req.region} {dinner_type}",
                category="식당",
                region=req.region,
                time="18:00",
                price=dinner_budget,
                is_open=True,
            ),
            PlaceItem(
                name=f"{req.region} 와인바",
                category="바",
                region=req.region,
                time="20:00",
                price=bar_budget,
                is_open=True,
            ),
        ]
    )

    return CourseResponse(
        course_id=str(uuid.uuid4()),
        user_id=req.user_id,
        region=req.region,
        courses=[mock_course],
    )

@router.get("/{course_id}")
def get_course(course_id: str):
    return {"course_id": course_id, "message": "코스 조회 기능 구현 예정"}
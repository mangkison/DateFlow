from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserPreference
from app.schemas.course import CourseRequest, CourseResponse, CourseItem, PlaceItem
from app.services.weather import get_weather
import uuid
import httpx

router = APIRouter()

B2_URL = "http://localhost:8001"

async def fetch_places(category: str, area: str) -> list[dict]:
    """B2 API에서 실제 장소 데이터 가져오기 (없으면 실시간 수집)"""
    # 지역명 정리: "해운대공원" → "해운대", "홍대입구" → "홍대"
    clean_area = area.replace("공원", "").replace("입구", "").replace("역", "").strip()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. 먼저 DB에서 조회
            res = await client.get(
                f"{B2_URL}/places",
                params={"category": category, "area": clean_area, "size": 5}
            )
            data = res.json()
            places = data.get("places", [])

            # 2. 없으면 실시간 수집 후 다시 조회
            if not places:
                await client.post(
                    f"{B2_URL}/places/collect",
                    json={"query": f"{clean_area} {category}", "crawl_supplement": False}
                )
                res = await client.get(
                    f"{B2_URL}/places",
                    params={"category": category, "area": clean_area, "size": 5}
                )
                data = res.json()
                places = data.get("places", [])

            return places
    except Exception:
        return []

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

    cafe_budget      = int(budget * 0.15)
    dinner_budget    = int(budget * 0.50)
    bar_budget       = int(budget * 0.35)

    # 3. 날씨 조회
    weather = await get_weather(req.lat, req.lon, req.region)
    is_outdoor = weather.get("is_outdoor_ok", True)

    # 4. B2 API에서 실제 장소 가져오기
    # 4. B2 API에서 실제 장소 가져오기
    cafes = await fetch_places("카페", req.region)
    restaurants = await fetch_places("레스토랑", req.region)
    bars = await fetch_places("바/펍", req.region)
    if not bars:
        bars = await fetch_places("기타", req.region)

    # 5. 장소 선택 (없으면 Mock 폴백)
    cafe_data = cafes[0] if cafes else None
    restaurant_data = restaurants[0] if restaurants else None
    bar_data = bars[0] if bars else None

    def calc_walk_minutes(lat1, lon1, lat2, lon2):
        """두 좌표 간 도보 이동시간 계산 (분)"""
        if not all([lat1, lon1, lat2, lon2]):
            return None
        import math
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        distance = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        # 도보 평균 속도 약 67m/분 (시속 4km)
        return round(distance / 67)

    def make_place(data, fallback_name, category, time, price):
        if data:
            return PlaceItem(
                name=data["name"],
                category=category,
                region=req.region,
                time=time,
                price=price,
                is_open=True,
                latitude=float(data["latitude"]) if data.get("latitude") else None,
                longitude=float(data["longitude"]) if data.get("longitude") else None,
            )
        return PlaceItem(
            name=fallback_name,
            category=category,
            region=req.region,
            time=time,
            price=price,
            is_open=True,
        )

    # 6. 코스 생성
    place_list = [
        make_place(cafe_data, f"{req.region} 카페", "카페", req.start_time, cafe_budget),
        make_place(restaurant_data, f"{req.region} 레스토랑", "식당", "18:00", dinner_budget),
        make_place(bar_data, f"{req.region} 바", "바", "20:00", bar_budget),
    ]

    # 7. 도보 이동시간 계산
    for i in range(len(place_list) - 1):
        place_list[i].walk_minutes_to_next = calc_walk_minutes(
            place_list[i].latitude, place_list[i].longitude,
            place_list[i+1].latitude, place_list[i+1].longitude,
        )

    course = CourseItem(
        title=f"{mood} 코스 ({weather['description']})",
        total_price=cafe_budget + dinner_budget + bar_budget,
        places=place_list,
    )
    

    return CourseResponse(
        course_id=str(uuid.uuid4()),
        user_id=req.user_id,
        region=req.region,
        courses=[course],
    )

@router.get("/{course_id}")
def get_course(course_id: str):
    return {"course_id": course_id, "message": "코스 조회 기능 구현 예정"}
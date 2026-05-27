"""데이트 코스 생성 엔드포인트 (B1 호환 인터페이스).

B2의 Place DB를 직접 조회하여 코스를 생성한다.
장소가 없으면 실시간 카카오 검색으로 수집 후 재조회한다.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.place import Place
from app.models.user import User, UserPreference
from app.schemas.course_schema import CourseItem, CourseRequest, CourseResponse, PlaceItem
from app.services.place_collector import collect_and_save
from app.services.weather import get_weather

router = APIRouter(prefix="/courses", tags=["courses"])


async def _fetch_places(category: str, area: str, db: AsyncSession, size: int = 5) -> list[Place]:
    stmt = (
        select(Place)
        .where(Place.is_active == True)
        .where(Place.category == category)
        .where(
            (Place.road_address.ilike(f"%{area}%")) |
            (Place.address.ilike(f"%{area}%"))
        )
        .limit(size)
    )
    result = await db.execute(stmt)
    places = result.scalars().all()

    if not places:
        await collect_and_save(query=f"{area} {category}", db=db)
        result = await db.execute(stmt)
        places = result.scalars().all()

    return list(places)


@router.post(
    "/generate",
    response_model=CourseResponse,
    summary="데이트 코스 생성",
    description=(
        "사용자 취향과 지역, 예산을 기반으로 데이트 코스를 생성합니다.\n\n"
        "DB에 장소가 없으면 카카오 API로 실시간 수집 후 코스를 구성합니다."
    ),
)
async def generate_course(
    req: CourseRequest,
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    if req.budget < 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="예산은 최소 10,000원 이상이어야 합니다.",
        )

    # 사용자 취향 조회
    mood = "감성적"
    budget = req.budget
    user_result = await db.execute(select(User).where(User.kakao_id == req.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        pref_result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user.id)
        )
        pref = pref_result.scalar_one_or_none()
        if pref and pref.extra:
            mood = pref.extra.get("mood", mood)
            budget = pref.extra.get("budget", budget)

    cafe_budget = int(budget * 0.15)
    dinner_budget = int(budget * 0.50)
    activity_budget = int(budget * 0.35)

    # 날씨 조회
    weather = await get_weather(req.lat, req.lon, req.region)

    # 장소 조회 — DB 저장 카테고리명 사용 (_CATEGORY_MAP 기준: 음식점→레스토랑, 문화시설→문화)
    cafes = await _fetch_places("카페", req.region, db)
    restaurants = await _fetch_places("레스토랑", req.region, db)
    activities = await _fetch_places("문화", req.region, db)

    cafe_name = cafes[0].name if cafes else f"{req.region} 카페"
    restaurant_name = restaurants[0].name if restaurants else f"{req.region} 레스토랑"
    activity_name = activities[0].name if activities else f"{req.region} 문화시설"

    course = CourseItem(
        title=f"{mood} 코스 ({weather['description']})",
        total_price=cafe_budget + dinner_budget + activity_budget,
        places=[
            PlaceItem(
                name=cafe_name,
                category="카페",
                region=req.region,
                time=req.start_time,
                price=cafe_budget,
                is_open=True,
            ),
            PlaceItem(
                name=activity_name,
                category="문화",
                region=req.region,
                time="15:00",
                price=activity_budget,
                is_open=True,
            ),
            PlaceItem(
                name=restaurant_name,
                category="레스토랑",
                region=req.region,
                time="18:00",
                price=dinner_budget,
                is_open=True,
            ),
        ],
    )

    return CourseResponse(
        course_id=str(uuid.uuid4()),
        user_id=req.user_id,
        region=req.region,
        courses=[course],
    )


@router.get(
    "/{course_id}",
    summary="코스 조회",
    description="코스 ID로 저장된 코스를 조회합니다. (향후 DB 저장 연동 예정)",
)
async def get_course(course_id: str) -> dict:
    return {"course_id": course_id, "message": "코스 조회 기능 구현 예정"}

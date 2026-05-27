"""사용자 취향 저장/조회 엔드포인트 (B1 호환 인터페이스).

user_id 문자열을 kakao_id로 매핑하여 B2의 User+UserPreference 모델을 사용.
취향 필드(mood, food_type, budget, avoid, age_group)는 UserPreference.extra에 저장.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User, UserPreference
from app.schemas.user_pref_schema import PersonPref, UserPrefCreate, UserPrefResponse

router = APIRouter(prefix="/prefs", tags=["user-prefs"])


async def _get_or_create_user(user_id: str, db: AsyncSession) -> User:
    # UUID 형식이면 users.id 로 직접 조회 (회원가입한 실제 유저)
    try:
        uid = uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()
        if user:
            return user
    except ValueError:
        pass
    # UUID가 아닌 경우 kakao_id로 조회 (레거시 호환)
    result = await db.execute(select(User).where(User.kakao_id == user_id))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(kakao_id=user_id, nickname=user_id)
    db.add(user)
    await db.flush()
    return user


def _pref_to_response(user_id_str: str, pref: UserPreference) -> UserPrefResponse:
    extra = pref.extra or {}
    p1 = extra.get("person1")
    p2 = extra.get("person2")
    return UserPrefResponse(
        user_id=user_id_str,
        partner_id=extra.get("partner_id"),
        mood=extra.get("mood", ""),
        food_type=extra.get("food_type", []),
        budget=extra.get("budget", 0),
        avoid=extra.get("avoid"),
        age_group=extra.get("age_group"),
        person1=PersonPref(**p1) if p1 else None,
        person2=PersonPref(**p2) if p2 else None,
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.post(
    "",
    response_model=UserPrefResponse,
    status_code=status.HTTP_200_OK,
    summary="취향 저장",
    description="user_id로 사용자를 조회하거나 생성하고 취향을 저장합니다. 기존 취향이 있으면 덮어씁니다.",
)
async def save_prefs(
    body: UserPrefCreate,
    db: AsyncSession = Depends(get_db),
) -> UserPrefResponse:
    user = await _get_or_create_user(body.user_id, db)

    extra_data = {
        "partner_id": body.partner_id,
        "mood": body.mood,
        "food_type": body.food_type,
        "budget": body.budget,
        "avoid": body.avoid,
        "age_group": body.age_group,
        "person1": body.person1.model_dump() if body.person1 else None,
        "person2": body.person2.model_dump() if body.person2 else None,
    }

    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()

    if pref:
        pref.extra = extra_data
        pref.budget_range_max = body.budget
        pref.disliked_categories = [body.avoid] if body.avoid else None
    else:
        pref = UserPreference(
            user_id=user.id,
            budget_range_max=body.budget,
            disliked_categories=[body.avoid] if body.avoid else None,
            extra=extra_data,
        )
        db.add(pref)

    await db.commit()
    await db.refresh(pref)
    return _pref_to_response(body.user_id, pref)


@router.get(
    "/{user_id}",
    response_model=UserPrefResponse,
    summary="취향 조회",
)
async def get_prefs(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> UserPrefResponse:
    # UUID면 users.id로 먼저 조회
    user = None
    try:
        uid = uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()
    except ValueError:
        pass
    if not user:
        result = await db.execute(select(User).where(User.kakao_id == user_id))
        user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="취향 정보가 없습니다.")

    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="취향 정보가 없습니다.")

    return _pref_to_response(user_id, pref)

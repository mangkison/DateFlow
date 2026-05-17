from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserPreference
from app.schemas.user import UserPrefCreate, UserPrefResponse

router = APIRouter()

# 취향 저장
@router.post("/prefs", response_model=UserPrefResponse)
def save_prefs(prefs: UserPrefCreate, db: Session = Depends(get_db)):
    # 기존 취향 있으면 업데이트
    existing = db.query(UserPreference).filter(
        UserPreference.user_id == prefs.user_id
    ).first()

    if existing:
        existing.partner_id = prefs.partner_id
        existing.mood       = prefs.mood
        existing.food_type  = prefs.food_type
        existing.budget     = prefs.budget
        existing.avoid      = prefs.avoid
        existing.age_group  = prefs.age_group
        db.commit()
        db.refresh(existing)
        return existing
    
    # 없으면 새로 저장
    new_prefs = UserPreference(
        user_id    = prefs.user_id,
        partner_id = prefs.partner_id,
        mood       = prefs.mood,
        food_type  = prefs.food_type,
        budget     = prefs.budget,
        avoid      = prefs.avoid,
        age_group  = prefs.age_group,
    )
    db.add(new_prefs)
    db.commit()
    db.refresh(new_prefs)
    return new_prefs

# 취향 조회
@router.get("/prefs/{user_id}", response_model=UserPrefResponse)
def get_prefs(user_id: str, db: Session = Depends(get_db)):
    prefs = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).first()

    if not prefs:
        raise HTTPException(status_code=404, detail="취향 정보가 없습니다.")
    
    return prefs
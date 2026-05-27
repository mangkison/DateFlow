"""사용자 취향 스키마 (B1 호환 인터페이스)."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class PersonPref(BaseModel):
    tags: List[str] = []
    gender: Optional[str] = None  # M / F / N


class UserPrefCreate(BaseModel):
    user_id: str
    partner_id: Optional[str] = None
    mood: str = ""
    food_type: List[str] = []
    budget: int = 0
    avoid: Optional[str] = None
    age_group: Optional[str] = None
    person1: Optional[PersonPref] = None  # 남자친구
    person2: Optional[PersonPref] = None  # 여자친구


class UserPrefResponse(BaseModel):
    user_id: str
    partner_id: Optional[str]
    mood: str
    food_type: List[str]
    budget: int
    avoid: Optional[str]
    age_group: Optional[str]
    person1: Optional[PersonPref] = None
    person2: Optional[PersonPref] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

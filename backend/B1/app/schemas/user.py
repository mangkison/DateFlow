from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# 취향 저장 요청
class UserPrefCreate(BaseModel):
    user_id:    str
    partner_id: Optional[str] = None
    mood:       str
    food_type:  List[str] = []
    budget:     int
    avoid:      Optional[str] = None
    age_group:  Optional[str] = None

# 취향 조회 응답
class UserPrefResponse(BaseModel):
    user_id:    str
    partner_id: Optional[str]
    mood:       str
    food_type:  List[str]
    budget:     int
    avoid:      Optional[str]
    age_group:  Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
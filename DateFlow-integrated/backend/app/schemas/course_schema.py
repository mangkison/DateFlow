"""코스 생성 스키마 (B1 호환 인터페이스)."""
from typing import List, Optional
from pydantic import BaseModel


class CourseRequest(BaseModel):
    user_id: str
    region: str
    lat: float
    lon: float
    start_time: str
    end_time: str
    budget: int
    weather: Optional[str] = None
    natural_input: Optional[str] = None


class PlaceItem(BaseModel):
    name: str
    category: str
    region: str
    time: str
    price: int
    is_open: bool


class CourseItem(BaseModel):
    title: str
    total_price: int
    places: List[PlaceItem]


class CourseResponse(BaseModel):
    course_id: str
    user_id: str
    region: str
    courses: List[CourseItem]

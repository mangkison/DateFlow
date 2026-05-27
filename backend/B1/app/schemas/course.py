from pydantic import BaseModel
from typing import Optional, List

# 코스 생성 요청
class CourseRequest(BaseModel):
    user_id:       str
    region:        str
    lat:           float
    lon:           float
    start_time:    str
    end_time:      str
    budget:        int
    weather:       Optional[str] = None
    natural_input: Optional[str] = None

# 장소 정보
class PlaceItem(BaseModel):
    name:      str
    category:  str
    region:    str
    time:      str
    price:     int
    is_open:   bool
    latitude:  Optional[float] = None
    longitude: Optional[float] = None
    walk_minutes_to_next: Optional[int] = None

# 코스 하나
class CourseItem(BaseModel):
    title:       str
    total_price: int
    places:      List[PlaceItem]

# 코스 생성 응답
class CourseResponse(BaseModel):
    course_id: str
    user_id:   str
    region:    str
    courses:   List[CourseItem]
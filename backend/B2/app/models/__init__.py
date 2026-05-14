# 모든 모델을 여기서 import해야 Alembic autogenerate가 전체 테이블을 감지한다
from app.models.base import Base
from app.models.crawl import CrawlLog, CrawlTarget
from app.models.course import ChatHistory, Course, CoursePlace
from app.models.place import (
    Place,
    PlaceOperatingHour,
    PlaceReport,
    PlaceReview,
    TagMaster,
)
from app.models.reservation import CourseFeedback, Reservation
from app.models.user import (
    Couple,
    CoupleAnniversary,
    User,
    UserPreference,
    VisitedPlace,
)

__all__ = [
    "Base",
    # user
    "User",
    "Couple",
    "CoupleAnniversary",
    "UserPreference",
    "VisitedPlace",
    # place
    "TagMaster",
    "Place",
    "PlaceOperatingHour",
    "PlaceReport",
    "PlaceReview",
    # course
    "Course",
    "CoursePlace",
    "ChatHistory",
    # reservation
    "Reservation",
    "CourseFeedback",
    # crawl
    "CrawlTarget",
    "CrawlLog",
]

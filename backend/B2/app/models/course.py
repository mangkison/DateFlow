import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.place import Place
    from app.models.reservation import CourseFeedback, Reservation
    from app.models.user import Couple, User


class Course(Base, TimestampMixin):
    __tablename__ = "courses"
    __table_args__ = (
        {
            "comment": (
                "AI 추천 데이트 코스 — total_budget 컬럼 없음, "
                "SUM(course_places.budget_allocated)으로 계산"
            )
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # couple_id / user_id 둘 중 하나만 세팅 (커플 vs 개인)
    couple_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("couples.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    course_date: Mapped[date] = mapped_column(nullable=False)
    area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # tag_master.code 값 배열
    theme_tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    # draft / confirmed / completed / cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    couple: Mapped[Optional["Couple"]] = relationship(back_populates="courses")
    user: Mapped[Optional["User"]] = relationship(back_populates=None)
    course_places: Mapped[list["CoursePlace"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CoursePlace.order_index",
    )
    feedback: Mapped[list["CourseFeedback"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="course")


# CREATE INDEX ix_courses_couple_id ON courses(couple_id);
# CREATE INDEX ix_courses_user_id ON courses(user_id);
# CREATE INDEX ix_courses_course_date ON courses(course_date DESC);
# CREATE INDEX ix_courses_status ON courses(status);
# CREATE INDEX ix_courses_theme_tags_gin ON courses USING gin(theme_tags);


class CoursePlace(Base):
    __tablename__ = "course_places"
    __table_args__ = (
        UniqueConstraint("course_id", "order_index", name="uq_course_places_order"),
        {"comment": "코스 내 장소 순서 — is_replaced/replaced_reason으로 자연어 수정 이력 추적"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    place_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # courses.total_budget 삭제 → 이 컬럼들의 SUM으로 대체
    budget_allocated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_minutes: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # AI가 이 장소를 다른 장소로 교체했을 때 True
    is_replaced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # "비가 와서 실내 카페로 변경" 같은 자연어 이유
    replaced_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    course: Mapped["Course"] = relationship(back_populates="course_places")
    place: Mapped[Optional["Place"]] = relationship(back_populates="course_places")
    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="course_place"
    )


# CREATE INDEX ix_course_places_course_id ON course_places(course_id);
# CREATE INDEX ix_course_places_place_id ON course_places(place_id);
# CREATE INDEX ix_course_places_replaced ON course_places(is_replaced) WHERE is_replaced = true;


class ChatHistory(Base):
    __tablename__ = "chat_histories"
    __table_args__ = (
        {
            "comment": (
                "챗봇 대화 이력 — session_id로 하나의 추천 세션 묶음, "
                "metadata에 suggested_places/tokens_used 저장"
            )
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 한 추천 흐름을 묶는 세션 단위
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # user / assistant / system
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # {course_id, suggested_place_ids, tokens_used, model, ...}
    # 'metadata'는 SQLAlchemy 예약어 → Python 속성명만 chat_metadata로 변경, DB 컬럼명은 'metadata' 유지
    chat_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="chat_histories")


# CREATE INDEX ix_chat_histories_user_session ON chat_histories(user_id, session_id);
# CREATE INDEX ix_chat_histories_created_at ON chat_histories(created_at DESC);
# CREATE INDEX ix_chat_histories_metadata_gin ON chat_histories USING gin(metadata);

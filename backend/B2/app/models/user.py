import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    UUID,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.course import ChatHistory, Course
    from app.models.place import Place, PlaceReport, PlaceReview
    from app.models.reservation import CourseFeedback, Reservation


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (
        # 소셜 로그인 ID는 값이 있을 때만 unique 보장 (Partial Index)
        # kakao_id, naver_id 둘 다 NULL 허용이므로 partial unique index 사용
        {"comment": "카카오/네이버 소셜 로그인 사용자 테이블"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kakao_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    naver_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    birth_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # M / F / N

    # Relationships
    preferences: Mapped[Optional["UserPreference"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    user_a_couples: Mapped[list["Couple"]] = relationship(
        foreign_keys="Couple.user_a_id", back_populates="user_a"
    )
    user_b_couples: Mapped[list["Couple"]] = relationship(
        foreign_keys="Couple.user_b_id", back_populates="user_b"
    )
    visited_places: Mapped[list["VisitedPlace"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["PlaceReview"]] = relationship(back_populates="user")
    reports: Mapped[list["PlaceReport"]] = relationship(back_populates="user")
    chat_histories: Mapped[list["ChatHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="user")
    feedbacks: Mapped[list["CourseFeedback"]] = relationship(back_populates="user")


# B-Tree partial unique indexes — DDL 수준에서 직접 지정 (alembic migration에서 처리)
# CREATE UNIQUE INDEX ix_users_kakao_id ON users(kakao_id) WHERE kakao_id IS NOT NULL;
# CREATE UNIQUE INDEX ix_users_naver_id ON users(naver_id) WHERE naver_id IS NOT NULL;
# CREATE INDEX ix_users_email ON users(email);
# CREATE INDEX ix_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NULL;


class Couple(Base, TimestampMixin):
    __tablename__ = "couples"
    __table_args__ = (
        CheckConstraint("user_a_id <> user_b_id", name="ck_couples_different_users"),
        UniqueConstraint("user_a_id", "user_b_id", name="uq_couples_pair"),
        {"comment": "커플 관계 테이블 — user_a_id < user_b_id 정렬 권장 (애플리케이션 레이어)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    anniversary_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active / inactive

    # Relationships
    user_a: Mapped["User"] = relationship(
        foreign_keys=[user_a_id], back_populates="user_a_couples"
    )
    user_b: Mapped["User"] = relationship(
        foreign_keys=[user_b_id], back_populates="user_b_couples"
    )
    anniversaries: Mapped[list["CoupleAnniversary"]] = relationship(
        back_populates="couple", cascade="all, delete-orphan"
    )
    courses: Mapped[list["Course"]] = relationship(back_populates="couple")


# CREATE INDEX ix_couples_user_a ON couples(user_a_id);
# CREATE INDEX ix_couples_user_b ON couples(user_b_id);
# CREATE INDEX ix_couples_status ON couples(status);


class CoupleAnniversary(Base):
    __tablename__ = "couple_anniversaries"
    __table_args__ = (
        {"comment": "커플 기념일 — is_recurring=True 이면 매년 반복"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    couple_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("couples.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    reminder_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    couple: Mapped["Couple"] = relationship(back_populates="anniversaries")


# CREATE INDEX ix_couple_anniversaries_couple_id ON couple_anniversaries(couple_id);
# CREATE INDEX ix_couple_anniversaries_date ON couple_anniversaries(date);


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"
    __table_args__ = (
        {"comment": "사용자 취향 설정 — 1 user : 1 preference"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # tag_master.code 값을 배열로 저장 (GIN 인덱스)
    preferred_atmospheres: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    budget_range_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    budget_range_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_areas: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    disliked_categories: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="preferences")


# CREATE UNIQUE INDEX ix_user_preferences_user_id ON user_preferences(user_id);
# CREATE INDEX ix_user_preferences_atmospheres_gin ON user_preferences USING gin(preferred_atmospheres);


class VisitedPlace(Base):
    __tablename__ = "visited_places"
    __table_args__ = (
        UniqueConstraint("user_id", "place_id", name="uq_visited_places_user_place"),
        {"comment": "사용자 방문 이력 — 재방문 시 visited_at 갱신"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE"), nullable=False
    )
    visited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    personal_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(2, 1), nullable=True
    )  # 1.0 ~ 5.0

    # Relationships
    user: Mapped["User"] = relationship(back_populates="visited_places")
    place: Mapped["Place"] = relationship(back_populates="visitors")


# CREATE INDEX ix_visited_places_user_id ON visited_places(user_id);
# CREATE INDEX ix_visited_places_place_id ON visited_places(place_id);
# CREATE INDEX ix_visited_places_visited_at ON visited_places(visited_at DESC);

import uuid
from datetime import date, datetime, time
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.course import Course, CoursePlace
    from app.models.place import Place
    from app.models.user import User


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"
    __table_args__ = (
        {
            "comment": (
                "예약 정보 — deeplink_url은 특정 예약 건 URL, "
                "places.booking_page_url(장소 고정)과 다름"
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
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="RESTRICT"),
        nullable=False,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_place_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_places.id", ondelete="SET NULL"),
        nullable=True,
    )
    reservation_date: Mapped[date] = mapped_column(nullable=False)
    reservation_time: Mapped[Optional[time]] = mapped_column(nullable=True)
    party_size: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    # pending / confirmed / cancelled / completed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # 외부 예약 시스템이 발급하는 이 예약 건 고유 딥링크 URL
    deeplink_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    external_reservation_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="reservations")
    place: Mapped["Place"] = relationship(back_populates="reservations")
    course: Mapped[Optional["Course"]] = relationship(back_populates="reservations")
    course_place: Mapped[Optional["CoursePlace"]] = relationship(
        back_populates="reservations"
    )


# CREATE INDEX ix_reservations_user_id ON reservations(user_id);
# CREATE INDEX ix_reservations_place_id ON reservations(place_id);
# CREATE INDEX ix_reservations_course_id ON reservations(course_id);
# CREATE INDEX ix_reservations_status ON reservations(status);
# CREATE INDEX ix_reservations_date ON reservations(reservation_date DESC);
# Partial: 활성 예약만 빠른 조회
# CREATE INDEX ix_reservations_active ON reservations(user_id, reservation_date)
#   WHERE status IN ('pending', 'confirmed');


class CourseFeedback(Base):
    __tablename__ = "course_feedback"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_course_feedback_course_user"),
        {"comment": "코스 피드백 — place_ratings는 {place_uuid: rating} JSONB"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 ~ 5
    # {"place_uuid_str": rating_int}
    place_ratings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    would_revisit: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    course: Mapped["Course"] = relationship(back_populates="feedback")
    user: Mapped["User"] = relationship(back_populates="feedbacks")


# CREATE INDEX ix_course_feedback_course_id ON course_feedback(course_id);
# CREATE INDEX ix_course_feedback_user_id ON course_feedback(user_id);
# CREATE INDEX ix_course_feedback_rating ON course_feedback(overall_rating);

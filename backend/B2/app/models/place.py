import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    UUID,
    Boolean,
    Computed,
    DateTime,
    DDL,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.course import CoursePlace
    from app.models.crawl import CrawlTarget
    from app.models.reservation import Reservation
    from app.models.user import User, VisitedPlace


class TagMaster(Base):
    __tablename__ = "tag_master"
    __table_args__ = (
        {"comment": "atmosphere_tags 표준 코드 관리 — places.atmosphere_tags는 이 테이블의 code 값 참조"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # atmosphere / theme / cuisine / activity 등
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# CREATE UNIQUE INDEX ix_tag_master_code ON tag_master(code);
# CREATE INDEX ix_tag_master_category ON tag_master(category);
# CREATE INDEX ix_tag_master_active ON tag_master(is_active) WHERE is_active = true;


class Place(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "places"
    __table_args__ = (
        {"comment": "장소 마스터 — trust_score는 Computed Column, review_count는 트리거 관리"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="크롤링으로 수집한 장소 소개 요약 — Qdrant 임베딩 원본"
    )
    # Qdrant place_summaries 컬렉션 포인트 ID (벡터 업데이트 시 참조)
    qdrant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="Qdrant 벡터 포인트 ID"
    )
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    road_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    # PostGIS POINT(longitude latitude) SRID 4326
    # spatial_index=False → __table_args__ GIST 인덱스로 직접 관리
    location: Mapped[Optional[Any]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=True,
    )
    # 카페 / 레스토랑 / 전시 / 공연 / 액티비티 / 쇼핑 등
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sub_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # 장소 고유 예약 페이지 URL (≠ reservations.deeplink_url)
    booking_page_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 외부 플랫폼 평점 (0.0 ~ 5.0)
    naver_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1), nullable=True)
    kakao_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1), nullable=True)
    google_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1), nullable=True)

    # Generated Column: NULL이 아닌 평점의 평균값 자동 계산
    trust_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        Computed(
            """
            ROUND(
                (COALESCE(naver_rating, 0) + COALESCE(kakao_rating, 0) + COALESCE(google_rating, 0))
                / NULLIF(
                    (CASE WHEN naver_rating IS NOT NULL THEN 1 ELSE 0 END
                     + CASE WHEN kakao_rating IS NOT NULL THEN 1 ELSE 0 END
                     + CASE WHEN google_rating IS NOT NULL THEN 1 ELSE 0 END)::NUMERIC,
                    0
                ),
                2
            )
            """,
            persisted=True,
        ),
        nullable=True,
        comment="naver/kakao/google 평점 평균 — Generated Column (읽기 전용)",
    )

    # place_reviews INSERT/DELETE 트리거로 자동 업데이트
    review_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="place_reviews 행 수 — 트리거(trg_place_review_count)가 유지",
    )

    # tag_master.code 값 배열 (GIN 인덱스)
    atmosphere_tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    operating_hours: Mapped[list["PlaceOperatingHour"]] = relationship(
        back_populates="place", cascade="all, delete-orphan"
    )
    reports: Mapped[list["PlaceReport"]] = relationship(
        back_populates="place", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["PlaceReview"]] = relationship(
        back_populates="place", cascade="all, delete-orphan"
    )
    visitors: Mapped[list["VisitedPlace"]] = relationship(back_populates="place")
    course_places: Mapped[list["CoursePlace"]] = relationship(back_populates="place")
    crawl_targets: Mapped[list["CrawlTarget"]] = relationship(back_populates="place")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="place")


# CREATE INDEX ix_places_name ON places(name);
# CREATE INDEX ix_places_category ON places(category);
# CREATE INDEX ix_places_active ON places(is_active) WHERE deleted_at IS NULL;
# CREATE INDEX ix_places_trust_score ON places(trust_score DESC) WHERE deleted_at IS NULL;
# CREATE INDEX ix_places_location_gist ON places USING gist(location);
# CREATE INDEX ix_places_atmosphere_tags_gin ON places USING gin(atmosphere_tags);


class PlaceOperatingHour(Base):
    __tablename__ = "place_operating_hours"
    __table_args__ = (
        UniqueConstraint("place_id", "day_of_week", name="uq_operating_hours_place_day"),
        {"comment": "장소 운영시간 — day_of_week: 0=월 ... 6=일"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=월 ~ 6=일
    open_time: Mapped[Optional[time]] = mapped_column(nullable=True)
    close_time: Mapped[Optional[time]] = mapped_column(nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    break_start: Mapped[Optional[time]] = mapped_column(nullable=True)
    break_end: Mapped[Optional[time]] = mapped_column(nullable=True)

    # Relationships
    place: Mapped["Place"] = relationship(back_populates="operating_hours")


# CREATE INDEX ix_operating_hours_place_id ON place_operating_hours(place_id);


class PlaceReport(Base):
    __tablename__ = "place_reports"
    __table_args__ = (
        {"comment": "장소 신고 — status: pending / resolved / dismissed"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    place: Mapped["Place"] = relationship(back_populates="reports")
    user: Mapped["User"] = relationship(back_populates="reports")


# CREATE INDEX ix_place_reports_place_id ON place_reports(place_id);
# CREATE INDEX ix_place_reports_status ON place_reports(status) WHERE status = 'pending';


class PlaceReview(Base, TimestampMixin):
    __tablename__ = "place_reviews"
    __table_args__ = (
        UniqueConstraint("place_id", "user_id", name="uq_place_reviews_place_user"),
        {"comment": "장소 리뷰 — INSERT/DELETE 시 트리거로 places.review_count 자동 갱신"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 ~ 5
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # [{url: str, caption: str}]
    images: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    place: Mapped["Place"] = relationship(back_populates="reviews")
    user: Mapped["User"] = relationship(back_populates="reviews")


# CREATE INDEX ix_place_reviews_place_id ON place_reviews(place_id);
# CREATE INDEX ix_place_reviews_created_at ON place_reviews(created_at DESC);
# CREATE INDEX ix_place_reviews_active ON place_reviews(place_id) WHERE is_deleted = false;


# ── review_count 자동 갱신 트리거 (place_reviews 테이블 생성 후 등록) ─────────────
_fn_update_review_count = DDL("""
CREATE OR REPLACE FUNCTION fn_update_place_review_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NOT NEW.is_deleted THEN
            UPDATE places SET review_count = review_count + 1 WHERE id = NEW.place_id;
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        IF NOT OLD.is_deleted THEN
            UPDATE places SET review_count = GREATEST(review_count - 1, 0) WHERE id = OLD.place_id;
        END IF;

    ELSIF TG_OP = 'UPDATE' THEN
        -- place_id 변경 (비정상적이지만 방어적 처리)
        IF OLD.place_id IS DISTINCT FROM NEW.place_id THEN
            IF NOT OLD.is_deleted THEN
                UPDATE places SET review_count = GREATEST(review_count - 1, 0) WHERE id = OLD.place_id;
            END IF;
            IF NOT NEW.is_deleted THEN
                UPDATE places SET review_count = review_count + 1 WHERE id = NEW.place_id;
            END IF;

        -- is_deleted 토글: 소프트 삭제(false→true) 또는 복구(true→false)
        ELSIF OLD.is_deleted IS DISTINCT FROM NEW.is_deleted THEN
            IF NEW.is_deleted THEN
                UPDATE places SET review_count = GREATEST(review_count - 1, 0) WHERE id = NEW.place_id;
            ELSE
                UPDATE places SET review_count = review_count + 1 WHERE id = NEW.place_id;
            END IF;
        END IF;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
""")

_trg_review_count = DDL("""
CREATE TRIGGER trg_place_review_count
AFTER INSERT OR DELETE OR UPDATE OF place_id, is_deleted ON place_reviews
FOR EACH ROW EXECUTE FUNCTION fn_update_place_review_count();
""")

event.listen(
    PlaceReview.__table__,
    "after_create",
    _fn_update_review_count.execute_if(dialect="postgresql"),
)
event.listen(
    PlaceReview.__table__,
    "after_create",
    _trg_review_count.execute_if(dialect="postgresql"),
)

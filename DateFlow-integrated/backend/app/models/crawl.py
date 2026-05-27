import uuid
from datetime import datetime
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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.place import Place


class CrawlTarget(Base, TimestampMixin):
    __tablename__ = "crawl_targets"
    __table_args__ = (
        {"comment": "크롤링 대상 관리 — place_id가 NULL이면 신규 장소 수집용"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    place_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    # naver / kakao / google
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    # place_info / reviews / images / operating_hours
    crawl_type: Mapped[str] = mapped_column(String(50), nullable=False)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # schedule_cron에서 계산된 다음 수집 예정 시각 — 스케줄러가 이 컬럼만 참조
    next_crawl_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 연속 실패 횟수 — 3 초과 시 is_active=False 자동화
    fail_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    # HTTP 조건부 요청용 캐시 헤더 저장
    etag: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_modified: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="HTTP Last-Modified 헤더 — If-Modified-Since 조건부 요청용"
    )

    # Relationships
    place: Mapped[Optional["Place"]] = relationship(back_populates="crawl_targets")
    crawl_logs: Mapped[list["CrawlLog"]] = relationship(
        back_populates="crawl_target", cascade="all, delete-orphan"
    )


# CREATE INDEX ix_crawl_targets_place_id ON crawl_targets(place_id);
# CREATE INDEX ix_crawl_targets_source ON crawl_targets(source);
# CREATE INDEX ix_crawl_targets_active ON crawl_targets(is_active) WHERE is_active = true;
# CREATE INDEX ix_crawl_targets_last_crawled ON crawl_targets(last_crawled_at ASC NULLS FIRST);


class CrawlLog(Base):
    __tablename__ = "crawl_logs"
    __table_args__ = (
        {
            "comment": (
                "크롤링 실행 로그 — raw_data(원본 JSONB) → parsed_data(파싱 결과 JSONB) 2단계 구조. "
                "파싱 실패해도 raw_data로 재처리 가능"
            )
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    crawl_target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # running / success / failed / partial
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    # 1단계: 크롤러가 수집한 원본 응답 그대로 저장
    raw_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="크롤링 원본 데이터 — 파싱 실패 시 재처리 기준",
    )
    # 2단계: raw_data 파싱 후 정규화된 데이터
    parsed_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="raw_data 파싱 결과 — places 테이블 upsert에 사용",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    records_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    http_status_code: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 재시도인 경우 원본 실패 로그 참조
    retry_of: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_logs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    crawl_target: Mapped["CrawlTarget"] = relationship(back_populates="crawl_logs")
    original_log: Mapped[Optional["CrawlLog"]] = relationship(
        "CrawlLog", foreign_keys=[retry_of], remote_side="CrawlLog.id"
    )


# CREATE INDEX ix_crawl_logs_target_id ON crawl_logs(crawl_target_id);
# CREATE INDEX ix_crawl_logs_started_at ON crawl_logs(started_at DESC);
# CREATE INDEX ix_crawl_logs_status ON crawl_logs(status);
# Partial: 실패 로그만 빠른 조회
# CREATE INDEX ix_crawl_logs_failed ON crawl_logs(crawl_target_id, started_at DESC)
#   WHERE status IN ('failed', 'partial');
# GIN: parsed_data / raw_data 내부 JSON 검색
# CREATE INDEX ix_crawl_logs_raw_data_gin ON crawl_logs USING gin(raw_data);
# CREATE INDEX ix_crawl_logs_parsed_data_gin ON crawl_logs USING gin(parsed_data);

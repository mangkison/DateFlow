import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, HttpUrl, field_validator


class FreshnessLevel(str, Enum):
    recent = "recent"        # 3개월 이내
    moderate = "moderate"    # 3~6개월
    old = "old"              # 6개월~1년
    very_old = "very_old"    # 1년 초과
    unknown = "unknown"      # 날짜 불명


class PolicyStatus(str, Enum):
    allowed = "allowed"
    blocked = "blocked"
    requires_api = "requires_api"
    rate_limited = "rate_limited"


class CrawlRequest(BaseModel):
    url: HttpUrl
    max_length: int = 500

    @field_validator("max_length")
    @classmethod
    def clamp_max_length(cls, v: int) -> int:
        return max(100, min(v, 2000))


class FreshnessInfo(BaseModel):
    level: FreshnessLevel
    published_at: Optional[datetime] = None
    score: float  # 0.0 ~ 1.0 (높을수록 최신)


class SourcePolicyResult(BaseModel):
    url: str
    status: PolicyStatus
    reason: str
    crawl_delay_seconds: float = 1.0
    recommended_api: Optional[str] = None


class CrawlResult(BaseModel):
    url: str
    title: Optional[str] = None
    summary: str
    freshness: FreshnessInfo
    fetched_at: datetime
    content_length_bytes: int


class AnalyzeUrlResult(BaseModel):
    url: str
    policy: SourcePolicyResult
    freshness: Optional[FreshnessInfo] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    fetched_at: Optional[datetime] = None
    error: Optional[str] = None


class RunTargetRequest(BaseModel):
    target_id: uuid.UUID


class CrawlLogResult(BaseModel):
    id: uuid.UUID
    crawl_target_id: uuid.UUID
    status: str
    http_status_code: Optional[int] = None
    duration_ms: Optional[int] = None
    records_count: int
    parsed_data: Optional[Any] = None
    error_message: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

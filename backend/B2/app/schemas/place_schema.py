import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PlaceCollectRequest(BaseModel):
    query: str = Field(..., description="검색어 (예: '홍대 카페', '강남 레스토랑')")
    crawl_supplement: bool = Field(
        True, description="웹 크롤링으로 운영시간·설명 보조 수집 여부"
    )


class WebCollectRequest(BaseModel):
    query: str = Field(..., description="검색어 (예: '용인 모현읍 맛집')")
    blog_display: int = Field(5, ge=1, le=10, description="블로그 검색 결과 수")
    category: str = Field("기타", description="수집 장소에 적용할 기본 카테고리")


class PlaceResult(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    road_address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    website_url: Optional[str] = None
    naver_rating: Optional[Decimal] = None
    kakao_rating: Optional[Decimal] = None
    trust_score: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class PlaceCollectResponse(BaseModel):
    query: str
    total: int
    places: list[PlaceResult]


class PlaceListResponse(BaseModel):
    total: int
    page: int
    size: int
    places: list[PlaceResult]


class PlaceEnrichResponse(BaseModel):
    total: int
    enriched: int
    skipped: int

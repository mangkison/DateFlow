from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.crawl_schema import (
    AnalyzeUrlResult,
    CrawlLogResult,
    CrawlRequest,
    CrawlResult,
    PolicyStatus,
    RunTargetRequest,
    SourcePolicyResult,
)
from app.services.crawl_processor import run_crawl_target
from app.services.safe_crawler import safe_fetch
from app.services.source_policy import check_source_policy

router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post(
    "/check-source",
    response_model=SourcePolicyResult,
    summary="URL 수집 가능 여부 확인",
    description=(
        "robots.txt 및 내부 정책을 확인하여 수집 허용 여부를 반환합니다. "
        "실제 페이지 요청은 하지 않습니다."
    ),
)
async def check_source(req: CrawlRequest) -> SourcePolicyResult:
    return await check_source_policy(str(req.url))


@router.post(
    "/fetch",
    response_model=CrawlResult,
    summary="안전한 웹 페이지 수집",
    description=(
        "정책 검사 → rate limiting → 본문 추출 → 개인정보 제거 → 신선도 평가 순으로 처리합니다. "
        "수집이 금지된 URL은 403을 반환합니다."
    ),
)
async def fetch_page(req: CrawlRequest) -> CrawlResult:
    try:
        return await safe_fetch(str(req.url), max_length=req.max_length)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"원격 페이지 수집 실패: {exc}",
        )


@router.post(
    "/analyze-url",
    response_model=AnalyzeUrlResult,
    summary="URL 통합 분석 (정책 + 수집 + 신선도)",
    description=(
        "check-source와 fetch를 한 번에 실행합니다. "
        "정책 위반 시에도 200을 반환하되 policy.status에 결과를 담습니다."
    ),
)
async def analyze_url(req: CrawlRequest) -> AnalyzeUrlResult:
    url_str = str(req.url)
    policy = await check_source_policy(url_str)

    if policy.status != PolicyStatus.allowed:
        return AnalyzeUrlResult(url=url_str, policy=policy)

    try:
        result = await safe_fetch(url_str, max_length=req.max_length)
        return AnalyzeUrlResult(
            url=url_str,
            policy=policy,
            freshness=result.freshness,
            title=result.title,
            summary=result.summary,
            fetched_at=result.fetched_at,
        )
    except Exception as exc:
        return AnalyzeUrlResult(url=url_str, policy=policy, error=str(exc))


@router.post(
    "/run-target",
    response_model=CrawlLogResult,
    summary="CrawlTarget 실행 — 수집·저장 파이프라인",
    description=(
        "지정한 CrawlTarget을 즉시 실행합니다. "
        "수집 → PostgreSQL(CrawlLog+Place) → Qdrant 벡터 저장 순서로 처리하고 "
        "CrawlLog를 반환합니다."
    ),
)
async def run_target(
    req: RunTargetRequest,
    db: AsyncSession = Depends(get_db),
) -> CrawlLogResult:
    try:
        log = await run_crawl_target(req.target_id, db)
        return CrawlLogResult.model_validate(log)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파이프라인 실행 오류: {exc}",
        )

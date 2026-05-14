"""
안전한 비동기 HTTP 수집기.
- 도메인별 요청 간격 강제 (rate limiting)
- 응답 크기 500 KB 제한
- robots.txt 정책 준수 (source_policy.py 위임)
"""
import asyncio
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from app.schemas.crawl_schema import CrawlResult, PolicyStatus
from app.services.content_cleaner import clean_html
from app.services.freshness_checker import check_freshness
from app.services.source_policy import check_source_policy

MAX_CONTENT_BYTES = 500 * 1024  # 500 KB
DEFAULT_TIMEOUT = 10.0

_USER_AGENT = (
    "DateFlowBot/1.0 (capstone academic project; "
    "contact: hsg329@hufs.ac.kr; respectful crawling)"
)

# 도메인별 마지막 요청 시각
_last_request: dict[str, float] = {}
_rate_lock = asyncio.Lock()


async def _wait_rate_limit(domain: str, delay: float) -> None:
    async with _rate_lock:
        last = _last_request.get(domain, 0.0)
        elapsed = time.monotonic() - last
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        _last_request[domain] = time.monotonic()


async def safe_fetch(url: str, max_length: int = 500) -> CrawlResult:
    """
    URL을 안전하게 가져와 CrawlResult를 반환한다.
    정책 위반 시 ValueError를 발생시킨다.
    """
    policy = await check_source_policy(url)
    if policy.status != PolicyStatus.allowed:
        raise ValueError(f"수집 불가: {policy.reason}")

    domain = urlparse(url).netloc.lower()
    await _wait_rate_limit(domain, policy.crawl_delay_seconds)

    headers = {"User-Agent": _USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"}

    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers=headers,
    ) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise ValueError(f"지원하지 않는 Content-Type: {content_type}")

            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes(chunk_size=8192):
                total += len(chunk)
                if total > MAX_CONTENT_BYTES:
                    break
                chunks.append(chunk)

    raw_html = b"".join(chunks).decode("utf-8", errors="replace")
    summary, title = clean_html(raw_html, max_length=max_length)
    freshness = check_freshness(raw_html)

    return CrawlResult(
        url=url,
        title=title,
        summary=summary,
        freshness=freshness,
        fetched_at=datetime.now(tz=timezone.utc),
        content_length_bytes=total,
    )

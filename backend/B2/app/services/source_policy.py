"""
robots.txt 준수 + 도메인 정책 체크.
실제 HTTP 요청 전에 반드시 호출해야 한다.
"""
import asyncio
from functools import lru_cache
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.schemas.crawl_schema import PolicyStatus, SourcePolicyResult

# 크롤링 대신 공식 API 사용을 권장하는 도메인
RECOMMENDED_APIS: dict[str, str] = {
    "instagram.com": "Instagram Graph API",
    "twitter.com": "Twitter API v2",
    "x.com": "Twitter API v2",
    "facebook.com": "Facebook Graph API",
    "naver.com": "Naver Open API (검색·지역)",
    "map.naver.com": "Naver Maps API",
    "kakao.com": "Kakao Local API",
    "map.kakao.com": "Kakao Maps API",
    "place.map.kakao.com": "Kakao Local API",
    "youtube.com": "YouTube Data API v3",
    "tripadvisor.com": "Tripadvisor Content API",
}

# 크롤링 자체가 차단된 도메인 (ToS 위반 또는 법적 리스크)
BLOCKED_DOMAINS: dict[str, str] = {
    "booking.com": "ToS 금지 — 공식 파트너 API 사용",
    "airbnb.com": "ToS 금지",
    "coupang.com": "ToS 금지",
    "baemin.com": "ToS 금지",
    "yogiyo.com": "ToS 금지",
}

_robots_cache: dict[str, RobotFileParser] = {}
_cache_lock = asyncio.Lock()


def _extract_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def _match_domain(domain: str, domain_dict: dict[str, str]) -> str | None:
    """domain이 dict 키의 suffix이면 해당 키를 반환."""
    if domain in domain_dict:
        return domain
    for key in domain_dict:
        if domain.endswith("." + key):
            return key
    return None


async def _fetch_robots(base_url: str) -> RobotFileParser:
    async with _cache_lock:
        if base_url in _robots_cache:
            return _robots_cache[base_url]

        rp = RobotFileParser()
        robots_url = f"{base_url}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(robots_url, follow_redirects=True)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp.allow_all = True
        except Exception:
            rp.allow_all = True

        _robots_cache[base_url] = rp
        return rp


async def check_source_policy(url: str) -> SourcePolicyResult:
    domain = _extract_domain(url)

    # 1. 완전 차단 도메인 (서브도메인 포함)
    blocked_key = _match_domain(domain, BLOCKED_DOMAINS)
    if blocked_key:
        return SourcePolicyResult(
            url=url,
            status=PolicyStatus.blocked,
            reason=BLOCKED_DOMAINS[blocked_key],
        )

    # 2. 공식 API 권장 도메인 (정확히 일치하는 경우만)
    if domain in RECOMMENDED_APIS:
        return SourcePolicyResult(
            url=url,
            status=PolicyStatus.requires_api,
            reason=f"{domain}은 공식 API 사용을 권장합니다.",
            recommended_api=RECOMMENDED_APIS[domain],
        )

    # 3. robots.txt 확인
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    rp = await _fetch_robots(base_url)

    if not rp.can_fetch("*", url):
        return SourcePolicyResult(
            url=url,
            status=PolicyStatus.blocked,
            reason="robots.txt에 의해 수집이 금지된 경로입니다.",
        )

    crawl_delay = rp.crawl_delay("*") or 1.0

    return SourcePolicyResult(
        url=url,
        status=PolicyStatus.allowed,
        reason="수집 허용",
        crawl_delay_seconds=float(crawl_delay),
    )

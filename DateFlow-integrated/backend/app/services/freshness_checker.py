"""
HTML 문서에서 작성일을 추출하고 신선도 점수를 계산한다.
"""
import re
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup

from app.schemas.crawl_schema import FreshnessInfo, FreshnessLevel

# ISO 8601 / RFC 2822 날짜 후보 패턴
_ISO_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?)"
)

# 한국어 날짜 표기 (2024년 03월 15일, 2024.03.15 등)
_KO_DATE_PATTERN = re.compile(r"(\d{4})[년.\-](\d{1,2})[월.\-](\d{1,2})일?")


def _extract_date_candidates(html: str) -> list[datetime]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[datetime] = []

    # 1. <meta> 태그: article:published_time, og:updated_time, datePublished
    for meta in soup.find_all("meta"):
        prop = meta.get("property", "") or meta.get("name", "") or meta.get("itemprop", "")
        if any(k in prop.lower() for k in ("published", "modified", "date", "updated")):
            content = meta.get("content", "")
            dt = _parse_iso(content)
            if dt:
                candidates.append(dt)

    # 2. <time datetime="...">
    for time_tag in soup.find_all("time"):
        dt_str = time_tag.get("datetime", "") or time_tag.get_text(strip=True)
        dt = _parse_iso(dt_str)
        if dt:
            candidates.append(dt)

    # 3. JSON-LD: datePublished
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or ""
        for m in _ISO_PATTERN.finditer(text):
            dt = _parse_iso(m.group(1))
            if dt:
                candidates.append(dt)

    # 4. 본문 텍스트에서 한국어 날짜 패턴
    body_text = soup.get_text(" ")
    for m in _KO_DATE_PATTERN.finditer(body_text):
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            candidates.append(dt)
        except ValueError:
            pass

    return candidates


def _parse_iso(s: str) -> Optional[datetime]:
    s = s.strip()
    if not s:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M%z",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s[:len(fmt) + 5], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

    m = _ISO_PATTERN.match(s)
    if m:
        return _parse_iso(m.group(1))
    return None


def _freshness_score(age_days: float) -> tuple[FreshnessLevel, float]:
    if age_days <= 90:
        return FreshnessLevel.recent, 1.0
    if age_days <= 180:
        return FreshnessLevel.moderate, 0.7
    if age_days <= 365:
        return FreshnessLevel.old, 0.4
    return FreshnessLevel.very_old, 0.1


def check_freshness(html: str) -> FreshnessInfo:
    candidates = _extract_date_candidates(html)
    if not candidates:
        return FreshnessInfo(level=FreshnessLevel.unknown, score=0.5)

    # 가장 최근 날짜를 대표 발행일로 사용
    now = datetime.now(tz=timezone.utc)
    published_at = max(candidates)

    # 미래 날짜는 무시
    if published_at > now:
        return FreshnessInfo(level=FreshnessLevel.unknown, score=0.5)

    age_days = (now - published_at).days
    level, score = _freshness_score(age_days)
    return FreshnessInfo(level=level, published_at=published_at, score=score)

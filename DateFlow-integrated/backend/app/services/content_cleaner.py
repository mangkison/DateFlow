"""
HTML → 정제된 텍스트 변환.
개인정보(이메일·전화번호) 및 광고성 문구 제거 후 요약 길이로 잘라낸다.
"""
import re
from typing import Optional

from bs4 import BeautifulSoup, Comment

MAX_SUMMARY_LENGTH = 500

# 제거할 광고·불필요 키워드 패턴 (전체 문장 단위)
_AD_PATTERNS = re.compile(
    r"(광고|협찬|sponsored|advertisement|본 포스팅은.{0,30}제공|"
    r"이 포스트는.{0,30}지원|파트너스 활동|쿠팡 파트너스)",
    re.IGNORECASE,
)

_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# 한국 전화번호 (02-XXXX-XXXX, 010-XXXX-XXXX, 0XX-XXX-XXXX 등)
_PHONE_PATTERN = re.compile(
    r"\b0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}\b"
)

_REMOVE_TAGS = {
    "script", "style", "nav", "header", "footer",
    "aside", "form", "button", "iframe", "noscript",
}


def _strip_html(html: str) -> tuple[str, Optional[str]]:
    """HTML → (본문 텍스트, 제목) 반환."""
    soup = BeautifulSoup(html, "html.parser")

    # HTML 주석 제거
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # 불필요 태그 제거
    for tag in soup.find_all(_REMOVE_TAGS):
        tag.decompose()

    title: Optional[str] = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # og:title 우선
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    # 본문 후보: article > main > body
    body = (
        soup.find("article")
        or soup.find("main")
        or soup.find("body")
        or soup
    )

    text = body.get_text(separator="\n", strip=True)
    return text, title


def _remove_pii(text: str) -> str:
    text = _EMAIL_PATTERN.sub("[이메일 제거]", text)
    text = _PHONE_PATTERN.sub("[전화번호 제거]", text)
    return text


def _remove_ads(text: str) -> str:
    lines = text.splitlines()
    cleaned = [ln for ln in lines if not _AD_PATTERNS.search(ln)]
    return " ".join(cleaned)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s{2,}", " ", text).strip()


def clean_html(html: str, max_length: int = MAX_SUMMARY_LENGTH) -> tuple[str, Optional[str]]:
    """
    Returns:
        (summary, title) — summary는 max_length자로 잘린 정제 텍스트
    """
    text, title = _strip_html(html)
    text = _remove_pii(text)
    text = _remove_ads(text)
    text = _normalize_whitespace(text)
    summary = text[:max_length] + ("..." if len(text) > max_length else "")
    return summary, title

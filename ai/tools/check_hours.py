"""카카오맵 페이지를 Playwright로 크롤링해서 영업시간을 확인하는 툴.

설계:
- 메모리 캐시 (TTL 30분) — 같은 장소 중복 방문 방지
- 카카오 Local API로 place_url 조회 → Playwright로 페이지 로딩 → 영업시간 파싱
"""

import os
import re
import time
from typing import Optional

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

from tools.logger import log_tool

load_dotenv()

# 메모리 캐시: {place_name: (result_text, timestamp)}
_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 30 * 60  # 30분

# 카카오맵 영업시간 셀렉터 후보 (페이지 구조 변경 대응)
KAKAO_HOURS_SELECTORS = [
    ".openhour_wrap",
    ".openhour_list",
    ".OpenHour",
    "[class*='OpenHour']",
    "[class*='openhour']",
    "[class*='operating']",
    ".location_detail",
]


def _get_kakao_url(place_name: str) -> Optional[str]:
    """카카오 Local API로 장소 검색 → place_url 반환."""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_KEY')}"}
    params = {"query": place_name, "size": 1}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        items = res.json().get("documents", [])
        if not items:
            return None
        return items[0].get("place_url")
    except Exception:
        return None


DAY_HOURS_PATTERN = re.compile(
    r"([월화수목금토일])\(([0-9/]+)\)\s*([0-9:]+|영업종료|휴무)\s*(?:~\s*([0-9:]+|영업종료|휴무))?"
)

EXPAND_TRIGGERS = [
    "text=영업정보 전체보기",
    "text=펼치기",
    "[aria-label*='펼치기']",
    "[aria-expanded='false']",
    "[class*='unfold']",
    "[class*='Unfold']",
]


def _try_expand(page) -> None:
    """영업시간 섹션의 펼치기 버튼을 시도해본다 (실패해도 무시)."""
    for selector in EXPAND_TRIGGERS:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=500):
                locator.click(timeout=1000)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def _scrape_hours(place_url: str) -> str:
    """Playwright로 카카오맵 페이지에서 영업시간 추출."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(place_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            _try_expand(page)

            body_text = page.locator("body").inner_text()

            # 1차 시도: 요일별 시간 패턴 추출 (가장 정확)
            matches = DAY_HOURS_PATTERN.findall(body_text)
            if matches:
                lines = []
                for day, date, open_t, close_t in matches:
                    if close_t:
                        lines.append(f"{day}({date}) {open_t} ~ {close_t}")
                    else:
                        lines.append(f"{day}({date}) {open_t}")
                # 영업 상태 헤더 함께 잡기
                status_match = re.search(r"영업\s*[중마감](?:[^\n]{0,30})", body_text)
                status = status_match.group(0).strip() if status_match else ""
                header = f"[{status}]\n" if status else ""
                return header + "\n".join(lines)

            # 2차 시도: 기존 셀렉터들
            for selector in KAKAO_HOURS_SELECTORS:
                try:
                    el = page.query_selector(selector)
                    if el:
                        text = el.inner_text().strip()
                        if text and ("영업" in text or ":" in text):
                            return text
                except Exception:
                    continue

            # 3차 폴백: "영업시간" 키워드 근처 텍스트
            match = re.search(r"영업시간[^\n]{0,200}", body_text)
            if match:
                return match.group(0).strip()

            return "영업시간 정보를 페이지에서 찾을 수 없음"
        finally:
            browser.close()


@tool
@log_tool
def check_hours(place_name: str, visit_date: str = "") -> str:
    """카카오맵에서 장소의 실제 영업시간을 확인합니다.

    Args:
        place_name: 확인할 장소 이름 (예: "성수 갤러리 카페")
        visit_date: 방문 예정 날짜나 요일 (선택, 예: "2025-05-23 토요일")

    Returns:
        영업시간 텍스트 + 카카오맵 링크. 같은 장소를 30분 안에 다시 조회하면 캐시 사용.
    """
    cache_key = place_name
    now = time.time()
    cached = _cache.get(cache_key)
    if cached and (now - cached[1]) < CACHE_TTL:
        return f"[캐시] {cached[0]}"

    place_url = _get_kakao_url(place_name)
    if not place_url:
        result = f"{place_name}: 카카오맵에서 장소를 찾을 수 없음"
        _cache[cache_key] = (result, now)
        return result

    try:
        hours_text = _scrape_hours(place_url)
        lines = [
            f"[{place_name}]",
            f"링크: {place_url}",
            "",
            hours_text,
        ]
        if visit_date:
            lines.append("")
            lines.append(f"방문 예정: {visit_date}")
        result = "\n".join(lines)
    except Exception as e:
        result = (
            f"{place_name}: 영업시간 조회 실패\n"
            f"오류: {type(e).__name__}: {e}\n"
            f"링크: {place_url}"
        )

    _cache[cache_key] = (result, now)
    return result

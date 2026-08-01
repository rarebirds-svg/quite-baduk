# referrer URL을 호스트로 파싱하고 유입 소스(search/social/referral/direct/internal)로 분류한다.
from __future__ import annotations

from urllib.parse import urlparse

INTERNAL_HOST = "inkbaduk.com"

# 호스트 라벨(점 구분 조각) 단위 매칭 — substring 매칭의 오분류(netflix.com→'x.com',
# content.com→'t.co')를 피한다. 도메인 라벨이 정확히 일치할 때만 분류한다.
_SEARCH_LABELS = frozenset({
    "google", "naver", "daum", "bing", "duckduckgo", "yahoo", "yandex", "baidu", "nate",
})
_SOCIAL_LABELS = frozenset({
    "facebook", "instagram", "twitter", "youtube", "threads", "kakao",
    "reddit", "linkedin", "pinterest", "tiktok",
})
# 라벨이 아니라 등록 도메인 전체로 매칭해야 하는 소셜(짧은 라벨이라 오탐 위험).
_SOCIAL_DOMAINS = frozenset({"x.com", "t.co", "youtu.be", "band.us", "fb.com"})


def parse_referrer_host(referrer: str) -> str | None:
    if not referrer:
        return None
    try:
        host = urlparse(referrer).hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def classify_source(referrer_host: str | None) -> str:
    if referrer_host is None:
        return "direct"
    host = referrer_host.lower()
    if host == INTERNAL_HOST or host.endswith("." + INTERNAL_HOST):
        return "internal"
    labels = set(host.split("."))
    if labels & _SEARCH_LABELS:
        return "search"
    if any(host == d or host.endswith("." + d) for d in _SOCIAL_DOMAINS):
        return "social"
    if labels & _SOCIAL_LABELS:
        return "social"
    return "referral"

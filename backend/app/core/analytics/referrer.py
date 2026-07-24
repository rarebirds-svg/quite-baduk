# referrer URL을 호스트로 파싱하고 유입 소스(search/social/referral/direct/internal)로 분류한다.
from __future__ import annotations

from urllib.parse import urlparse

INTERNAL_HOST = "inkbaduk.com"

_SEARCH = ("google.", "naver.", "daum.", "bing.", "duckduckgo.", "search.")
_SOCIAL = ("facebook.", "instagram.", "twitter.", "x.com", "t.co",
           "youtube.", "youtu.be", "threads.", "kakao.", "band.us")


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
    if any(s in host for s in _SEARCH):
        return "search"
    if any(s in host for s in _SOCIAL):
        return "social"
    return "referral"

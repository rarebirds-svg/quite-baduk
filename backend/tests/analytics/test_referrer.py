# referrer 파싱·source 분류 로직 검증.
from __future__ import annotations

import pytest

from app.core.analytics.referrer import classify_source, parse_referrer_host


@pytest.mark.parametrize("ref,host", [
    ("https://www.google.com/", "google.com"),
    ("https://search.naver.com/search.naver?query=x", "search.naver.com"),
    ("", None),
    ("not a url", None),
])
def test_parse_referrer_host(ref, host):
    assert parse_referrer_host(ref) == host


@pytest.mark.parametrize("host,source", [
    (None, "direct"),
    ("google.com", "search"),
    ("search.naver.com", "search"),
    ("m.search.daum.net", "search"),
    ("bing.com", "search"),
    ("facebook.com", "social"),
    ("t.co", "social"),
    ("x.com", "social"),
    ("m.x.com", "social"),
    ("google.co.kr", "search"),
    ("inkbaduk.com", "internal"),
    ("someblog.tistory.com", "referral"),
    # 라벨 경계 매칭 — substring 오분류가 재발하지 않도록 고정.
    ("netflix.com", "referral"),      # 'x.com' 부분문자열 포함하지만 social 아님
    ("content.com", "referral"),      # 't.co' 부분문자열 포함하지만 social 아님
    ("researchgate.net", "referral"),
    ("mygoogle-fan.net", "referral"),  # 'google' 라벨이 아니므로 search 아님
])
def test_classify_source(host, source):
    assert classify_source(host) == source

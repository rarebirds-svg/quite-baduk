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
    ("inkbaduk.com", "internal"),
    ("someblog.tistory.com", "referral"),
])
def test_classify_source(host, source):
    assert classify_source(host) == source

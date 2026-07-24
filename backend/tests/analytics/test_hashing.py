# 방문자 해시 결정성·일일 솔트 회전 검증.
from __future__ import annotations

from app.core.analytics.hashing import daily_salt, visitor_hash


def test_visitor_hash_deterministic():
    assert visitor_hash("1.2.3.4", "salt") == visitor_hash("1.2.3.4", "salt")


def test_visitor_hash_differs_by_ip_and_salt():
    assert visitor_hash("1.2.3.4", "s") != visitor_hash("9.9.9.9", "s")
    assert visitor_hash("1.2.3.4", "s1") != visitor_hash("1.2.3.4", "s2")


def test_daily_salt_stable_per_day_rotates_across_days():
    assert daily_salt("2026-07-24") == daily_salt("2026-07-24")
    assert daily_salt("2026-07-24") != daily_salt("2026-07-25")

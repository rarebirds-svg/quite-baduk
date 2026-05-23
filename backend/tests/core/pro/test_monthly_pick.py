# 월간 픽 알고리즘 단위 테스트 — 결정적 시드와 fallback 동작.
import pytest

from app.core.pro.monthly_pick import (
    InvalidYearMonth,
    parse_yyyymm,
    pick_index,
)


def test_parse_yyyymm_valid():
    assert parse_yyyymm("2026-05") == (2026, 5)
    assert parse_yyyymm("1999-12") == (1999, 12)


def test_parse_yyyymm_rejects_bad_format():
    for bad in ["2026-13", "2026/05", "26-05", "2026-5", "2026-00", "abcd-ef"]:
        with pytest.raises(InvalidYearMonth):
            parse_yyyymm(bad)


def test_pick_index_deterministic():
    assert pick_index("2026-05", 100) == pick_index("2026-05", 100)
    assert pick_index("2026-06", 100) == pick_index("2026-06", 100)


def test_pick_index_changes_with_input():
    a = pick_index("2026-05", 100)
    b = pick_index("2026-06", 100)
    assert a != b  # SHA256 충돌 가능성 극히 낮음


def test_pick_index_in_range():
    for yyyymm in ["2024-01", "2024-06", "2025-12"]:
        assert 0 <= pick_index(yyyymm, 50) < 50


def test_pick_index_single_candidate():
    assert pick_index("2026-05", 1) == 0


def test_pick_index_zero_raises():
    with pytest.raises(ValueError):
        pick_index("2026-05", 0)

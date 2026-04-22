"""Tests for nickname normalization + validation contract."""
from __future__ import annotations

import pytest

from app.core.nickname import (
    MAX_LEN,
    MIN_LEN,
    InvalidNickname,
    normalize,
    to_key,
    validate,
)


# ─── normalize ───────────────────────────────────────────────────────────

def test_normalize_trims_whitespace():
    assert normalize("  alice  ") == "alice"


def test_normalize_applies_nfkc():
    # Full-width "Ａ" (U+FF21) → ASCII "A" under NFKC
    assert normalize("Ａlice") == "Alice"


def test_normalize_preserves_hangul():
    assert normalize("홍길동") == "홍길동"


# ─── validate ────────────────────────────────────────────────────────────

def test_validate_accepts_two_through_thirty_two_chars():
    validate("ab")
    validate("a" * MAX_LEN)


def test_validate_rejects_too_short():
    with pytest.raises(InvalidNickname):
        validate("a")


def test_validate_rejects_too_long():
    with pytest.raises(InvalidNickname):
        validate("a" * (MAX_LEN + 1))


def test_validate_rejects_empty_after_trim():
    # normalize() would turn "   " into "" — validate is called on the normalized form.
    with pytest.raises(InvalidNickname):
        validate("")


def test_validate_rejects_control_characters():
    with pytest.raises(InvalidNickname):
        validate("alice\x00bob")


def test_validate_rejects_newline():
    with pytest.raises(InvalidNickname):
        validate("ali\nce")


def test_validate_rejects_tab():
    with pytest.raises(InvalidNickname):
        validate("ali\tce")


def test_validate_rejects_emoji_face():
    with pytest.raises(InvalidNickname):
        validate("alice😀")


def test_validate_rejects_emoji_flag():
    with pytest.raises(InvalidNickname):
        validate("kr🇰🇷")


def test_validate_rejects_symbol_modifier():
    # Skin tone modifier
    with pytest.raises(InvalidNickname):
        validate("alice🏻")


def test_validate_accepts_korean_punctuation():
    # middle dot, ideographic space-equivalents allowed via NFKC; just latin/hangul letters here
    validate("홍길동_2")
    validate("Alice.Kim")


def test_validate_assumes_caller_already_normalized():
    """validate doesn't normalize — that's the caller's job. We verify raw
    whitespace-only strings are rejected explicitly."""
    with pytest.raises(InvalidNickname):
        validate("   ")


# ─── to_key (uniqueness comparison form) ─────────────────────────────────

def test_to_key_is_casefolded():
    assert to_key(normalize("Alice")) == to_key(normalize("alice"))
    assert to_key(normalize("ALICE")) == to_key(normalize("alice"))


def test_to_key_preserves_hangul_case_insensitive_idempotent():
    # Hangul has no case — key is identical to input
    assert to_key(normalize("홍길동")) == "홍길동"


def test_to_key_distinguishes_different_names():
    assert to_key(normalize("alice")) != to_key(normalize("bob"))


def test_min_len_is_two_max_len_is_thirty_two():
    assert MIN_LEN == 2
    assert MAX_LEN == 32

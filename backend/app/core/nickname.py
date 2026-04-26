"""Nickname normalization, validation, and uniqueness-key derivation.

The uniqueness key (``to_key``) is what the in-memory NicknameRegistry and
the DB ``sessions.nickname_key`` UNIQUE constraint compare on. The display
form (``normalize`` output) is what we show back to the user.
"""
from __future__ import annotations

import unicodedata

MIN_LEN = 2
MAX_LEN = 32


class InvalidNickname(ValueError):
    """Raised when a nickname fails structural validation."""


def normalize(name: str) -> str:
    """Trim + NFKC-normalize. Display form.

    Caller should always feed ``validate`` the result of ``normalize``.
    """
    return unicodedata.normalize("NFKC", name).strip()


def _is_disallowed_char(ch: str) -> bool:
    # Control chars, format chars, line/paragraph separators.
    cat = unicodedata.category(ch)
    if cat.startswith("C"):  # Cc, Cf, Cn, Co, Cs
        return True
    if cat in {"Zl", "Zp"}:
        return True
    # Whitespace other than the NBSP that NFKC already normalised away.
    if ch.isspace():
        return True
    # Emoji + pictographs. Unicodedata doesn't expose Extended_Pictographic
    # directly; we use the broader 'So' (Symbol, Other) and variation
    # selectors / modifier codepoints as a practical proxy.
    if cat in {"So", "Sk"}:
        return True
    # Skin-tone / variation modifier codepoints (U+1F3FB..U+1F3FF, U+FE0F).
    cp = ord(ch)
    if 0x1F3FB <= cp <= 0x1F3FF or cp == 0xFE0F or cp == 0x200D:
        return True
    # Regional indicator symbols (flag emoji components).
    if 0x1F1E6 <= cp <= 0x1F1FF:
        return True
    return False


def validate(name: str) -> None:
    """Raise :class:`InvalidNickname` if the nickname is unacceptable.

    Expects the caller to have already ``normalize``d the value.
    """
    n = len(name)
    if n < MIN_LEN or n > MAX_LEN:
        raise InvalidNickname(f"length {n} not in [{MIN_LEN}, {MAX_LEN}]")
    for ch in name:
        if _is_disallowed_char(ch):
            raise InvalidNickname(f"disallowed character: U+{ord(ch):04X}")


def to_key(normalized: str) -> str:
    """Uniqueness comparison form. Casefolded NFKC."""
    return normalized.casefold()

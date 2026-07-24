# 방문자를 원본 IP 저장 없이 식별하기 위한 일일 솔트 해시 — 익일 재식별 불가.
from __future__ import annotations

import hashlib
import secrets

_salts: dict[str, str] = {}


def daily_salt(day: str) -> str:
    """UTC 날짜 문자열(YYYY-MM-DD)별 랜덤 솔트. 프로세스 생존 동안 캐시."""
    salt = _salts.get(day)
    if salt is None:
        salt = secrets.token_hex(16)
        _salts[day] = salt
    return salt


def visitor_hash(ip: str, salt: str) -> str:
    return hashlib.sha256(f"{ip}:{salt}".encode()).hexdigest()

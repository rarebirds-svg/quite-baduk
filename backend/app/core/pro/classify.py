# 프로 기보 event 문자열로 base 컬렉션(world/masterpiece)을 판정한다.
from __future__ import annotations

# 국제기전 키워드(소문자). 포함되면 'world', 아니면 'masterpiece'.
WORLD_EVENT_KEYS = ("chunlan", "fujitsu", "ing cup", "lg cup", "samsung", "toyota")


def classify_collection(event: str | None) -> str:
    if not event:
        return "masterpiece"
    low = event.lower()
    return "world" if any(k in low for k in WORLD_EVENT_KEYS) else "masterpiece"

# 방문 통계에서 제외할 봇·크롤러를 User-Agent로 판정한다.
from __future__ import annotations

_BOT_MARKERS = (
    "bot", "crawler", "spider", "slurp", "yeti", "bingbot", "googlebot",
    "baiduspider", "yandex", "duckduckbot", "curl", "wget", "python-requests",
    "headless", "facebookexternalhit", "preview",
)


def is_bot(user_agent: str | None) -> bool:
    if not user_agent:
        return True
    ua = user_agent.lower()
    return any(m in ua for m in _BOT_MARKERS)

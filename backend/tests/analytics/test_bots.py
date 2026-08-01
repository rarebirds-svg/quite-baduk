# User-Agent 봇 판정 검증.
from __future__ import annotations

import pytest

from app.core.analytics.bots import is_bot


@pytest.mark.parametrize("ua,bot", [
    (None, True),
    ("", True),
    ("Mozilla/5.0 (iPhone) Safari", False),
    ("Googlebot/2.1 (+http://www.google.com/bot.html)", True),
    ("Mozilla/5.0 (compatible; Yeti/1.1; +http://naver.me/bot)", True),
    ("curl/8.0", True),
])
def test_is_bot(ua, bot):
    assert is_bot(ua) is bot

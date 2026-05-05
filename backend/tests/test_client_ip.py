"""Unit tests for :mod:`app.client_ip`. The helper drives rate-limit
keys for unauthenticated endpoints, so each branch (CF header trusted,
peer fallback, unknown peer) needs a regression."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app import client_ip as _client_ip_module
from app.client_ip import client_ip


def _request_with(headers: dict[str, str], peer_host: str | None) -> MagicMock:
    """Build a stand-in for :class:`fastapi.Request` with just the two
    attributes our helper looks at."""
    req = MagicMock()
    req.headers = headers
    if peer_host is None:
        req.client = None
    else:
        client = MagicMock()
        client.host = peer_host
        req.client = client
    return req


def test_client_ip_uses_cf_header_when_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _client_ip_module.settings, "cf_trusted_proxy", True
    )
    req = _request_with(
        headers={"cf-connecting-ip": "203.0.113.5"},
        peer_host="127.0.0.1",  # cloudflared local
    )
    assert client_ip(req) == "203.0.113.5"


def test_client_ip_strips_whitespace_in_cf_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _client_ip_module.settings, "cf_trusted_proxy", True
    )
    req = _request_with(
        headers={"cf-connecting-ip": "  203.0.113.5  "},
        peer_host="127.0.0.1",
    )
    assert client_ip(req) == "203.0.113.5"


def test_client_ip_falls_back_to_peer_when_cf_header_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even with ``cf_trusted_proxy=True``, no header → use peer."""
    monkeypatch.setattr(
        _client_ip_module.settings, "cf_trusted_proxy", True
    )
    req = _request_with(headers={}, peer_host="10.0.0.42")
    assert client_ip(req) == "10.0.0.42"


def test_client_ip_ignores_cf_header_when_proxy_untrusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default (cf_trusted_proxy=False) must NOT trust the CF header,
    otherwise a public-facing dev process is rate-limit spoofable."""
    monkeypatch.setattr(
        _client_ip_module.settings, "cf_trusted_proxy", False
    )
    req = _request_with(
        headers={"cf-connecting-ip": "203.0.113.5"},
        peer_host="10.0.0.42",
    )
    assert client_ip(req) == "10.0.0.42"


def test_client_ip_returns_unknown_when_peer_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _client_ip_module.settings, "cf_trusted_proxy", False
    )
    req = _request_with(headers={}, peer_host=None)
    assert client_ip(req) == "unknown"

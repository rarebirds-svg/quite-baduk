"""Resolve a stable client IP for rate limiting and audit logging.

Trust model:

- ``X-Forwarded-For`` is **never** trusted. Any client can set it.
- ``CF-Connecting-IP`` is trusted iff :attr:`Settings.cf_trusted_proxy` is
  True. This is appropriate when the FastAPI process is reachable
  exclusively through a Cloudflare tunnel (``cloudflared``), because in
  that topology the only connections we see come from the local tunnel
  daemon and the only way for a client IP to reach us is through CF's
  edge, which sets the header.
- Otherwise we fall back to the immediate peer address from the ASGI
  scope. In dev that's the dev machine's loopback interface.
"""
from __future__ import annotations

from fastapi import Request

from app.config import settings


def client_ip(request: Request) -> str:
    """Best-effort client IP. Returns ``"unknown"`` only when neither the
    Cloudflare header nor an ASGI peer address is available.
    """
    if settings.cf_trusted_proxy:
        cf = request.headers.get("cf-connecting-ip")
        if cf:
            return cf.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def client_country(request: Request) -> str | None:
    """Best-effort 2-letter ISO country from Cloudflare's ``CF-IPCountry``
    header. Trusted only when :attr:`Settings.cf_trusted_proxy` is set —
    same trust model as :func:`client_ip`.

    Returns ``None`` when the header is absent (dev / non-Cloudflare) or
    carries a non-country sentinel: ``XX`` (unknown), ``T1`` (Tor).
    """
    if not settings.cf_trusted_proxy:
        return None
    raw = request.headers.get("cf-ipcountry")
    if not raw:
        return None
    code = raw.strip().upper()
    if len(code) != 2 or code in ("XX", "T1"):
        return None
    return code

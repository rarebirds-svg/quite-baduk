"""Baseline security response headers.

The headers here are the minimum that consumer-facing app review checklists
(Apple, Google) and common web-security guidelines (OWASP Secure Headers)
expect. Any environment-specific tightening (CSP report-uri, COOP/COEP)
is best done at the reverse proxy / Cloudflare Transform Rules layer.

Notes on the chosen CSP:

* ``script-src`` allows ``'unsafe-inline'`` because Next.js 14 ships its
  hydration payload as an inline ``<script>`` and we are not nonce-aware.
  Switching to a nonce-based policy is a Next.js 15 era follow-up.
* ``style-src`` allows ``'unsafe-inline'`` for the same reason — Tailwind's
  runtime utility resolution and the editorial design's CSS variables in
  ``style`` attributes need it.
* ``connect-src`` deliberately whitelists ``ws:`` and ``wss:`` so the game
  WebSocket works behind Cloudflare's TLS termination.
* ``frame-ancestors 'none'`` doubles up with ``X-Frame-Options: DENY`` for
  legacy clients.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self' ws: wss:",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ]
)

_PERMISSIONS_POLICY = ", ".join(
    [
        "accelerometer=()",
        "camera=()",
        "geolocation=()",
        "gyroscope=()",
        "magnetometer=()",
        "microphone=()",
        "payment=()",
        "usb=()",
    ]
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add the project's default security response headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault("Content-Security-Policy", _CSP)
        response.headers.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        if settings.is_production:
            # HSTS is harmless over plain HTTP (browsers ignore it), but we
            # only emit it in production to avoid surprising local-dev users
            # whose browser cache might pin a stale localhost certificate.
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

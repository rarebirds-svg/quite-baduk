from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.game_service import GameError


def _safe_validation_errors(exc: RequestValidationError) -> object:
    """pydantic v2 오류 목록을 JSON 직렬화 가능하게 정리한다.

    비JSON 본문이면 ``input``에 raw bytes가 들어와 그대로 직렬화하면
    TypeError(500)가 난다. bytes는 치환 디코딩으로 문자열화한다.
    """
    return jsonable_encoder(
        exc.errors(),
        custom_encoder={bytes: lambda b: b.decode("utf-8", errors="replace")},
    )


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": str(exc.detail), "message_key": f"errors.{exc.detail}"}},
        )

    @app.exception_handler(RequestValidationError)
    async def val_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message_key": "errors.validation",
                    "detail": _safe_validation_errors(exc),
                }
            },
        )

    @app.exception_handler(GameError)
    async def game_error_handler(request: Request, exc: GameError) -> JSONResponse:
        # Outer "detail" matches FastAPI's default error envelope; the inner
        # {code, detail} pair is what clients now read so they can distinguish
        # e.g. "you tried to play on F5" from "you tried to play on F6"
        # (both surface the same `code` but with different `detail`).
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "code": exc.code,
                    "detail": exc.detail,
                }
            },
        )

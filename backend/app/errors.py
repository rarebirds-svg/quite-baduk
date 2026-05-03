from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.game_service import GameError


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
                    "detail": exc.errors(),
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

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import enable_wal
from app.errors import register_handlers

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await enable_wal()

    from app.session_purge import run_purge_loop

    purge_task = asyncio.create_task(
        run_purge_loop(
            interval_sec=settings.session_purge_interval_sec,
            ttl_sec=settings.session_idle_ttl_sec,
        )
    )
    try:
        yield
    finally:
        purge_task.cancel()
        try:
            await purge_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(title="Baduk AI", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from app.api import admin as admin_router
    from app.api import analysis as analysis_router
    from app.api import games as games_router
    from app.api import health as health_router
    from app.api import session as session_router
    from app.api import stats as stats_router
    from app.api import ws as ws_router

    app.include_router(session_router.router)
    app.include_router(games_router.router)
    app.include_router(analysis_router.router)
    app.include_router(stats_router.router)
    app.include_router(health_router.router)
    app.include_router(ws_router.router)
    app.include_router(admin_router.router)

    register_handlers(app)
    return app


app = create_app()

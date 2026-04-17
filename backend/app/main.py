from contextlib import asynccontextmanager
from typing import AsyncGenerator

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
    yield


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
    from app.api import auth as auth_router
    from app.api import games as games_router
    from app.api import analysis as analysis_router
    from app.api import stats as stats_router
    from app.api import health as health_router
    from app.api import ws as ws_router

    app.include_router(auth_router.router)
    app.include_router(games_router.router)
    app.include_router(analysis_router.router)
    app.include_router(stats_router.router)
    app.include_router(health_router.router)
    app.include_router(ws_router.router)

    register_handlers(app)
    return app


app = create_app()

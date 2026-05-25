import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import enable_wal
from app.errors import register_handlers
from app.middleware.security_headers import SecurityHeadersMiddleware

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

    from app import last_seen_cache
    from app.db import AsyncSessionLocal
    last_seen_cache.start_flusher(AsyncSessionLocal)

    from app.engine_pool import get_pool
    pool = get_pool()
    await pool.start_all()

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
        # cache 잔여를 DB로 마저 흘려보낸 뒤 flusher task 종료.
        try:
            await last_seen_cache.flush_all(AsyncSessionLocal)
        finally:
            await last_seen_cache.stop_flusher()
        purge_task.cancel()
        try:
            await purge_task
        except asyncio.CancelledError:
            pass
        await pool.stop_all()


def create_app() -> FastAPI:
    app = FastAPI(title="Baduk AI", version="0.1.0", lifespan=lifespan)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from app.api import admin as admin_router
    from app.api import admin_pro as admin_pro_router
    from app.api import analysis as analysis_router
    from app.api import daily as daily_router
    from app.api import games as games_router
    from app.api import health as health_router
    from app.api import session as session_router
    from app.api import spectate as spectate_router
    from app.api import spectate_pro as spectate_pro_router
    from app.api import stats as stats_router
    from app.api import ws as ws_router

    app.include_router(session_router.router)
    app.include_router(games_router.router)
    app.include_router(analysis_router.router)
    app.include_router(stats_router.router)
    app.include_router(health_router.router)
    app.include_router(ws_router.router)
    app.include_router(admin_router.router)
    app.include_router(admin_pro_router.router)
    app.include_router(daily_router.router)
    app.include_router(spectate_pro_router.router)
    app.include_router(spectate_router.router)

    register_handlers(app)
    return app


app = create_app()

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from copilot_api.core.config import Settings, get_settings
from copilot_api.core.errors import register_exception_handlers
from copilot_api.core.middleware import RequestIDMiddleware
from copilot_api.core.request_guards import OriginCSRFMiddleware, SlidingWindowRateLimiter
from copilot_api.infrastructure.database.engine import (
    create_database_engine,
    create_session_factory,
)
from copilot_api.routers import api_v1_router
from copilot_api.routers.health import router as health_router
from copilot_api.services.maintenance import cleanup_expired_sessions


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)

    async def maintenance_loop() -> None:
        while True:
            try:
                await cleanup_expired_sessions(session_factory)
            except (SQLAlchemyError, OSError, TimeoutError):
                pass
            await asyncio.sleep(settings.session_cleanup_interval_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        maintenance_task = (
            asyncio.create_task(maintenance_loop()) if not settings.use_demo_repository else None
        )
        try:
            yield
        finally:
            if maintenance_task is not None:
                maintenance_task.cancel()
                with suppress(asyncio.CancelledError):
                    await maintenance_task
            await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.login_rate_limiter = SlidingWindowRateLimiter(
        settings.login_rate_limit_attempts,
        60.0,
    )
    origins = sorted(settings.allowed_origin_set)
    app.add_middleware(OriginCSRFMiddleware, allowed_origins=set(origins))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()

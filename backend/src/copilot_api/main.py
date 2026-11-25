from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from copilot_api.core.config import Settings, get_settings
from copilot_api.core.errors import register_exception_handlers
from copilot_api.core.middleware import RequestIDMiddleware
from copilot_api.infrastructure.database.engine import (
    create_database_engine,
    create_session_factory,
)
from copilot_api.routers import api_v1_router
from copilot_api.routers.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = create_database_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = create_session_factory(engine)
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()

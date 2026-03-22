from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.db import init_db
from src.core.logging import configure_logging
from src.api.routes.process import router as process_router
from src.api.routes.transactions import router as transactions_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: configure logging and initialise the database on startup."""
    configure_logging()
    await init_db()
    yield


def create_app() -> FastAPI:
    """Factory that builds and configures the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ARCRA API",
        description="Autonomous Reconciliation and Contextual Resolution Agent — Backend API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(transactions_router, prefix="/api/v1")
    app.include_router(process_router, prefix="/api/v1")

    return app


app = create_app()

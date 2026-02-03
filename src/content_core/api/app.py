"""FastAPI application for Content Core REST API."""

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from content_core.api.routes import engines_router, extract_router, health_router
from content_core.api.schemas import ErrorResponse
from content_core.logging import logger


def _get_version() -> str:
    """Get the Content Core version."""
    try:
        from importlib.metadata import version

        return version("content-core")
    except Exception:
        return "unknown"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Content Core API server")

    # Initialize processor registry
    from content_core.processors import ProcessorRegistry

    registry = ProcessorRegistry.instance()
    available = registry.list_names()
    logger.info(f"Available processors: {', '.join(available)}")

    yield

    # Shutdown
    logger.info("Shutting down Content Core API server")


def create_app(
    *,
    include_ui: bool = True,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        include_ui: Whether to mount the web UI. Default True.
        cors_origins: List of allowed CORS origins. Default allows all.

    Returns:
        Configured FastAPI application.
    """
    api_app = FastAPI(
        title="Content Core API",
        description="Extract content from URLs, files, and text",
        version=_get_version(),
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS middleware
    origins = cors_origins or ["*"]
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @api_app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error",
                detail=str(exc),
                error_type=type(exc).__name__,
            ).model_dump(),
        )

    # Mount API routes
    api_app.include_router(health_router, prefix="/api/v1")
    api_app.include_router(engines_router, prefix="/api/v1")
    api_app.include_router(extract_router, prefix="/api/v1")

    # Optionally mount web UI
    if include_ui and os.getenv("CCORE_UI_ENABLED", "true").lower() != "false":
        try:
            from content_core.ui import create_ui_router

            ui_router = create_ui_router()
            api_app.include_router(ui_router)
            logger.info("Web UI mounted at /")
        except ImportError as e:
            logger.warning(f"Web UI not available: {e}")

    return api_app


# Default app instance for uvicorn
app = create_app()

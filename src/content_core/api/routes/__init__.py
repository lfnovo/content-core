"""API route modules."""

from content_core.api.routes.engines import router as engines_router
from content_core.api.routes.extract import router as extract_router
from content_core.api.routes.health import router as health_router

__all__ = ["health_router", "engines_router", "extract_router"]

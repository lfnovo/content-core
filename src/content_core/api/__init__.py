"""Content Core REST API module.

This module provides a FastAPI-based REST API for content extraction.

Usage:
    # Run with uvicorn
    uvicorn content_core.api:app --host 0.0.0.0 --port 8000

    # Or programmatically
    from content_core.api import create_app
    app = create_app()
"""

from content_core.api.app import app, create_app

__all__ = ["app", "create_app"]

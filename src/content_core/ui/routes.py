"""Web UI routes for Content Core."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from content_core.content.extraction import extract_content
from content_core.logging import logger
from content_core.processors import ProcessorRegistry

# Get template and static directories
UI_DIR = Path(__file__).parent
TEMPLATES_DIR = UI_DIR / "templates"
STATIC_DIR = UI_DIR / "static"


def _get_version() -> str:
    """Get the Content Core version."""
    try:
        from importlib.metadata import version

        return version("content-core")
    except Exception:
        return "unknown"


def _get_unavailability_reason(processor_cls) -> Optional[str]:
    """Determine why a processor is unavailable."""
    if processor_cls.is_available():
        return None

    name = processor_cls.name
    caps = processor_cls.capabilities
    requires = caps.requires

    # Special case for firecrawl - needs API key
    if name == "firecrawl":
        if not os.environ.get("FIRECRAWL_API_KEY"):
            return "Requires FIRECRAWL_API_KEY"

    # Check if it's a dependency issue
    if requires:
        return f"Install: content-core[{requires[0]}]"

    return "Not available"


def create_ui_router() -> APIRouter:
    """Create the UI router with templates and static files."""
    router = APIRouter(tags=["ui"])

    # Set up Jinja2 templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Mount static files
    router.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """Main extraction page."""
        # Get all engines (available and unavailable) with full capabilities
        engines = []
        for processor_cls in ProcessorRegistry._all_processors:
            caps = processor_cls.capabilities
            available = processor_cls.is_available()
            reason = _get_unavailability_reason(processor_cls) if not available else None

            engines.append({
                "name": processor_cls.name,
                "priority": caps.priority,
                "category": caps.category,
                "mime_types": caps.mime_types,
                "extensions": caps.extensions,
                "available": available,
                "reason": reason,
            })
        engines.sort(key=lambda e: (-1 if e["available"] else 1, -e["priority"]))

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "engines": engines,
                "version": _get_version(),
            },
        )

    @router.post("/ui/extract", response_class=HTMLResponse)
    async def ui_extract(
        request: Request,
        source_type: str = Form(...),
        url: Optional[str] = Form(default=None),
        text_content: Optional[str] = Form(default=None),
        file: Optional[UploadFile] = File(default=None),
        engine: Optional[str] = Form(default=None),
        timeout: int = Form(default=300),
    ) -> HTMLResponse:
        """Handle extraction form submission via HTMX."""
        try:
            # Parse options from form fields prefixed with "options."
            form_data = await request.form()
            options: Dict[str, Any] = {}
            for key, value in form_data.items():
                if key.startswith("options."):
                    opt_name = key[8:]  # Remove "options." prefix
                    # Handle checkboxes ("on" = True, missing = False)
                    if value == "on":
                        options[opt_name] = True
                    elif value:  # Non-empty string values
                        options[opt_name] = value

            # Only pass options if there are any
            extraction_options = options if options else None

            # Determine which source to use
            if source_type == "url" and url:
                result = await extract_content(
                    url=url.strip(),
                    engine=engine if engine else None,
                    timeout=timeout,
                    options=extraction_options,
                )
            elif source_type == "text" and text_content:
                result = await extract_content(
                    content=text_content,
                    engine=engine if engine else None,
                    timeout=timeout,
                    options=extraction_options,
                )
            elif source_type == "file" and file and file.filename:
                # Write to temp file
                suffix = Path(file.filename).suffix or ""
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    content = await file.read()
                    tmp.write(content)
                    tmp_path = tmp.name

                try:
                    result = await extract_content(
                        file_path=tmp_path,
                        engine=engine if engine else None,
                        timeout=timeout,
                        options=extraction_options,
                    )
                finally:
                    try:
                        Path(tmp_path).unlink()
                    except Exception:
                        pass
            else:
                return templates.TemplateResponse(
                    request=request,
                    name="partials/error.html",
                    context={
                        "error": "No valid input provided",
                        "detail": "Please provide a URL, upload a file, or enter text content.",
                    },
                )

            return templates.TemplateResponse(
                request=request,
                name="partials/result.html",
                context={
                    "content": result.content,
                    "source_type": result.source_type,
                    "mime_type": result.mime_type,
                    "engine_used": result.engine_used,
                    "metadata": result.metadata,
                    "warnings": result.warnings,
                },
            )

        except Exception as e:
            logger.error(f"UI extraction error: {e}")
            return templates.TemplateResponse(
                request=request,
                name="partials/error.html",
                context={
                    "error": "Extraction failed",
                    "detail": str(e),
                },
            )

    return router

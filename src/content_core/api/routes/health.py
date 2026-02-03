"""Health check endpoints."""

from fastapi import APIRouter

from content_core.api.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


def _get_version() -> str:
    """Get the Content Core version."""
    try:
        from importlib.metadata import version

        return version("content-core")
    except Exception:
        return "unknown"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint.

    Returns basic health status and version information.
    """
    return HealthResponse(
        status="healthy",
        version=_get_version(),
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    """Readiness check endpoint.

    Checks if the service is ready to handle requests.
    Verifies that key components are available.
    """
    checks: dict[str, bool] = {}

    # Check processor registry
    try:
        from content_core.processors import ProcessorRegistry

        registry = ProcessorRegistry.instance()
        checks["processors"] = len(registry.list_available()) > 0
    except Exception:
        checks["processors"] = False

    # Overall status
    all_checks_pass = all(checks.values())

    return ReadyResponse(
        status="ready" if all_checks_pass else "not_ready",
        checks=checks,
    )

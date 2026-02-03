"""Pydantic schemas for the Content Core REST API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    version: str = Field(description="Content Core version")


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str = Field(description="Service status")
    checks: Dict[str, bool] = Field(description="Individual component checks")


class EngineInfo(BaseModel):
    """Information about an extraction engine."""

    name: str = Field(description="Engine name")
    available: bool = Field(description="Whether the engine is available")
    reason: Optional[str] = Field(
        default=None,
        description="Reason why engine is unavailable (only set when available=False)",
    )
    mime_types: List[str] = Field(description="Supported MIME types")
    extensions: List[str] = Field(description="Supported file extensions")
    priority: int = Field(description="Engine priority (higher = preferred)")
    category: str = Field(description="Engine category")
    requires: List[str] = Field(
        default_factory=list, description="Required optional dependencies"
    )


class EnginesResponse(BaseModel):
    """Response containing available engines."""

    engines: List[EngineInfo] = Field(description="List of available engines")


class ExtractionRequest(BaseModel):
    """Request for content extraction."""

    url: Optional[str] = Field(
        default=None, description="URL to extract content from"
    )
    content: Optional[str] = Field(
        default=None, description="Raw content (text or base64 encoded)"
    )
    engine: Optional[str] = Field(
        default=None, description="Engine to use for extraction (auto-select if not specified)"
    )
    timeout: int = Field(
        default=300, ge=1, le=3600, description="Timeout in seconds"
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional engine-specific options"
    )

    @field_validator("url", "content")
    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure strings are not empty if provided."""
        if v is not None and not v.strip():
            return None
        return v


class ExtractionResponse(BaseModel):
    """Response from content extraction."""

    content: str = Field(description="Extracted content")
    source_type: str = Field(description="Type of source: 'file', 'url', or 'content'")
    mime_type: Optional[str] = Field(
        default=None, description="MIME type of the processed content"
    )
    engine_used: str = Field(description="Name of the engine that performed extraction")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional extraction metadata"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Warnings that occurred during extraction"
    )


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    error_type: Optional[str] = Field(default=None, description="Error type name")

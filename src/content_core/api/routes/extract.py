"""Content extraction endpoints."""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from content_core.api.schemas import ErrorResponse, ExtractionRequest, ExtractionResponse
from content_core.common import ExtractionError, FatalExtractionError
from content_core.content.extraction import extract_content
from content_core.logging import logger

router = APIRouter(tags=["extract"])


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Extraction error"},
    },
)
async def extract_from_json(request: ExtractionRequest) -> ExtractionResponse:
    """Extract content from URL or raw content.

    Provide either a URL or raw content (text or base64 encoded).
    Optionally specify an engine to use for extraction.
    """
    # Validate exactly one source is provided
    sources = [request.url, request.content]
    provided = [s for s in sources if s is not None]

    if len(provided) == 0:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'url' or 'content'",
        )
    if len(provided) > 1:
        raise HTTPException(
            status_code=400,
            detail="Must provide only one of 'url' or 'content'",
        )

    try:
        if request.url:
            result = await extract_content(
                url=request.url,
                engine=request.engine,
                timeout=request.timeout,
                options=request.options,
            )
        else:
            result = await extract_content(
                content=request.content,
                engine=request.engine,
                timeout=request.timeout,
                options=request.options,
            )

        return ExtractionResponse(
            content=result.content,
            source_type=result.source_type,
            mime_type=result.mime_type,
            engine_used=result.engine_used,
            metadata=result.metadata,
            warnings=result.warnings,
        )

    except FatalExtractionError as e:
        logger.error(f"Fatal extraction error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except ExtractionError as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}",
        )


@router.post(
    "/extract/file",
    response_model=ExtractionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Extraction error"},
    },
)
async def extract_from_file(
    file: UploadFile = File(..., description="File to extract content from"),
    engine: Optional[str] = Form(
        default=None, description="Engine to use for extraction"
    ),
    timeout: int = Form(default=300, ge=1, le=3600, description="Timeout in seconds"),
) -> ExtractionResponse:
    """Extract content from an uploaded file.

    Upload a file (PDF, DOCX, image, audio, etc.) and extract its content.
    Optionally specify an engine to use for extraction.
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File must have a filename",
        )

    # Get file extension
    suffix = Path(file.filename).suffix or ""

    try:
        # Write uploaded file to temp location
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = await extract_content(
                file_path=tmp_path,
                engine=engine,
                timeout=timeout,
            )

            return ExtractionResponse(
                content=result.content,
                source_type=result.source_type,
                mime_type=result.mime_type,
                engine_used=result.engine_used,
                metadata=result.metadata,
                warnings=result.warnings,
            )

        finally:
            # Clean up temp file
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass

    except FatalExtractionError as e:
        logger.error(f"Fatal extraction error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except ExtractionError as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during file extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}",
        )

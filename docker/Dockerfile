# Content Core Docker Image
# Multi-stage build for optimized image size
#
# Build variants:
#   Minimal (default): Only core dependencies (docling)
#     docker build -t content-core:minimal .
#
#   Full: All optional dependencies
#     docker build -t content-core:full \
#       --build-arg INSTALL_PYMUPDF=true \
#       --build-arg INSTALL_MARKER=true \
#       --build-arg INSTALL_CRAWL4AI=true .

# Global build arguments (declared before first FROM to be available in all stages)
ARG INSTALL_PYMUPDF=false
ARG INSTALL_MARKER=false
ARG INSTALL_CRAWL4AI=false
ARG PRELOAD_DOCLING_MODELS=true
ARG PRELOAD_WHISPER_MODELS=false
ARG PRELOAD_VLM_MODELS=false
ARG PRELOAD_MARKER_MODELS=false

# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
FROM python:3.11-slim AS builder

# Re-declare build arguments to use in this stage
ARG INSTALL_PYMUPDF
ARG INSTALL_MARKER
ARG INSTALL_CRAWL4AI

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set up working directory
WORKDIR /app

# Copy dependency files and source (needed for hatchling build)
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Create virtual environment and install dependencies
# Include server extras for uvicorn
RUN uv sync --frozen --no-dev --extra server

# Install optional PyMuPDF dependency (AGPL-3.0 license)
RUN if [ "$INSTALL_PYMUPDF" = "true" ]; then \
    echo "Installing PyMuPDF (AGPL-3.0 license)..." && \
    uv pip install "pymupdf>=1.25.5" "pymupdf4llm>=0.0.17"; \
    fi

# Install optional Crawl4AI dependency (Playwright browsers installed in runtime stage)
RUN if [ "$INSTALL_CRAWL4AI" = "true" ]; then \
    echo "Installing Crawl4AI..." && \
    uv pip install "crawl4ai>=0.7.0"; \
    fi

# =============================================================================
# Stage 2: Marker Builder - Install Marker with system dependencies (optional)
# =============================================================================
FROM builder AS marker-builder

# Re-declare build argument to use in this stage
ARG INSTALL_MARKER

# Install Marker system dependencies and package (GPL-3.0 license)
# Marker requires Cairo, Pango, and other graphics libraries
RUN if [ "$INSTALL_MARKER" = "true" ]; then \
    apt-get update && apt-get install -y --no-install-recommends \
        libcairo2-dev \
        libpango1.0-dev \
        libgdk-pixbuf-2.0-dev \
        libffi-dev \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/* \
    && echo "Installing Marker (GPL-3.0 license)..." \
    && uv pip install "marker-pdf[full]>=1.0.0"; \
    fi

# =============================================================================
# Stage 3: Models - Pre-download ML models (optional)
# =============================================================================
FROM marker-builder AS models

# Re-declare build arguments to use in this stage
ARG PRELOAD_DOCLING_MODELS
ARG PRELOAD_WHISPER_MODELS
ARG PRELOAD_VLM_MODELS
ARG PRELOAD_MARKER_MODELS

# Pre-download Docling models if requested
RUN if [ "$PRELOAD_DOCLING_MODELS" = "true" ]; then \
    uv run python -c "from docling.document_converter import DocumentConverter; DocumentConverter()" 2>/dev/null || true; \
    fi

# Pre-download Whisper models if requested
RUN if [ "$PRELOAD_WHISPER_MODELS" = "true" ]; then \
    uv run python -c "import whisper; whisper.load_model('base')" 2>/dev/null || true; \
    fi

# Pre-download Marker models if requested
RUN if [ "$PRELOAD_MARKER_MODELS" = "true" ]; then \
    uv run python -c "from marker.models import create_model_dict; create_model_dict()" 2>/dev/null || true; \
    fi

# =============================================================================
# Stage 4: Runtime - Final image
# =============================================================================
FROM python:3.11-slim AS runtime

# Re-declare build arguments to use in this stage
ARG INSTALL_MARKER
ARG INSTALL_CRAWL4AI

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For audio/video processing
    ffmpeg \
    # For document processing
    libmagic1 \
    # For healthcheck
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Marker runtime dependencies if needed
RUN if [ "$INSTALL_MARKER" = "true" ]; then \
    apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*; \
    fi

# Install Chromium runtime dependencies for Crawl4AI/Playwright
RUN if [ "$INSTALL_CRAWL4AI" = "true" ]; then \
    apt-get update && apt-get install -y --no-install-recommends \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
    && rm -rf /var/lib/apt/lists/*; \
    fi

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set up working directory
WORKDIR /app

# Copy virtual environment from models stage (includes all optional deps)
COPY --from=models /app/.venv /app/.venv

# Copy pre-downloaded models from models stage
COPY --from=models /root/.cache /home/appuser/.cache

# Copy application source
COPY src/ /app/src/

# Copy entrypoint script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set ownership
RUN chown -R appuser:appuser /app /home/appuser

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Playwright browsers path (for Crawl4AI)
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright \
    # Content Core settings
    CCORE_API_HOST=0.0.0.0 \
    CCORE_API_PORT=8000 \
    CCORE_UI_ENABLED=true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Entrypoint handles first-run setup (e.g., Playwright browsers)
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["uvicorn", "content_core.api:app", "--host", "0.0.0.0", "--port", "8000"]

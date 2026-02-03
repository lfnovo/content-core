"""Fallback executor for content extraction.

This module provides the FallbackExecutor class that executes extraction
with fallback chains, handling retries and fatal errors.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from content_core.common.exceptions import ExtractionError, FatalExtractionError
from content_core.engine_config.schema import FallbackConfig
from content_core.logging import logger
from content_core.processors import ProcessorRegistry
from content_core.processors.base import ProcessorResult, Source


class FallbackExecutor:
    """Executes content extraction with fallback chain support.

    This class handles:
    - Sequential execution of engine chain
    - Fatal error detection (non-retryable errors)
    - Configurable error handling (warn, fail, next)
    - Timeout management per engine
    """

    def __init__(self, config: FallbackConfig):
        """Initialize the executor.

        Args:
            config: Fallback configuration.
        """
        self.config = config
        self._registry: Optional[ProcessorRegistry] = None

    @property
    def registry(self) -> ProcessorRegistry:
        """Get the processor registry (lazy loaded)."""
        if self._registry is None:
            self._registry = ProcessorRegistry.instance()
        return self._registry

    def _is_fatal_error(self, error: Exception) -> bool:
        """Check if an error is fatal (should not trigger fallback).

        Args:
            error: The exception to check.

        Returns:
            True if the error is fatal and fallback should be skipped.
        """
        error_type = type(error).__name__

        # Always treat FatalExtractionError as fatal
        if isinstance(error, FatalExtractionError):
            return True

        # Check against configured fatal errors
        return error_type in self.config.fatal_errors

    async def execute(
        self,
        source: Source,
        engines: List[str],
        options: Optional[Dict[str, Any]] = None,
        engine_options: Optional[Dict[str, Dict[str, Any]]] = None,
        timeout: int = 300,
    ) -> ProcessorResult:
        """Execute extraction with fallback chain.

        Args:
            source: The Source to extract content from.
            engines: List of engine names to try in order.
            options: Global options passed to all engines.
            engine_options: Engine-specific options keyed by engine name.
            timeout: Timeout in seconds for each engine attempt.

        Returns:
            ProcessorResult from the first successful engine.

        Raises:
            FatalExtractionError: If a fatal error occurs.
            ExtractionError: If all engines fail.
        """
        if not self.config.enabled:
            # Fallback disabled - only try first engine
            engines = engines[:1]

        errors: List[Tuple[str, Exception]] = []
        attempts = min(len(engines), self.config.max_attempts)

        for i, engine_name in enumerate(engines[:attempts]):
            try:
                # Merge global options with engine-specific options
                merged_options = dict(options or {})
                if engine_options and engine_name in engine_options:
                    merged_options.update(engine_options[engine_name])

                result = await self._execute_single(
                    engine_name, source, merged_options, timeout
                )

                # Add warning if we fell back to this engine
                if i > 0:
                    failed_engines = [e[0] for e in errors]
                    result.warnings.append(
                        f"Used fallback engine '{engine_name}' after "
                        f"{failed_engines} failed"
                    )

                return result

            except Exception as e:
                # Check for fatal errors
                if self._is_fatal_error(e):
                    logger.error(f"Fatal error from engine '{engine_name}': {e}")
                    raise FatalExtractionError(
                        f"Fatal extraction error: {e}"
                    ) from e

                errors.append((engine_name, e))

                # Handle error based on configuration
                if self.config.on_error == "fail":
                    raise ExtractionError(
                        f"Engine '{engine_name}' failed: {e}"
                    ) from e
                elif self.config.on_error == "warn":
                    logger.warning(
                        f"Engine '{engine_name}' failed, trying next: {e}"
                    )
                    logger.debug(f"Full exception from '{engine_name}':", exc_info=True)
                # on_error == "next" - silent fallback
                else:
                    logger.debug(
                        f"Engine '{engine_name}' failed silently: {e}", exc_info=True
                    )

        # All engines failed
        error_summary = "; ".join(
            f"{name}: {type(err).__name__}: {err}" for name, err in errors
        )
        raise ExtractionError(
            f"All {len(errors)} engines failed: {error_summary}"
        )

    async def _execute_single(
        self,
        engine_name: str,
        source: Source,
        options: Optional[Dict[str, Any]],
        timeout: int,
    ) -> ProcessorResult:
        """Execute a single engine with timeout.

        Args:
            engine_name: The engine name to use.
            source: The Source to extract content from.
            options: Processor-specific options.
            timeout: Timeout in seconds.

        Returns:
            ProcessorResult from the engine.

        Raises:
            ValueError: If the engine is not found.
            asyncio.TimeoutError: If the engine times out.
            Exception: Any exception from the processor.
        """
        processor_cls = self.registry.get(engine_name)
        if not processor_cls:
            raise ValueError(
                f"Engine '{engine_name}' not found. "
                f"Available: {self.registry.list_names()}"
            )

        if not processor_cls.is_available():
            raise ValueError(
                f"Engine '{engine_name}' is not available "
                f"(missing dependencies: {processor_cls.capabilities.requires})"
            )

        logger.info(
            f"Extracting with engine '{engine_name}' "
            f"for MIME type '{source.mime_type}'"
        )

        processor = processor_cls()
        result = await asyncio.wait_for(
            processor.extract(source, options),
            timeout=timeout,
        )

        # Ensure engine_used is in metadata
        if "extraction_engine" not in result.metadata:
            result.metadata["extraction_engine"] = engine_name

        return result

"""Benchmark runner for document extraction engines."""

import asyncio
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BenchmarkResult, ContentAnalyzer, Engine, QualityScorer


class BenchmarkRunner:
    """Runs benchmarks for document extraction engines."""

    def __init__(
        self,
        engines: List[Engine],
        scorer: Optional[QualityScorer] = None,
        analyzer: Optional[ContentAnalyzer] = None,
    ):
        """Initialize the benchmark runner.

        Args:
            engines: List of engines to benchmark
            scorer: Optional quality scorer for measuring extraction accuracy
            analyzer: Optional content analyzer for extracting metrics
        """
        self.engines = engines
        self.scorer = scorer
        self.analyzer = analyzer

    async def run(
        self,
        files: List[Path],
        timeout_seconds: int = 600,
        options: Optional[Dict[str, Any]] = None,
        verbose: bool = True,
    ) -> Tuple[List[BenchmarkResult], Dict[str, Dict[str, str]]]:
        """Run benchmarks on all files with all engines.

        Args:
            files: List of files to benchmark
            timeout_seconds: Timeout per extraction
            options: Engine-specific options (e.g., describe_images)
            verbose: Print progress messages

        Returns:
            Tuple of (results list, outputs dict)
        """
        options = options or {}
        results: List[BenchmarkResult] = []
        outputs: Dict[str, Dict[str, str]] = {engine.name: {} for engine in self.engines}

        for file_path in files:
            if verbose:
                print(f"\nBenchmarking: {file_path.name}")
                print("-" * 50)

            for engine in self.engines:
                if not self._supports_file(engine, file_path):
                    continue

                result, content = await self._run_single(
                    engine, file_path, timeout_seconds, options, verbose
                )
                results.append(result)

                if content:
                    outputs[engine.name][file_path.name] = content

        return results, outputs

    def _supports_file(self, engine: Engine, file_path: Path) -> bool:
        """Check if engine supports the file type."""
        file_type = file_path.suffix.lstrip(".").lower()
        return engine.supports(file_type)

    def _get_file_type(self, file_path: Path) -> str:
        """Get file type from path."""
        return file_path.suffix.lstrip(".").lower()

    async def _run_single(
        self,
        engine: Engine,
        file_path: Path,
        timeout_seconds: int,
        options: Dict[str, Any],
        verbose: bool,
    ) -> Tuple[BenchmarkResult, str]:
        """Run a single benchmark for one engine on one file."""
        file_name = file_path.name
        file_type = self._get_file_type(file_path)

        engine_display = engine.name
        if options.get("describe_images") and hasattr(engine, "name") and "docling" in engine.name:
            engine_display = f"{engine.name} (describe_images)"

        if verbose:
            print(f"  Running {engine_display} on {file_name}...", end=" ", flush=True)

        # Start memory tracking
        tracemalloc.start()
        start_time = time.perf_counter()

        content = ""
        error = None

        try:
            content = await asyncio.wait_for(
                engine.extract(str(file_path), options),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            error = f"Timeout after {timeout_seconds}s"
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}"

        # Stop timing and memory tracking
        elapsed = time.perf_counter() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)

        # Analyze content
        metrics = self._analyze_content(content, file_name)

        result = BenchmarkResult(
            engine=engine.name,
            file=file_name,
            file_type=file_type,
            time_seconds=round(elapsed, 2),
            memory_peak_mb=round(peak_mb, 2),
            output_size_bytes=metrics["output_size_bytes"],
            output_lines=metrics["output_lines"],
            has_content=metrics["has_content"],
            error=error,
            quality_score=metrics.get("quality_score"),
            quality_found=metrics.get("quality_found"),
            quality_total=metrics.get("quality_total"),
            extra_metrics=metrics.get("extra_metrics", {}),
        )

        # Print status
        if verbose:
            if error:
                print(f"FAILED ({elapsed:.1f}s) - {error}")
            else:
                quality_str = ""
                if metrics.get("quality_score") is not None:
                    quality_str = f", quality={metrics['quality_score']:.0%}"
                print(
                    f"OK ({elapsed:.1f}s, {metrics['output_size_bytes'] / 1024:.1f}KB{quality_str})"
                )

        return result, content

    def _analyze_content(self, content: str, file_name: str) -> Dict[str, Any]:
        """Analyze content and return metrics."""
        if not content:
            return {
                "output_size_bytes": 0,
                "output_lines": 0,
                "has_content": False,
                "quality_score": None,
                "quality_found": None,
                "quality_total": None,
                "extra_metrics": {},
            }

        lines = content.split("\n")

        result = {
            "output_size_bytes": len(content.encode("utf-8")),
            "output_lines": len(lines),
            "has_content": len(content.strip()) > 0,
            "quality_score": None,
            "quality_found": None,
            "quality_total": None,
            "extra_metrics": {},
        }

        # Score quality if scorer is available
        if self.scorer:
            quality = self.scorer.score(content, file_name)
            if quality:
                result["quality_score"] = round(quality.score, 3)
                result["quality_found"] = quality.found
                result["quality_total"] = quality.total

        # Analyze content if analyzer is available
        if self.analyzer:
            result["extra_metrics"] = self.analyzer.analyze(content)

        return result

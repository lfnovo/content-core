"""Report generator for benchmark results."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .base import BenchmarkResult


class ReportGenerator:
    """Generates reports from benchmark results."""

    def __init__(self, file_type: str = "document"):
        """Initialize the report generator.

        Args:
            file_type: Type of files being benchmarked (e.g., "pdf", "docx")
        """
        self.file_type = file_type

    def generate_markdown(
        self,
        results: List[BenchmarkResult],
        engines: List[str],
        files: List[Path],
    ) -> str:
        """Generate markdown report from benchmark results."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_type_upper = self.file_type.upper()

        report = f"""# {file_type_upper} Extraction Benchmark Results

**Date:** {now}
**Files tested:** {len(files)}
**Engines tested:** {', '.join(engines)}

## Summary

| Engine | Avg Time | Peak Memory | Avg Size | Success Rate |
|--------|----------|-------------|----------|--------------|
"""

        # Calculate summary stats per engine
        for engine in engines:
            engine_results = [r for r in results if r.engine == engine]
            successful = [r for r in engine_results if r.error is None]

            if successful:
                avg_time = sum(r.time_seconds for r in successful) / len(successful)
                max_memory = max(r.memory_peak_mb for r in successful)
                avg_size = sum(r.output_size_bytes for r in successful) / len(successful)
            else:
                avg_time = 0
                max_memory = 0
                avg_size = 0

            success_rate = len(successful) / len(engine_results) * 100 if engine_results else 0

            report += (
                f"| {engine} | {avg_time:.1f}s | {max_memory:.0f}MB | "
                f"{avg_size/1024:.1f}KB | {success_rate:.0f}% |\n"
            )

        # Check if any results have quality scores
        has_quality_scores = any(r.quality_score is not None for r in results)

        if has_quality_scores:
            report += f"\n## Quality Scores (benchmark.{self.file_type})\n\n"
            report += "| Engine | Quality | Found/Total | Time | Status |\n"
            report += "|--------|---------|-------------|------|--------|\n"

            quality_results = [r for r in results if r.quality_score is not None]
            for r in sorted(quality_results, key=lambda x: x.quality_score or 0, reverse=True):
                status = "OK" if r.error is None else "FAILED"
                report += (
                    f"| {r.engine} | **{r.quality_score:.0%}** | {r.quality_found}/{r.quality_total} | "
                    f"{r.time_seconds:.1f}s | {status} |\n"
                )

            report += "\n"

        report += "## Per-File Results\n\n"

        # Per-file results
        for file_path in files:
            file_name = file_path.name
            file_results = [r for r in results if r.file == file_name]

            if not file_results:
                continue

            report += f"### {file_name}\n\n"

            # Check if this is a benchmark file with quality scores
            is_benchmark_file = any(r.quality_score is not None for r in file_results)
            has_extra_metrics = any(r.extra_metrics for r in file_results)

            if is_benchmark_file:
                report += "| Engine | Time | Memory | Size | Quality | Status |\n"
                report += "|--------|------|--------|------|---------|--------|\n"
                for r in file_results:
                    status = "OK" if r.error is None else f"FAILED: {r.error[:30]}"
                    quality = f"{r.quality_score:.0%}" if r.quality_score is not None else "N/A"
                    report += (
                        f"| {r.engine} | {r.time_seconds:.1f}s | {r.memory_peak_mb:.0f}MB | "
                        f"{r.output_size_bytes/1024:.1f}KB | {quality} | {status} |\n"
                    )
            elif has_extra_metrics:
                # Build header dynamically from extra_metrics
                metric_keys = []
                for r in file_results:
                    if r.extra_metrics:
                        metric_keys = list(r.extra_metrics.keys())
                        break

                header = "| Engine | Time | Memory | Size | Lines |"
                separator = "|--------|------|--------|------|-------|"
                for key in metric_keys:
                    header += f" {key.replace('_', ' ').title()} |"
                    separator += "------|"
                header += " Status |"
                separator += "--------|"

                report += header + "\n"
                report += separator + "\n"

                for r in file_results:
                    status = "OK" if r.error is None else f"FAILED: {r.error[:30]}"
                    row = (
                        f"| {r.engine} | {r.time_seconds:.1f}s | {r.memory_peak_mb:.0f}MB | "
                        f"{r.output_size_bytes/1024:.1f}KB | {r.output_lines} |"
                    )
                    for key in metric_keys:
                        value = r.extra_metrics.get(key, 0) if r.extra_metrics else 0
                        row += f" {value} |"
                    row += f" {status} |"
                    report += row + "\n"
            else:
                report += "| Engine | Time | Memory | Size | Lines | Status |\n"
                report += "|--------|------|--------|------|-------|--------|\n"
                for r in file_results:
                    status = "OK" if r.error is None else f"FAILED: {r.error[:30]}"
                    report += (
                        f"| {r.engine} | {r.time_seconds:.1f}s | {r.memory_peak_mb:.0f}MB | "
                        f"{r.output_size_bytes/1024:.1f}KB | {r.output_lines} | {status} |\n"
                    )

            report += "\n"

        return report

    def save_results(
        self,
        results: List[BenchmarkResult],
        outputs: Dict[str, Dict[str, str]],
        engines: List[str],
        files: List[Path],
        output_dir: Path,
    ) -> None:
        """Save benchmark results to disk.

        Args:
            results: List of benchmark results
            outputs: Dict mapping engine names to file outputs
            engines: List of engine names
            files: List of file paths
            output_dir: Directory to save results
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON results
        json_path = output_dir / "results.json"
        with open(json_path, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "file_type": self.file_type,
                    "engines": engines,
                    "files": [f.name for f in files],
                    "results": [asdict(r) for r in results],
                },
                f,
                indent=2,
            )
        print(f"Saved: {json_path}")

        # Save markdown report
        md_path = output_dir / "results.md"
        report = self.generate_markdown(results, engines, files)
        with open(md_path, "w") as f:
            f.write(report)
        print(f"Saved: {md_path}")

        # Save individual outputs
        outputs_dir = output_dir / "outputs"
        for engine, file_outputs in outputs.items():
            engine_dir = outputs_dir / engine
            engine_dir.mkdir(parents=True, exist_ok=True)

            for file_name, content in file_outputs.items():
                # Replace original extension with .md
                output_name = Path(file_name).stem + ".md"
                output_path = engine_dir / output_name
                with open(output_path, "w") as f:
                    f.write(content)

        if any(outputs.values()):
            print(f"Saved outputs to: {outputs_dir}")

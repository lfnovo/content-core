#!/usr/bin/env python
"""
PDF Extraction Benchmark for content-core.

Compares performance and output quality of different PDF extraction engines.

Usage:
    uv run python scripts/benchmark_pdf_engines.py [--engines ENGINE,...] [--files FILE,...]

Examples:
    uv run python scripts/benchmark_pdf_engines.py
    uv run python scripts/benchmark_pdf_engines.py --engines pymupdf4llm,docling
    uv run python scripts/benchmark_pdf_engines.py --files 2601.20958v1.pdf
    uv run python scripts/benchmark_pdf_engines.py --timeout 300
"""

import argparse
import asyncio
import json
import os
import re
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Default test files directory
TEST_INPUT_DIR = Path(__file__).parent.parent / "tests" / "input_content"
OUTPUT_BASE_DIR = Path(__file__).parent.parent / "tests" / "output"

# Available engines
AVAILABLE_ENGINES = ["pymupdf4llm", "docling", "docling-vlm"]


@dataclass
class BenchmarkResult:
    """Results from benchmarking a single engine on a single file."""

    engine: str
    file: str

    # Performance
    time_seconds: float
    memory_peak_mb: float

    # Output
    output_size_bytes: int
    output_lines: int

    # Structure counts (automatic detection)
    headers_count: int
    tables_count: int
    formulas_count: int

    # Validation
    first_line: str
    has_content: bool
    error: Optional[str] = None


def count_headers(content: str) -> int:
    """Count markdown headers (## style)."""
    return len(re.findall(r"^#{1,6}\s+.+$", content, re.MULTILINE))


def count_tables(content: str) -> int:
    """Count markdown tables (lines starting with |)."""
    table_rows = re.findall(r"^\|.+\|$", content, re.MULTILINE)
    # Group consecutive table rows (approximate table count)
    if not table_rows:
        return 0
    # Count separator rows as table indicators
    separators = len(re.findall(r"^\|[\s\-:|]+\|$", content, re.MULTILINE))
    return max(separators, 1) if table_rows else 0


def count_formulas(content: str) -> int:
    """Count LaTeX formulas ($$ or $ delimited)."""
    # Block formulas
    block_formulas = len(re.findall(r"\$\$[^$]+\$\$", content))
    # Inline formulas (avoiding $$)
    inline_formulas = len(re.findall(r"(?<!\$)\$(?!\$)[^$]+\$(?!\$)", content))
    return block_formulas + inline_formulas


def analyze_content(content: str) -> Dict:
    """Analyze content and return metrics."""
    lines = content.split("\n")
    first_line = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            first_line = stripped[:100]  # Truncate for display
            break

    return {
        "output_size_bytes": len(content.encode("utf-8")),
        "output_lines": len(lines),
        "headers_count": count_headers(content),
        "tables_count": count_tables(content),
        "formulas_count": count_formulas(content),
        "first_line": first_line,
        "has_content": len(content.strip()) > 0,
    }


# --- Engine Implementations ---


def benchmark_pymupdf4llm(file_path: str) -> str:
    """Extract PDF using pymupdf4llm."""
    import pymupdf4llm

    return pymupdf4llm.to_markdown(file_path, page_chunks=False, write_images=False)


async def benchmark_docling(file_path: str) -> str:
    """Extract PDF using docling via content-core."""
    from content_core.common.state import ProcessSourceState
    from content_core.processors.docling import extract_with_docling

    state = ProcessSourceState(file_path=file_path)
    result = await extract_with_docling(state)
    return result.content


async def benchmark_docling_vlm(file_path: str) -> str:
    """Extract PDF using docling-vlm via content-core."""
    from content_core.common.state import ProcessSourceState
    from content_core.processors.docling_vlm import extract_with_docling_vlm

    state = ProcessSourceState(file_path=file_path, vlm_inference_mode="local")
    result = await extract_with_docling_vlm(state)
    return result["content"]


# --- Benchmark Runner ---


async def run_single_benchmark(
    engine: str,
    file_path: Path,
    timeout_seconds: int = 600,
) -> BenchmarkResult:
    """Run a single benchmark for one engine on one file."""
    file_name = file_path.name

    print(f"  Running {engine} on {file_name}...", end=" ", flush=True)

    # Start memory tracking
    tracemalloc.start()
    start_time = time.perf_counter()

    content = ""
    error = None

    try:
        if engine == "pymupdf4llm":
            # Sync function, run in executor
            loop = asyncio.get_event_loop()
            content = await asyncio.wait_for(
                loop.run_in_executor(None, benchmark_pymupdf4llm, str(file_path)),
                timeout=timeout_seconds,
            )
        elif engine == "docling":
            content = await asyncio.wait_for(
                benchmark_docling(str(file_path)),
                timeout=timeout_seconds,
            )
        elif engine == "docling-vlm":
            content = await asyncio.wait_for(
                benchmark_docling_vlm(str(file_path)),
                timeout=timeout_seconds,
            )
        else:
            raise ValueError(f"Unknown engine: {engine}")

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
    metrics = analyze_content(content) if content else {
        "output_size_bytes": 0,
        "output_lines": 0,
        "headers_count": 0,
        "tables_count": 0,
        "formulas_count": 0,
        "first_line": "",
        "has_content": False,
    }

    result = BenchmarkResult(
        engine=engine,
        file=file_name,
        time_seconds=round(elapsed, 2),
        memory_peak_mb=round(peak_mb, 2),
        error=error,
        **metrics,
    )

    # Print status
    if error:
        print(f"FAILED ({elapsed:.1f}s) - {error}")
    else:
        print(f"OK ({elapsed:.1f}s, {metrics['output_size_bytes'] / 1024:.1f}KB)")

    return result, content


async def run_benchmarks(
    engines: List[str],
    files: List[Path],
    timeout_seconds: int,
) -> tuple[List[BenchmarkResult], Dict[str, Dict[str, str]]]:
    """Run all benchmarks and return results with outputs."""
    results = []
    outputs: Dict[str, Dict[str, str]] = {engine: {} for engine in engines}

    for file_path in files:
        print(f"\nBenchmarking: {file_path.name}")
        print("-" * 50)

        for engine in engines:
            result, content = await run_single_benchmark(
                engine, file_path, timeout_seconds
            )
            results.append(result)
            if content:
                outputs[engine][file_path.name] = content

    return results, outputs


def generate_markdown_report(
    results: List[BenchmarkResult],
    engines: List[str],
    files: List[Path],
) -> str:
    """Generate markdown report from benchmark results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# PDF Extraction Benchmark Results

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

        report += f"| {engine} | {avg_time:.1f}s | {max_memory:.0f}MB | {avg_size/1024:.1f}KB | {success_rate:.0f}% |\n"

    report += "\n## Per-File Results\n\n"

    # Per-file results
    for file_path in files:
        file_name = file_path.name
        file_results = [r for r in results if r.file == file_name]

        report += f"### {file_name}\n\n"
        report += "| Engine | Time | Memory | Size | Lines | Headers | Tables | Formulas | Status |\n"
        report += "|--------|------|--------|------|-------|---------|--------|----------|--------|\n"

        for r in file_results:
            status = "✅" if r.error is None else f"❌ {r.error[:30]}"
            report += (
                f"| {r.engine} | {r.time_seconds:.1f}s | {r.memory_peak_mb:.0f}MB | "
                f"{r.output_size_bytes/1024:.1f}KB | {r.output_lines} | "
                f"{r.headers_count} | {r.tables_count} | {r.formulas_count} | {status} |\n"
            )

        report += "\n"

    report += """## Structure Detection Notes

- **Headers**: Markdown headers (`#`, `##`, etc.)
- **Tables**: Markdown tables (pipe-delimited rows)
- **Formulas**: LaTeX formulas (`$...$` or `$$...$$`)

## Engine Details

- **pymupdf4llm**: Fast, lightweight, uses PyMuPDF for text extraction
- **docling**: Document understanding with OCR and table detection
- **docling-vlm**: Vision-Language Model for complex document layouts
"""

    return report


def save_results(
    results: List[BenchmarkResult],
    outputs: Dict[str, Dict[str, str]],
    engines: List[str],
    files: List[Path],
    output_dir: Path,
):
    """Save benchmark results to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON results
    json_path = output_dir / "results.json"
    with open(json_path, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
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
    report = generate_markdown_report(results, engines, files)
    with open(md_path, "w") as f:
        f.write(report)
    print(f"Saved: {md_path}")

    # Save individual outputs
    outputs_dir = output_dir / "outputs"
    for engine, file_outputs in outputs.items():
        engine_dir = outputs_dir / engine
        engine_dir.mkdir(parents=True, exist_ok=True)

        for file_name, content in file_outputs.items():
            # Replace .pdf extension with .md
            output_name = Path(file_name).stem + ".md"
            output_path = engine_dir / output_name
            with open(output_path, "w") as f:
                f.write(content)

    if any(outputs.values()):
        print(f"Saved outputs to: {outputs_dir}")


def find_pdf_files(test_dir: Path, file_names: Optional[List[str]] = None) -> List[Path]:
    """Find PDF files to benchmark."""
    all_pdfs = sorted(test_dir.glob("*.pdf"))

    if file_names:
        # Filter to specified files
        filtered = []
        for name in file_names:
            matches = [p for p in all_pdfs if p.name == name or p.stem == name]
            if matches:
                filtered.extend(matches)
            else:
                print(f"Warning: File not found: {name}")
        return filtered

    return all_pdfs


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark PDF extraction engines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run all engines on all PDFs
  %(prog)s --engines pymupdf4llm,docling      # Only test specific engines
  %(prog)s --files 2601.20958v1.pdf           # Only test specific file
  %(prog)s --timeout 300                      # Set 5 minute timeout
        """,
    )
    parser.add_argument(
        "--engines",
        type=str,
        default=",".join(AVAILABLE_ENGINES),
        help=f"Comma-separated list of engines (default: {','.join(AVAILABLE_ENGINES)})",
    )
    parser.add_argument(
        "--files",
        type=str,
        default=None,
        help="Comma-separated list of PDF files to test (default: all in tests/input_content/)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds per extraction (default: 600)",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=str(TEST_INPUT_DIR),
        help=f"Input directory for PDF files (default: {TEST_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: tests/output/benchmark_TIMESTAMP)",
    )

    args = parser.parse_args()

    # Parse engines
    engines = [e.strip() for e in args.engines.split(",")]
    invalid_engines = [e for e in engines if e not in AVAILABLE_ENGINES]
    if invalid_engines:
        print(f"Error: Unknown engines: {invalid_engines}")
        print(f"Available engines: {AVAILABLE_ENGINES}")
        return 1

    # Find PDF files
    input_dir = Path(args.input_dir)
    file_names = args.files.split(",") if args.files else None
    pdf_files = find_pdf_files(input_dir, file_names)

    if not pdf_files:
        print(f"Error: No PDF files found in {input_dir}")
        return 1

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_BASE_DIR / f"benchmark_{timestamp}"

    print("=" * 60)
    print("PDF Extraction Benchmark")
    print("=" * 60)
    print(f"Engines: {', '.join(engines)}")
    print(f"Files: {len(pdf_files)}")
    for f in pdf_files:
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.1f} KB)")
    print(f"Timeout: {args.timeout}s per extraction")
    print(f"Output: {output_dir}")

    # Run benchmarks
    results, outputs = asyncio.run(
        run_benchmarks(engines, pdf_files, args.timeout)
    )

    # Save results
    print("\n" + "=" * 60)
    print("Saving results...")
    save_results(results, outputs, engines, pdf_files, output_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(generate_markdown_report(results, engines, pdf_files))

    return 0


if __name__ == "__main__":
    exit(main())

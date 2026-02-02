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
    uv run python scripts/benchmark_pdf_engines.py --engines docling --describe-images

Engines:
    - pymupdf4llm: Fast, lightweight extraction using PyMuPDF. Best for simple documents.
    - docling: Standard docling pipeline with OCR and table detection.
    - docling-vlm: Vision-Language Model (granite-docling) for complex document layouts.

Picture Description (--describe-images):
    Enables VLM-based image captioning using SmolVLM-256M-Instruct model.

    IMPORTANT FINDINGS:
    1. Use with 'docling' engine, NOT 'docling-vlm'. The VlmPipeline does not
       properly support picture description enrichment.
       See: https://github.com/docling-project/docling/discussions/2434

    2. MPS (Apple Silicon GPU) produces garbage output with SmolVLM/Granite Vision.
       This script forces CPU inference for picture descriptions as a workaround.

    3. Descriptions are stored in pic.meta.description.text but the markdown export
       shows <!-- image --> by default. Access descriptions via the document model.

    4. CPU inference is slower (~100s vs ~25s) but produces correct results.

    Example output with --describe-images:
        Description: "The image is a line graph titled 'Trigonometric Functions.'
        The graph shows a downward trend, with the y-axis increasing..."
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
class QualityScore:
    """Quality metrics for extraction accuracy."""

    score: float  # 0.0 to 1.0
    found: int  # Number of expected elements found
    total: int  # Total expected elements
    details: Dict[str, bool]  # Which elements were found


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

    # Quality score (for files with known content)
    quality_score: Optional[float] = None
    quality_found: Optional[int] = None
    quality_total: Optional[int] = None


# Expected content for benchmark.pdf (our synthetic test file)
BENCHMARK_PDF_EXPECTED = {
    "title": "Benchmark Document for PDF Extraction",
    "sections": [
        "Introduction",
        "Mathematical Formulas",
        "Data Table",
        "Figure",
        "Conclusion",
        "References",
    ],
    "subsections": [
        "Famous Equations",
        "LaTeX Block Formula",
    ],
    "formulas": [
        "E = mc",  # E = mc^2 (partial match)
        "e^(i",  # Euler's identity (partial)
        "a^2 + b^2",  # Pythagorean
        "sqrt(b^2",  # Quadratic formula (partial)
    ],
    "table_data": [
        "Quick Sort",
        "Merge Sort",
        "Bubble Sort",
        "Neural Net",
        "45.2",  # Quick Sort time
        "98.7",  # Neural Net accuracy (unique value)
    ],
    "figure": [
        "Figure 1",
        "sin(x)",
        "cos(x)",
    ],
}


def score_benchmark_pdf(content: str) -> QualityScore:
    """Score extraction quality against expected benchmark.pdf content."""
    content_lower = content.lower()
    details = {}

    # Check title
    details["title"] = BENCHMARK_PDF_EXPECTED["title"].lower() in content_lower

    # Check sections
    for section in BENCHMARK_PDF_EXPECTED["sections"]:
        key = f"section_{section.lower().replace(' ', '_')}"
        details[key] = section.lower() in content_lower

    # Check subsections
    for subsection in BENCHMARK_PDF_EXPECTED["subsections"]:
        key = f"subsection_{subsection.lower().replace(' ', '_')}"
        details[key] = subsection.lower() in content_lower

    # Check formulas (case-sensitive for math)
    for formula in BENCHMARK_PDF_EXPECTED["formulas"]:
        key = f"formula_{formula[:10].replace(' ', '_')}"
        details[key] = formula in content

    # Check table data
    for data in BENCHMARK_PDF_EXPECTED["table_data"]:
        key = f"table_{data.lower().replace(' ', '_')}"
        details[key] = data.lower() in content_lower

    # Check figure references
    for fig in BENCHMARK_PDF_EXPECTED["figure"]:
        key = f"figure_{fig.lower().replace(' ', '_')}"
        details[key] = fig.lower() in content_lower

    found = sum(1 for v in details.values() if v)
    total = len(details)
    score = found / total if total > 0 else 0.0

    return QualityScore(score=score, found=found, total=total, details=details)


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


def analyze_content(content: str, file_name: str = "") -> Dict:
    """Analyze content and return metrics."""
    lines = content.split("\n")
    first_line = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            first_line = stripped[:100]  # Truncate for display
            break

    result = {
        "output_size_bytes": len(content.encode("utf-8")),
        "output_lines": len(lines),
        "headers_count": count_headers(content),
        "tables_count": count_tables(content),
        "formulas_count": count_formulas(content),
        "first_line": first_line,
        "has_content": len(content.strip()) > 0,
        "quality_score": None,
        "quality_found": None,
        "quality_total": None,
    }

    # Score quality for benchmark.pdf
    if file_name == "benchmark.pdf":
        quality = score_benchmark_pdf(content)
        result["quality_score"] = round(quality.score, 3)
        result["quality_found"] = quality.found
        result["quality_total"] = quality.total

    return result


# --- Engine Implementations ---


def benchmark_pymupdf4llm(file_path: str) -> str:
    """Extract PDF using pymupdf4llm."""
    import pymupdf4llm

    return pymupdf4llm.to_markdown(file_path, page_chunks=False, write_images=False)


async def benchmark_docling(file_path: str, describe_images: bool = False) -> str:
    """Extract PDF using docling standard pipeline.

    When describe_images=True, enables VLM-based picture description using
    the SmolVLM-256M-Instruct model. This is the recommended approach for
    image descriptions as per docling documentation.

    Note: Picture description uses CPU device because the SmolVLM model
    produces incorrect output with MPS (Apple Silicon GPU).
    """
    import asyncio
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        smolvlm_picture_description,
    )
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()

    # Enable image description if requested
    # Uses SmolVLM-256M-Instruct for describing images found in the document
    # See: https://docling-project.github.io/docling/examples/pictures_description/
    if describe_images:
        pipeline_options.do_picture_description = True
        pipeline_options.generate_picture_images = True
        pipeline_options.images_scale = 2.0  # Higher resolution for better descriptions
        pipeline_options.picture_description_options = smolvlm_picture_description
        # Use CPU for picture description - MPS produces incorrect output with SmolVLM
        pipeline_options.accelerator_options = AcceleratorOptions(device='cpu')

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    # Run in executor to avoid blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, converter.convert, file_path)

    doc = result.document
    return doc.export_to_markdown()


async def benchmark_docling_vlm(file_path: str, describe_images: bool = False) -> str:
    """Extract PDF using docling VLM pipeline (granite-docling model).

    The VLM pipeline uses a vision-language model for document structure
    understanding. This is different from picture description which is
    an enrichment step available on the standard pipeline.

    Note: Picture description with VlmPipeline is not fully supported.
    Use --describe-images with the 'docling' engine instead for best results.
    See: https://github.com/docling-project/docling/discussions/2434
    """
    import asyncio
    from docling.datamodel.pipeline_options import VlmPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.pipeline.vlm_pipeline import VlmPipeline
    from docling.datamodel import vlm_model_specs

    model_spec = vlm_model_specs.GRANITEDOCLING_MLX
    pipeline_options = VlmPipelineOptions(vlm_options=model_spec)

    # Note: Picture description is not well-supported with VlmPipeline.
    # The options below are kept for testing purposes but may not produce
    # meaningful descriptions. Use the 'docling' engine with --describe-images
    # for proper picture descriptions.
    if describe_images:
        from docling.datamodel.pipeline_options import smolvlm_picture_description
        pipeline_options.do_picture_description = True
        pipeline_options.generate_picture_images = True
        pipeline_options.picture_description_options = smolvlm_picture_description

    converter = DocumentConverter(
        format_options={
            "pdf": PdfFormatOption(pipeline_cls=VlmPipeline, pipeline_options=pipeline_options)
        }
    )

    # Run in executor to avoid blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, converter.convert, file_path)

    doc = result.document
    return doc.export_to_markdown()


# --- Benchmark Runner ---


async def run_single_benchmark(
    engine: str,
    file_path: Path,
    timeout_seconds: int = 600,
    describe_images: bool = False,
) -> BenchmarkResult:
    """Run a single benchmark for one engine on one file."""
    file_name = file_path.name

    engine_display = engine
    if describe_images and engine in ("docling", "docling-vlm"):
        engine_display = f"{engine} (describe_images)"

    print(f"  Running {engine_display} on {file_name}...", end=" ", flush=True)

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
                benchmark_docling(str(file_path), describe_images=describe_images),
                timeout=timeout_seconds,
            )
        elif engine == "docling-vlm":
            content = await asyncio.wait_for(
                benchmark_docling_vlm(str(file_path), describe_images=describe_images),
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
    metrics = analyze_content(content, file_name) if content else {
        "output_size_bytes": 0,
        "output_lines": 0,
        "headers_count": 0,
        "tables_count": 0,
        "formulas_count": 0,
        "first_line": "",
        "has_content": False,
        "quality_score": None,
        "quality_found": None,
        "quality_total": None,
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
        quality_str = ""
        if metrics.get("quality_score") is not None:
            quality_str = f", quality={metrics['quality_score']:.0%}"
        print(f"OK ({elapsed:.1f}s, {metrics['output_size_bytes'] / 1024:.1f}KB{quality_str})")

    return result, content


async def run_benchmarks(
    engines: List[str],
    files: List[Path],
    timeout_seconds: int,
    describe_images: bool = False,
) -> tuple[List[BenchmarkResult], Dict[str, Dict[str, str]]]:
    """Run all benchmarks and return results with outputs."""
    results = []
    outputs: Dict[str, Dict[str, str]] = {engine: {} for engine in engines}

    for file_path in files:
        print(f"\nBenchmarking: {file_path.name}")
        print("-" * 50)

        for engine in engines:
            result, content = await run_single_benchmark(
                engine, file_path, timeout_seconds, describe_images=describe_images
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

    # Check if any results have quality scores
    has_quality_scores = any(r.quality_score is not None for r in results)

    if has_quality_scores:
        report += "\n## Quality Scores (benchmark.pdf)\n\n"
        report += "| Engine | Quality | Found/Total | Time | Status |\n"
        report += "|--------|---------|-------------|------|--------|\n"

        quality_results = [r for r in results if r.quality_score is not None]
        for r in sorted(quality_results, key=lambda x: x.quality_score or 0, reverse=True):
            status = "✅" if r.error is None else f"❌"
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

        report += f"### {file_name}\n\n"

        # Include Quality column for benchmark.pdf
        if file_name == "benchmark.pdf":
            report += "| Engine | Time | Memory | Size | Headers | Tables | Quality | Status |\n"
            report += "|--------|------|--------|------|---------|--------|---------|--------|\n"
            for r in file_results:
                status = "✅" if r.error is None else f"❌ {r.error[:30]}"
                quality = f"{r.quality_score:.0%}" if r.quality_score is not None else "N/A"
                report += (
                    f"| {r.engine} | {r.time_seconds:.1f}s | {r.memory_peak_mb:.0f}MB | "
                    f"{r.output_size_bytes/1024:.1f}KB | {r.headers_count} | "
                    f"{r.tables_count} | {quality} | {status} |\n"
                )
        else:
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
  %(prog)s --engines docling --describe-images  # With image descriptions

Notes on --describe-images:
  - Best used with 'docling' engine (not 'docling-vlm')
  - Uses SmolVLM-256M-Instruct model for image captioning
  - Forces CPU inference (MPS produces incorrect output)
  - Slower (~100s vs ~25s) but generates accurate descriptions
  - Descriptions stored in document model, not in markdown export
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
    parser.add_argument(
        "--describe-images",
        action="store_true",
        help=(
            "Enable VLM-based image descriptions (recommended with 'docling' engine). "
            "Uses SmolVLM-256M on CPU. Slower but generates accurate captions."
        ),
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
    if args.describe_images:
        print("Image description: ENABLED (SmolVLM-256M on CPU, best with 'docling' engine)")
    print(f"Output: {output_dir}")

    # Run benchmarks
    results, outputs = asyncio.run(
        run_benchmarks(engines, pdf_files, args.timeout, describe_images=args.describe_images)
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

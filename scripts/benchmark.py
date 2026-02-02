#!/usr/bin/env python
"""
Document Extraction Benchmark for content-core.

Compares performance and output quality of different extraction engines
for various document types (PDF, DOCX).

Usage:
    uv run python scripts/benchmark.py [--type TYPE] [--engines ENGINE,...] [--files FILE,...]

Examples:
    uv run python scripts/benchmark.py                           # Run all engines on all files
    uv run python scripts/benchmark.py --type pdf                # Only PDF files
    uv run python scripts/benchmark.py --type docx               # Only DOCX files
    uv run python scripts/benchmark.py --type pdf --engines docling,pymupdf4llm
    uv run python scripts/benchmark.py --files benchmark.pdf,benchmark.docx
    uv run python scripts/benchmark.py --type pdf --describe-images

Supported Types:
    - pdf: PDF documents
    - docx: Microsoft Word documents
    - all: All supported document types (default)

PDF Engines:
    - simple: Basic PyMuPDF text extraction without markdown formatting.
    - pymupdf4llm: Fast, lightweight extraction using PyMuPDF.
    - marker: Deep learning-based extraction for high-quality markdown.
    - docling: Standard docling pipeline with OCR and table detection.
    - docling-vlm: Vision-Language Model for complex document layouts.
    - docling-serve: Remote extraction via docling-serve API.

DOCX Engines:
    - python-docx: Basic python-docx extraction.
    - docling: Docling extraction for best quality.

Remote Engines:
    For docling-serve, provide the server URL:
    uv run python scripts/benchmark.py --type pdf --engines docling-serve --docling-serve-url http://server:5001
"""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Default directories
TEST_INPUT_DIR = Path(__file__).parent.parent / "tests" / "input_content"
OUTPUT_BASE_DIR = Path(__file__).parent.parent / "tests" / "output"


def get_engines_for_type(
    file_type: str,
    engine_names: Optional[List[str]] = None,
    docling_serve_url: Optional[str] = None,
):
    """Get engines for the specified file type."""
    from benchmarks.types.pdf import AVAILABLE_PDF_ENGINES, get_pdf_engines
    from benchmarks.types.docx import AVAILABLE_DOCX_ENGINES, get_docx_engines

    if file_type == "pdf":
        if engine_names:
            # Filter to only valid PDF engines
            valid_names = [n for n in engine_names if n in AVAILABLE_PDF_ENGINES]
            if not valid_names:
                raise ValueError(
                    f"No valid PDF engines in: {engine_names}. Available: {AVAILABLE_PDF_ENGINES}"
                )
            return get_pdf_engines(valid_names, docling_serve_url=docling_serve_url)
        return get_pdf_engines(docling_serve_url=docling_serve_url)
    elif file_type == "docx":
        if engine_names:
            # Filter to only valid DOCX engines
            valid_names = [n for n in engine_names if n in AVAILABLE_DOCX_ENGINES]
            if not valid_names:
                raise ValueError(
                    f"No valid DOCX engines in: {engine_names}. Available: {AVAILABLE_DOCX_ENGINES}"
                )
            return get_docx_engines(valid_names)
        return get_docx_engines()
    else:
        raise ValueError(f"Unknown file type: {file_type}")


def get_scorer_for_type(file_type: str):
    """Get quality scorer for the specified file type."""
    from benchmarks.types.pdf import PDFQualityScorer
    from benchmarks.types.docx import DOCXQualityScorer

    if file_type == "pdf":
        return PDFQualityScorer()
    elif file_type == "docx":
        return DOCXQualityScorer()
    return None


def get_analyzer_for_type(file_type: str):
    """Get content analyzer for the specified file type."""
    from benchmarks.types.pdf import MarkdownAnalyzer
    from benchmarks.types.docx import DOCXContentAnalyzer

    if file_type == "pdf":
        return MarkdownAnalyzer()
    elif file_type == "docx":
        return DOCXContentAnalyzer()
    return None


def find_files(test_dir: Path, file_type: str, file_names: Optional[List[str]] = None) -> List[Path]:
    """Find files to benchmark."""
    if file_type == "all":
        patterns = ["*.pdf", "*.docx"]
    else:
        patterns = [f"*.{file_type}"]

    all_files = []
    for pattern in patterns:
        all_files.extend(sorted(test_dir.glob(pattern)))

    if file_names:
        # Filter to specified files
        filtered = []
        for name in file_names:
            matches = [p for p in all_files if p.name == name or p.stem == name]
            if matches:
                filtered.extend(matches)
            else:
                print(f"Warning: File not found: {name}")
        return filtered

    return all_files


async def run_benchmark_for_type(
    file_type: str,
    files: List[Path],
    engine_names: Optional[List[str]],
    timeout_seconds: int,
    options: dict,
    output_dir: Path,
    docling_serve_url: Optional[str] = None,
    verbose: bool = True,
):
    """Run benchmark for a specific file type."""
    from benchmarks.runner import BenchmarkRunner
    from benchmarks.reporter import ReportGenerator

    # Filter files for this type
    type_files = [f for f in files if f.suffix.lstrip(".").lower() == file_type]
    if not type_files:
        if verbose:
            print(f"\nNo {file_type.upper()} files to benchmark.")
        return [], {}

    engines = get_engines_for_type(file_type, engine_names, docling_serve_url=docling_serve_url)
    scorer = get_scorer_for_type(file_type)
    analyzer = get_analyzer_for_type(file_type)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"{file_type.upper()} Extraction Benchmark")
        print(f"{'=' * 60}")
        print(f"Engines: {', '.join(e.name for e in engines)}")
        print(f"Files: {len(type_files)}")
        for f in type_files:
            size_kb = f.stat().st_size / 1024
            print(f"  - {f.name} ({size_kb:.1f} KB)")

    runner = BenchmarkRunner(engines, scorer, analyzer)
    results, outputs = await runner.run(type_files, timeout_seconds, options, verbose)

    # Save results
    type_output_dir = output_dir / file_type
    reporter = ReportGenerator(file_type)

    if verbose:
        print(f"\nSaving {file_type.upper()} results...")

    reporter.save_results(
        results, outputs, [e.name for e in engines], type_files, type_output_dir
    )

    # Print summary
    if verbose:
        print(f"\n{file_type.upper()} Summary:")
        print(reporter.generate_markdown(results, [e.name for e in engines], type_files))

    return results, outputs


async def main_async(args):
    """Main async entry point."""
    # Parse engine names
    engine_names = None
    if args.engines:
        engine_names = [e.strip() for e in args.engines.split(",")]

    # Parse file names
    file_names = None
    if args.files:
        file_names = [f.strip() for f in args.files.split(",")]

    # Find all files first
    input_dir = Path(args.input_dir)
    all_files = find_files(input_dir, args.type, file_names)

    if not all_files:
        print(f"Error: No files found in {input_dir}")
        return 1

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_BASE_DIR / f"benchmark_{timestamp}"

    options = {
        "describe_images": args.describe_images,
    }

    # Get docling-serve URL
    docling_serve_url = getattr(args, "docling_serve_url", None)

    print("=" * 60)
    print("Document Extraction Benchmark")
    print("=" * 60)
    print(f"Type: {args.type}")
    print(f"Timeout: {args.timeout}s per extraction")
    if args.describe_images:
        print("Image description: ENABLED")
    if docling_serve_url:
        print(f"Docling-serve URL: {docling_serve_url}")
    print(f"Output: {output_dir}")

    # Run benchmarks by type
    all_results = []
    all_outputs = {}

    if args.type in ("all", "pdf"):
        pdf_files = [f for f in all_files if f.suffix.lower() == ".pdf"]
        if pdf_files:
            results, outputs = await run_benchmark_for_type(
                "pdf", pdf_files, engine_names, args.timeout, options, output_dir,
                docling_serve_url=docling_serve_url
            )
            all_results.extend(results)
            all_outputs.update(outputs)

    if args.type in ("all", "docx"):
        docx_files = [f for f in all_files if f.suffix.lower() == ".docx"]
        if docx_files:
            results, outputs = await run_benchmark_for_type(
                "docx", docx_files, engine_names, args.timeout, options, output_dir
            )
            all_results.extend(results)
            all_outputs.update(outputs)

    print("\n" + "=" * 60)
    print("Benchmark Complete!")
    print("=" * 60)
    print(f"Results saved to: {output_dir}")

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark document extraction engines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run all engines on all files
  %(prog)s --type pdf                         # Only benchmark PDFs
  %(prog)s --type docx                        # Only benchmark DOCX files
  %(prog)s --type pdf --engines docling       # Only test docling on PDFs
  %(prog)s --files benchmark.pdf              # Only test specific file
  %(prog)s --type pdf --describe-images       # With image descriptions
  %(prog)s --type pdf --engines docling-serve --docling-serve-url http://server:5001

PDF Engines: simple, pymupdf4llm, marker, docling, docling-vlm, docling-serve
DOCX Engines: python-docx, docling
        """,
    )
    parser.add_argument(
        "--type", "-t",
        type=str,
        choices=["pdf", "docx", "all"],
        default="all",
        help="Type of files to benchmark (default: all)",
    )
    parser.add_argument(
        "--engines", "-e",
        type=str,
        default=None,
        help="Comma-separated list of engines to test",
    )
    parser.add_argument(
        "--files", "-f",
        type=str,
        default=None,
        help="Comma-separated list of files to test (default: all in tests/input_content/)",
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
        help=f"Input directory for files (default: {TEST_INPUT_DIR})",
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
        help="Enable VLM-based image descriptions (PDF only, uses SmolVLM on CPU)",
    )
    parser.add_argument(
        "--docling-serve-url",
        type=str,
        default=None,
        help="URL for docling-serve remote extraction (e.g., http://server:5001)",
    )

    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    exit(main())

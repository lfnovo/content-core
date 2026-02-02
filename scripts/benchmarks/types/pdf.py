"""PDF extraction engines and quality scoring."""

import asyncio
import re
from typing import Any, Dict, List, Optional

from ..base import ContentAnalyzer, Engine, QualityScore, QualityScorer
from ..test_data.pdf_expected import BENCHMARK_PDF_EXPECTED


# --- Quality Scorer ---


class PDFQualityScorer(QualityScorer):
    """Score PDF extraction quality against expected content."""

    file_type = "pdf"

    def score(self, content: str, file_name: str) -> Optional[QualityScore]:
        """Score extraction quality against expected benchmark.pdf content.

        Handles both ASCII and LaTeX formula variations by checking multiple
        pattern variants for each expected formula.
        """
        if file_name != "benchmark.pdf":
            return None

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
        # Each formula is a tuple: (key_name, [pattern_variants])
        for formula_name, patterns in BENCHMARK_PDF_EXPECTED["formulas"]:
            key = f"formula_{formula_name}"
            # Check if any pattern variant matches
            details[key] = any(pattern in content for pattern in patterns)

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


# --- Content Analyzer ---


class MarkdownAnalyzer(ContentAnalyzer):
    """Analyze markdown content for structure metrics."""

    file_type = "pdf"

    def analyze(self, content: str) -> Dict[str, Any]:
        """Extract metrics from markdown content."""
        return {
            "headers_count": self._count_headers(content),
            "tables_count": self._count_tables(content),
            "formulas_count": self._count_formulas(content),
        }

    def _count_headers(self, content: str) -> int:
        """Count markdown headers (## style)."""
        return len(re.findall(r"^#{1,6}\s+.+$", content, re.MULTILINE))

    def _count_tables(self, content: str) -> int:
        """Count markdown tables (lines starting with |)."""
        table_rows = re.findall(r"^\|.+\|$", content, re.MULTILINE)
        if not table_rows:
            return 0
        # Count separator rows as table indicators
        separators = len(re.findall(r"^\|[\s\-:|]+\|$", content, re.MULTILINE))
        return max(separators, 1) if table_rows else 0

    def _count_formulas(self, content: str) -> int:
        """Count LaTeX formulas ($$ or $ delimited)."""
        # Block formulas
        block_formulas = len(re.findall(r"\$\$[^$]+\$\$", content))
        # Inline formulas (avoiding $$)
        inline_formulas = len(re.findall(r"(?<!\$)\$(?!\$)[^$]+\$(?!\$)", content))
        return block_formulas + inline_formulas


# --- Engines ---


class SimpleEngine(Engine):
    """Basic PyMuPDF text extraction without markdown formatting."""

    name = "simple"
    supported_types = ["pdf"]

    async def extract(self, file_path: str, options: Dict[str, Any]) -> str:
        """Extract PDF using basic PyMuPDF text extraction."""
        import fitz

        def _extract():
            doc = fitz.open(file_path)
            try:
                pages = []
                for page in doc:
                    text = page.get_text()
                    if text.strip():
                        pages.append(text)
                return "\n\n".join(pages)
            finally:
                doc.close()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract)


class PyMuPDF4LLMEngine(Engine):
    """Fast, lightweight extraction using pymupdf4llm."""

    name = "pymupdf4llm"
    supported_types = ["pdf"]

    async def extract(self, file_path: str, options: Dict[str, Any]) -> str:
        """Extract PDF using pymupdf4llm."""
        import pymupdf4llm

        def _extract():
            return pymupdf4llm.to_markdown(file_path, page_chunks=False, write_images=False)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract)


class MarkerEngine(Engine):
    """Deep learning-based extraction for high-quality markdown output.

    Note: First run will be slow as models are loaded (~2-5GB).
    License: GPL-3.0
    """

    name = "marker"
    supported_types = ["pdf"]

    async def extract(self, file_path: str, options: Dict[str, Any]) -> str:
        """Extract PDF using Marker."""
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        def _extract():
            artifact_dict = create_model_dict()
            converter = PdfConverter(artifact_dict=artifact_dict)
            result = converter(file_path)
            return result.markdown

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract)


class DoclingEngine(Engine):
    """Document understanding with OCR and table detection.

    When describe_images=True, enables VLM-based picture description using
    the SmolVLM-256M-Instruct model.

    Note: Picture description uses CPU device because the SmolVLM model
    produces incorrect output with MPS (Apple Silicon GPU).
    """

    name = "docling"
    supported_types = ["pdf"]

    async def extract(self, file_path: str, options: Dict[str, Any]) -> str:
        """Extract PDF using docling standard pipeline."""
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            smolvlm_picture_description,
        )
        from docling.document_converter import DocumentConverter, PdfFormatOption

        describe_images = options.get("describe_images", False)

        pipeline_options = PdfPipelineOptions()

        if describe_images:
            pipeline_options.do_picture_description = True
            pipeline_options.generate_picture_images = True
            pipeline_options.images_scale = 2.0
            pipeline_options.picture_description_options = smolvlm_picture_description
            # Use CPU for picture description - MPS produces incorrect output with SmolVLM
            pipeline_options.accelerator_options = AcceleratorOptions(device="cpu")

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, converter.convert, file_path)

        doc = result.document
        return doc.export_to_markdown()


class DoclingVLMEngine(Engine):
    """Vision-Language Model (granite-docling) for complex document layouts.

    Note: Picture description with VlmPipeline is not fully supported.
    Use DoclingEngine with describe_images=True for best results.
    See: https://github.com/docling-project/docling/discussions/2434
    """

    name = "docling-vlm"
    supported_types = ["pdf"]

    async def extract(self, file_path: str, options: Dict[str, Any]) -> str:
        """Extract PDF using docling VLM pipeline."""
        from docling.datamodel import vlm_model_specs
        from docling.datamodel.pipeline_options import VlmPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.pipeline.vlm_pipeline import VlmPipeline

        describe_images = options.get("describe_images", False)

        model_spec = vlm_model_specs.GRANITEDOCLING_MLX
        pipeline_options = VlmPipelineOptions(vlm_options=model_spec)

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

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, converter.convert, file_path)

        doc = result.document
        return doc.export_to_markdown()


# --- Factory Functions ---


def get_pdf_engines(names: Optional[List[str]] = None) -> List[Engine]:
    """Get PDF extraction engines by name.

    Args:
        names: List of engine names to get. If None, returns all available engines.

    Returns:
        List of Engine instances
    """
    all_engines = {
        "simple": SimpleEngine(),
        "pymupdf4llm": PyMuPDF4LLMEngine(),
        "marker": MarkerEngine(),
        "docling": DoclingEngine(),
        "docling-vlm": DoclingVLMEngine(),
    }

    if names is None:
        return list(all_engines.values())

    engines = []
    for name in names:
        if name in all_engines:
            engines.append(all_engines[name])
        else:
            raise ValueError(f"Unknown PDF engine: {name}. Available: {list(all_engines.keys())}")
    return engines


# List of available PDF engine names
AVAILABLE_PDF_ENGINES = ["simple", "pymupdf4llm", "marker", "docling", "docling-vlm"]

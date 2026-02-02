"""Document type-specific benchmark implementations."""

from .pdf import (
    PDFQualityScorer,
    MarkdownAnalyzer,
    SimpleEngine,
    PyMuPDF4LLMEngine,
    MarkerEngine,
    DoclingEngine,
    DoclingVLMEngine,
    get_pdf_engines,
)
from .docx import (
    DOCXQualityScorer,
    PythonDocxEngine,
    DoclingDocxEngine,
    get_docx_engines,
)

__all__ = [
    # PDF
    "PDFQualityScorer",
    "MarkdownAnalyzer",
    "SimpleEngine",
    "PyMuPDF4LLMEngine",
    "MarkerEngine",
    "DoclingEngine",
    "DoclingVLMEngine",
    "get_pdf_engines",
    # DOCX
    "DOCXQualityScorer",
    "PythonDocxEngine",
    "DoclingDocxEngine",
    "get_docx_engines",
]

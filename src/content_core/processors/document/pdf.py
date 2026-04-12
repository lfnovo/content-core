import asyncio
import re
import unicodedata

import pdfplumber  # type: ignore

from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput

def count_formula_placeholders(text):
    """
    Count the number of formula placeholders in extracted text.

    Args:
        text (str): Extracted text content
    Returns:
        int: Number of formula placeholders found
    """
    if not text:
        return 0
    return text.count('<!-- formula-not-decoded -->')


def convert_table_to_markdown(table):
    """
    Convert a table to markdown format.

    Args:
        table: Table data (list of lists)
    Returns:
        str: Markdown-formatted table
    """
    if not table or not table[0]:
        return ""

    # Build markdown table
    markdown_lines = []

    # Header row
    header = table[0]
    header_row = "| " + " | ".join(str(cell) if cell else "" for cell in header) + " |"
    markdown_lines.append(header_row)

    # Separator row
    separator = "|" + "|".join([" --- " for _ in header]) + "|"
    markdown_lines.append(separator)

    # Data rows
    for row in table[1:]:
        if row:  # Skip empty rows
            row_text = "| " + " | ".join(str(cell) if cell else "" for cell in row) + " |"
            markdown_lines.append(row_text)

    return "\n".join(markdown_lines) + "\n"

SUPPORTED_PDF_TYPES = ["application/pdf"]


def clean_pdf_text(text):
    """
    Clean text extracted from PDFs with enhanced space handling.
    Preserves special characters like (, ), %, = that are valid in code/math.

    Args:
        text (str): The raw text extracted from a PDF
    Returns:
        str: Cleaned text with minimal necessary spacing
    """
    if not text:
        return text

    # Step 1: Normalize Unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Replace common PDF artifacts
    replacements = {
        # Common ligatures
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb00": "ff",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        # Quotation marks and apostrophes
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u2032": "'",
        "\u201a": ",",
        "\u201e": '"',
        # Dashes and hyphens
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        # Other common replacements
        "\u2026": "...",
        "\u2022": "*",
        "\u00b0": " degrees ",
        "\u00b9": "1",
        "\u00b2": "2",
        "\u00b3": "3",
        "\u00a9": "(c)",
        "\u00ae": "(R)",
        "\u2122": "(TM)",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Step 3: Clean control characters while preserving essential whitespace and special chars
    text = "".join(
        char
        for char in text
        if unicodedata.category(char)[0] != "C"
        or char in "\n\t "
        or char in "()%=[]{}#$@!?.,;:+-*/^<>&|~"
    )

    # Step 4: Enhanced space cleaning
    text = re.sub(r"[ \t]+", " ", text)  # Consolidate horizontal whitespace
    text = re.sub(r" +\n", "\n", text)  # Remove spaces before newlines
    text = re.sub(r"\n +", "\n", text)  # Remove spaces after newlines
    text = re.sub(r"\n\t+", "\n", text)  # Remove tabs at start of lines
    text = re.sub(r"\t+\n", "\n", text)  # Remove tabs at end of lines
    text = re.sub(r"\t+", " ", text)  # Replace tabs with single space

    # Step 5: Remove empty lines while preserving paragraph structure
    text = re.sub(r"\n{3,}", "\n\n", text)  # Max two consecutive newlines
    text = re.sub(r"^\s+", "", text)  # Remove leading whitespace
    text = re.sub(r"\s+$", "", text)  # Remove trailing whitespace

    # Step 6: Clean up around punctuation
    text = re.sub(r"\s+([.,;:!?)])", r"\1", text)  # Remove spaces before punctuation
    text = re.sub(r"(\()\s+", r"\1", text)  # Remove spaces after opening parenthesis
    text = re.sub(
        r"\s+([.,])\s+", r"\1 ", text
    )  # Ensure single space after periods and commas

    # Step 7: Remove zero-width and invisible characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u200e\u200f]", "", text)

    # Step 8: Fix hyphenation and line breaks
    text = re.sub(
        r"(?<=\w)-\s*\n\s*(?=\w)", "", text
    )  # Remove hyphenation at line breaks

    return text.strip()


async def _extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    def _extract():
        with pdfplumber.open(pdf_path) as pdf:
            full_text = []
            logger.debug(f"Found {len(pdf.pages)} pages in PDF")
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                # Table extraction
                try:
                    tables = page.extract_tables()
                    if tables:
                        logger.debug(f"Found {len(tables)} table(s) on page {page_num + 1}")
                        for table_num, table in enumerate(tables):
                            if table and any(
                                any(str(cell).strip() for cell in row if cell)
                                for row in table if row
                            ):
                                page_text += f"\n\n[Table {table_num + 1} from page {page_num + 1}]\n"
                                page_text += convert_table_to_markdown(table) + "\n"
                except Exception as e:
                    logger.debug(f"Table extraction failed on page {page_num + 1}: {e}")
                full_text.append(page_text)
            return clean_pdf_text("\n\n".join(full_text))
    return await asyncio.get_event_loop().run_in_executor(None, _extract)


async def extract_pdf_file(file_path: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content from a PDF file."""
    try:
        text = await _extract_text_from_pdf(file_path)
        return ExtractionOutput(
            content=text,
            source_type="file",
            identified_type="application/pdf",
        )
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found at {file_path}")
    except Exception as e:
        raise Exception(f"An error occurred: {e}")

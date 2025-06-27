import asyncio
import re
import unicodedata

import fitz  # type: ignore

from content_core.common import ProcessSourceState
from content_core.config import CONFIG
from content_core.logging import logger

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


def extract_page_with_ocr(page, page_num):
    """
    Extract text from a page using OCR (Tesseract).
    
    Args:
        page: PyMuPDF page object
        page_num (int): Page number for logging
    Returns:
        str: OCR-extracted text or None if OCR fails
    """
    try:
        logger.debug(f"Attempting OCR extraction for page {page_num}")
        # Create TextPage using OCR
        textpage = page.get_textpage_ocr()
        if textpage:
            # Extract text from the OCR TextPage
            ocr_text = textpage.extractText()
            logger.debug(f"OCR successful for page {page_num}, extracted {len(ocr_text)} characters")
            return ocr_text
        else:
            logger.warning(f"OCR TextPage creation failed for page {page_num}")
            return None
    except (ImportError, RuntimeError, OSError) as e:
        # Common errors: Tesseract not installed, OCR failure, file access issues
        logger.debug(f"OCR extraction failed for page {page_num}: {e}")
        return None
    except Exception as e:
        # Unexpected errors - log as warning for debugging
        logger.warning(f"Unexpected error during OCR extraction for page {page_num}: {e}")
        return None


def convert_table_to_markdown(table):
    """
    Convert a PyMuPDF table to markdown format.
    
    Args:
        table: Table data from PyMuPDF (list of lists)
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

# Configuration constants
DEFAULT_FORMULA_THRESHOLD = 3
DEFAULT_OCR_FALLBACK = True

SUPPORTED_FITZ_TYPES = [
    "application/pdf",
    "application/epub+zip",
]


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
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        # Quotation marks and apostrophes
        """: "'",
        """: "'",
        '"': '"',
        "′": "'",
        "‚": ",",
        "„": '"',
        # Dashes and hyphens
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        # Other common replacements
        "…": "...",
        "•": "*",
        "°": " degrees ",
        "¹": "1",
        "²": "2",
        "³": "3",
        "©": "(c)",
        "®": "(R)",
        "™": "(TM)",
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




async def _extract_text_from_pdf(pdf_path):
    """Extract text from PDF asynchronously with table detection"""

    def _extract():
        doc = fitz.open(pdf_path)
        try:
            full_text = []
            logger.debug(f"Found {len(doc)} pages in PDF")
            
            # Use quality improvement flags for better text extraction
            extraction_flags = (
                fitz.TEXT_PRESERVE_LIGATURES |  # Better character rendering
                fitz.TEXT_PRESERVE_WHITESPACE |  # Better spacing preservation
                fitz.TEXT_PRESERVE_IMAGES       # Better image-text integration
            )
            
            # Get OCR configuration
            ocr_config = CONFIG.get('extraction', {}).get('pymupdf', {})
            enable_ocr = ocr_config.get('enable_formula_ocr', False)
            formula_threshold = ocr_config.get('formula_threshold', DEFAULT_FORMULA_THRESHOLD)
            ocr_fallback = ocr_config.get('ocr_fallback', DEFAULT_OCR_FALLBACK)
            
            for page_num, page in enumerate(doc):
                # Extract regular text with quality flags
                standard_text = page.get_text(flags=extraction_flags)
                
                # Check if we should try OCR for this page
                formula_count = count_formula_placeholders(standard_text)
                use_ocr = (enable_ocr and 
                          formula_count >= formula_threshold and 
                          formula_count > 0)
                
                if use_ocr:
                    logger.debug(f"Page {page_num + 1} has {formula_count} formulas, attempting OCR")
                    ocr_text = extract_page_with_ocr(page, page_num + 1)
                    
                    if ocr_text and ocr_fallback:
                        # Use OCR text but preserve table extraction from standard text
                        page_text = ocr_text
                        logger.debug(f"Using OCR text for page {page_num + 1}")
                    else:
                        # OCR failed, use standard text
                        page_text = standard_text
                        if not ocr_text:
                            logger.debug(f"OCR failed for page {page_num + 1}, using standard extraction")
                else:
                    page_text = standard_text
                
                # Try to find and extract tables (regardless of OCR)
                try:
                    tables = page.find_tables()
                    if tables:
                        logger.debug(f"Found {len(tables)} table(s) on page {page_num + 1}")
                        
                        # For each table found, convert to markdown and append
                        for table_num, table in enumerate(tables):
                            # Extract table data
                            table_data = table.extract()
                            # Validate table has actual content (not just empty rows/cells)
                            if table_data and len(table_data) > 0 and any(
                                any(str(cell).strip() for cell in row if cell) for row in table_data if row
                            ):
                                # Add a marker before the table
                                page_text += f"\n\n[Table {table_num + 1} from page {page_num + 1}]\n"
                                # Convert to markdown
                                markdown_table = convert_table_to_markdown(table_data)
                                page_text += markdown_table + "\n"
                except Exception as e:
                    # If table extraction fails, continue with regular text
                    logger.debug(f"Table extraction failed on page {page_num + 1}: {e}")
                
                full_text.append(page_text)
            
            # Join all pages and clean
            combined_text = "".join(full_text)
            return clean_pdf_text(combined_text)
        finally:
            doc.close()

    # Run CPU-bound PDF processing in a thread pool
    return await asyncio.get_event_loop().run_in_executor(None, _extract)


async def extract_pdf(state: ProcessSourceState):
    """
    Parse the PDF file and extract its content asynchronously.
    """
    return_dict = {}
    assert state.file_path, "No file path provided"
    assert state.identified_type in SUPPORTED_FITZ_TYPES, "Unsupported File Type"

    if state.file_path is not None and state.identified_type in SUPPORTED_FITZ_TYPES:
        file_path = state.file_path
        try:
            text = await _extract_text_from_pdf(file_path)
            return_dict["content"] = text
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found at {file_path}")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")

    return return_dict

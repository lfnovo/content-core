import asyncio

from docx import Document  # type: ignore
from docx.table import Table, _Cell  # type: ignore
from docx.text.hyperlink import Hyperlink  # type: ignore

from content_core.logging import logger


def _cell_text(cell):
    text = " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())
    return text.replace("|", "\\|").replace("\n", " ")


def _row_cells(row):
    """The cells of a row, one per grid column.

    ``row.cells`` raises ``ValueError`` for a vertically merged cell that has
    no cell above it, so the row's own cells are used then.
    """
    try:
        return row.cells
    except ValueError:
        return [_Cell(tc, row.table) for tc in row._tr.tc_lst]


def _table_to_markdown(table):
    """Render a python-docx table as a markdown table, the first row as header."""
    rows = [[_cell_text(cell) for cell in _row_cells(row)] for row in table.rows]
    rows = [row for row in rows if row]
    if not rows or not any(any(row) for row in rows):
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(rows[0]) + " |"]
    lines.append("| " + " | ".join(["---"] * width) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _formatted_run(run):
    if run.bold:
        return f"**{run.text}**"
    if run.italic:
        return f"*{run.text}*"
    return run.text


async def extract_docx_content_detailed(file_path):
    """Extract content from DOCX file"""

    def _extract():
        try:
            doc = Document(file_path)
            content = []

            # iter_inner_content yields the body's paragraphs and tables in
            # document order; doc.paragraphs leaves every table out.
            for block in doc.iter_inner_content():
                if isinstance(block, Table):
                    table = _table_to_markdown(block)
                    if table:
                        content.append(table)
                    continue
                paragraph = block
                if not paragraph.text.strip():
                    continue

                style = paragraph.style.name if paragraph.style else "Normal"
                text = paragraph.text.strip()

                # Get paragraph formatting
                p_format = paragraph.paragraph_format
                indent = p_format.left_indent or 0

                # Convert indent to spaces (1 level = 4 spaces)
                indent_level = 0
                if hasattr(indent, "pt"):
                    indent_level = int(indent.pt / 72)  # 72 points = 1 inch
                indent_spaces = " " * (indent_level * 4)

                # Handle different types of formatting
                if "Heading" in style:
                    level = style[-1] if style[-1].isdigit() else "1"
                    heading_marks = "#" * int(level)
                    content.append(f"\n{heading_marks} {text}\n")

                # Handle bullet points
                elif (
                    paragraph.style
                    and hasattr(paragraph.style, "name")
                    and paragraph.style.name.startswith("List")
                ):
                    # Numbered list
                    if (
                        hasattr(paragraph._p, "pPr")
                        and paragraph._p.pPr is not None
                        and hasattr(paragraph._p.pPr, "numPr")
                        and paragraph._p.pPr.numPr is not None
                    ):
                        # Try to get the actual number
                        try:
                            if (
                                hasattr(paragraph._p.pPr.numPr, "numId")
                                and paragraph._p.pPr.numPr.numId is not None
                                and hasattr(paragraph._p.pPr.numPr.numId, "val")
                            ):
                                number = paragraph._p.pPr.numPr.numId.val
                                content.append(f"{indent_spaces}{number}. {text}")
                            else:
                                content.append(f"{indent_spaces}1. {text}")
                        except Exception:
                            content.append(f"{indent_spaces}1. {text}")
                    # Bullet list
                    else:
                        content.append(f"{indent_spaces}* {text}")

                else:
                    # Handle text formatting. paragraph.runs leaves out the runs
                    # inside a hyperlink, so a link's text was dropped; the
                    # paragraph's inner content holds runs and hyperlinks.
                    formatted_text = []
                    for item in paragraph.iter_inner_content():
                        if isinstance(item, Hyperlink):
                            text = "".join(_formatted_run(run) for run in item.runs)
                            formatted_text.append(
                                f"[{text}]({item.url})" if item.url and text else text
                            )
                        else:
                            formatted_text.append(_formatted_run(item))

                    content.append(f"{indent_spaces}{''.join(formatted_text)}")

            return "\n\n".join(content)

        except Exception as e:
            logger.error(f"Failed to extract DOCX content: {e}")
            return None

    return await asyncio.get_event_loop().run_in_executor(None, _extract)


async def get_docx_info(file_path):
    """Get DOCX metadata and content"""

    async def _get_info():
        try:
            doc = Document(file_path)

            # Extract core properties if available
            core_props = {
                "author": doc.core_properties.author,
                "created": doc.core_properties.created,
                "modified": doc.core_properties.modified,
                "title": doc.core_properties.title,
                "subject": doc.core_properties.subject,
                "keywords": doc.core_properties.keywords,
                "category": doc.core_properties.category,
                "comments": doc.core_properties.comments,
            }

            # Get document content
            content = await extract_docx_content_detailed(file_path)

            # Get document statistics
            stats = {
                "paragraph_count": len(doc.paragraphs),
                "word_count": sum(
                    len(p.text.split()) for p in doc.paragraphs if p.text.strip()
                ),
                "character_count": sum(
                    len(p.text) for p in doc.paragraphs if p.text.strip()
                ),
            }

            return {"metadata": core_props, "content": content, "statistics": stats}

        except Exception as e:
            logger.error(f"Failed to get DOCX info: {e}")
            return None

    return await _get_info()

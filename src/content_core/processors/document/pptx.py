import asyncio

from pptx import Presentation  # type: ignore
from pptx.enum.shapes import MSO_SHAPE_TYPE  # type: ignore

from content_core.logging import logger


def _table_to_markdown(table):
    """Render a slide table as a markdown table, the first row as header."""
    rows = [
        [cell.text.strip().replace("|", "\\|").replace("\n", " ") for cell in row.cells]
        for row in table.rows
    ]
    if not rows or not any(any(row) for row in rows):
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(rows[0]) + " |"]
    lines.append("| " + " | ".join(["---"] * width) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _shape_texts(shapes, title):
    """Yield the text of the shapes in reading order.

    A group shape and a table (a graphic frame) have no ``text`` of their
    own: a group's text is in the shapes it groups, and a table's in its
    cells, so both are read through.
    """
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _shape_texts(shape.shapes, title)
        elif getattr(shape, "has_table", False) and shape.has_table:
            table = _table_to_markdown(shape.table)
            if table:
                yield table
        elif hasattr(shape, "text") and shape.text.strip():
            if shape != title:  # Skip title as it's already added
                yield shape.text.strip()


async def extract_pptx_content(file_path):
    """Extract content from PPTX file"""

    def _extract():
        try:
            prs = Presentation(file_path)
            content = []

            for slide_number, slide in enumerate(prs.slides, 1):
                content.append(f"\n# Slide {slide_number}\n")

                # Extract title
                if slide.shapes.title:
                    content.append(f"## {slide.shapes.title.text}\n")

                # Extract text from all shapes, groups and tables included
                content.extend(_shape_texts(slide.shapes, slide.shapes.title))

            return "\n\n".join(content)

        except Exception as e:
            logger.error(f"Failed to extract PPTX content: {e}")
            return None

    return await asyncio.get_event_loop().run_in_executor(None, _extract)


async def get_pptx_info(file_path):
    """Get PPTX metadata and content"""

    def _get_pptx_metadata_sync(file_path):
        """Synchronous helper to extract metadata using python-pptx."""
        try:
            prs = Presentation(file_path)
            props = {
                "slide_count": len(prs.slides),
                "title": "",  # PowerPoint doesn't have built-in metadata like Word
            }
            stats = {
                "slide_count": len(prs.slides),
                "shape_count": sum(len(slide.shapes) for slide in prs.slides),
                "text_frame_count": sum(
                    sum(1 for shape in slide.shapes if hasattr(shape, "text"))
                    for slide in prs.slides
                ),
            }
            return {"metadata": props, "statistics": stats}
        except Exception as e:
            logger.error(f"Failed to get PPTX metadata: {e}")
            return None

    try:
        # Run blocking python-pptx operations in executor
        metadata_info = await asyncio.get_event_loop().run_in_executor(
            None, _get_pptx_metadata_sync, file_path
        )

        # Await the async content extraction directly
        content = await extract_pptx_content(file_path)

        if metadata_info:
            # Combine results
            return {**metadata_info, "content": content}
        else:
            # Fallback if metadata extraction failed
            return {"metadata": {}, "statistics": {}, "content": content}

    except Exception as e:
        logger.error(f"Failed to get PPTX info: {e}")
        return None

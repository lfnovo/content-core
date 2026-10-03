"""OpenDocument extraction (ODT/ODS/ODP) using odfpy."""
import asyncio

from odf import teletype  # type: ignore
from odf.namespaces import DRAWNS, PRESENTATIONNS, TABLENS, TEXTNS  # type: ignore
from odf.opendocument import load  # type: ignore

from content_core.logging import logger

ODT_MIME = "application/vnd.oasis.opendocument.text"
ODS_MIME = "application/vnd.oasis.opendocument.spreadsheet"
ODP_MIME = "application/vnd.oasis.opendocument.presentation"

SUPPORTED_ODF_TYPES = [ODT_MIME, ODS_MIME, ODP_MIME]

_H = (TEXTNS, "h")
_P = (TEXTNS, "p")
_LIST = (TEXTNS, "list")
_LIST_ITEM = (TEXTNS, "list-item")
_LIST_HEADER = (TEXTNS, "list-header")
_SECTION = (TEXTNS, "section")
_TABLE = (TABLENS, "table")
_TABLE_ROW = (TABLENS, "table-row")
_TABLE_CELL = (TABLENS, "table-cell")
_COVERED_CELL = (TABLENS, "covered-table-cell")
_TABLE_ROW_GROUPS = {
    (TABLENS, "table-header-rows"),
    (TABLENS, "table-rows"),
    (TABLENS, "table-row-group"),
}
_DRAW_PAGE = (DRAWNS, "page")
_NOTES = (PRESENTATIONNS, "notes")


def _elements(node):
    """Yield the element children of an odfpy node (skipping text nodes)."""
    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            yield child


def _paragraphs(node):
    """Yield the text of every paragraph/heading under node, in document order."""
    for child in _elements(node):
        if child.qname in (_P, _H):
            text = teletype.extractText(child).strip()
            if text:
                yield text
        else:
            yield from _paragraphs(child)


def _cell_text(cell):
    text = " ".join(_paragraphs(cell))
    return text.replace("|", "\\|").replace("\n", " ")


def _table_rows(node):
    """Yield table-row elements, descending into header/row groups."""
    for child in _elements(node):
        if child.qname == _TABLE_ROW:
            yield child
        elif child.qname in _TABLE_ROW_GROUPS:
            yield from _table_rows(child)


def _table_to_markdown(table_el, max_rows=10000, max_cols=100):
    """Render a table:table element as a markdown table.

    Repeated rows/cells (``number-*-repeated``) are expanded up to the limits;
    trailing empty cells and rows are dropped, since spreadsheets pad every
    sheet out to the application's full grid with repeated empty cells.
    """
    rows = []
    pending_empty = 0  # empty rows are only materialized if content follows
    for row_el in _table_rows(table_el):
        if len(rows) >= max_rows:
            break
        row = []
        for cell in _elements(row_el):
            if cell.qname not in (_TABLE_CELL, _COVERED_CELL):
                continue
            repeat = int(cell.getAttrNS(TABLENS, "number-columns-repeated") or 1)
            value = _cell_text(cell)
            row.extend([value] * min(repeat, max_cols - len(row)))
            if len(row) >= max_cols:
                break
        while row and not row[-1]:
            row.pop()
        repeat = int(row_el.getAttrNS(TABLENS, "number-rows-repeated") or 1)
        if not row:
            pending_empty += repeat
            continue
        rows.extend([[]] * min(pending_empty, max_rows - len(rows)))
        pending_empty = 0
        rows.extend([row] * min(repeat, max_rows - len(rows)))

    if not rows:
        return ""

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(rows[0]) + " |"]
    lines.append("| " + " | ".join(["---"] * width) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _list_items(list_el, depth=0):
    """Render a text:list as markdown bullets, indenting nested lists."""
    items = []
    indent = " " * (depth * 4)
    for item in _elements(list_el):
        if item.qname not in (_LIST_ITEM, _LIST_HEADER):
            continue
        for child in _elements(item):
            if child.qname == _LIST:
                items.extend(_list_items(child, depth + 1))
            else:
                items.extend(f"{indent}* {text}" for text in _paragraphs_of(child))
    return items


def _paragraphs_of(node):
    """Text of node itself if it is a paragraph/heading, else of its descendants."""
    if node.qname in (_P, _H):
        text = teletype.extractText(node).strip()
        return [text] if text else []
    return list(_paragraphs(node))


def _odt_blocks(node):
    """Yield markdown blocks for the body of a text document."""
    for child in _elements(node):
        if child.qname == _H:
            text = teletype.extractText(child).strip()
            if text:
                level = int(child.getAttrNS(TEXTNS, "outline-level") or 1)
                yield f"{'#' * max(1, min(level, 6))} {text}"
        elif child.qname == _P:
            text = teletype.extractText(child).strip()
            if text:
                yield text
        elif child.qname == _LIST:
            items = _list_items(child)
            if items:
                yield "\n".join(items)
        elif child.qname == _TABLE:
            table = _table_to_markdown(child)
            if table:
                yield table
        elif child.qname == _SECTION:
            yield from _odt_blocks(child)


async def extract_odt_content(file_path):
    """Extract content from an ODT file as markdown."""

    def _extract():
        doc = load(file_path)
        return "\n\n".join(_odt_blocks(doc.text))

    return await asyncio.get_event_loop().run_in_executor(None, _extract)


async def extract_ods_content(file_path):
    """Extract content from an ODS file: one markdown table per sheet.

    Sheet headings match ``xlsx.py`` (``# Sheet: <name>``).
    """

    def _extract():
        doc = load(file_path)
        content = []
        for sheet in _elements(doc.spreadsheet):
            if sheet.qname != _TABLE:
                continue
            name = sheet.getAttrNS(TABLENS, "name") or ""
            try:
                table = _table_to_markdown(sheet)
            except Exception as e:
                logger.warning(f"Skipping ODS sheet {name!r}: {e}")
                continue
            content.append(f"# Sheet: {name}")
            if table:
                content.append(table)
        return "\n\n".join(content)

    return await asyncio.get_event_loop().run_in_executor(None, _extract)


async def extract_odp_content(file_path):
    """Extract content from an ODP file: one block per slide.

    Slide headings match ``pptx.py`` (``# Slide N``).
    """

    def _extract():
        doc = load(file_path)
        content = []
        slides = [el for el in _elements(doc.presentation) if el.qname == _DRAW_PAGE]
        for slide_number, slide in enumerate(slides, 1):
            try:
                frames = []
                for shape in _elements(slide):
                    if shape.qname == _NOTES:
                        continue
                    text = "\n".join(_paragraphs_of(shape))
                    if text:
                        frames.append(text)
            except Exception as e:
                logger.warning(f"Skipping ODP slide {slide_number}: {e}")
                continue
            content.append(f"# Slide {slide_number}")
            content.extend(frames)
        return "\n\n".join(content)

    return await asyncio.get_event_loop().run_in_executor(None, _extract)

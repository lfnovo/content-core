"""Unit tests for content_core.processors.document (office extraction)."""

from unittest.mock import AsyncMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.document import extract_office


@pytest.fixture
def config():
    return ContentCoreConfig()


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class TestExtractOfficeRouting:
    async def test_docx_calls_docx_extractor(self, config):
        with patch(
            "content_core.processors.document.extract_docx_content_detailed",
            new_callable=AsyncMock,
            return_value="# Heading\n\nDocx content",
        ) as mock_docx:
            result = await extract_office("/fake/doc.docx", DOCX_MIME, config)
            mock_docx.assert_called_once_with("/fake/doc.docx")
            assert result.content == "# Heading\n\nDocx content"
            assert result.source_type == "file"
            assert result.identified_type == DOCX_MIME

    async def test_pptx_calls_pptx_extractor(self, config):
        with patch(
            "content_core.processors.document.extract_pptx_content",
            new_callable=AsyncMock,
            return_value="# Slide 1\n\n## Title\n\nSlide content",
        ) as mock_pptx:
            result = await extract_office("/fake/pres.pptx", PPTX_MIME, config)
            mock_pptx.assert_called_once_with("/fake/pres.pptx")
            assert "Slide content" in result.content
            assert result.identified_type == PPTX_MIME

    async def test_xlsx_calls_xlsx_extractor(self, config):
        with patch(
            "content_core.processors.document.extract_xlsx_content",
            new_callable=AsyncMock,
            return_value="| Col1 | Col2 |\n| --- | --- |\n| A | B |",
        ) as mock_xlsx:
            result = await extract_office("/fake/data.xlsx", XLSX_MIME, config)
            mock_xlsx.assert_called_once_with("/fake/data.xlsx")
            assert "Col1" in result.content
            assert result.identified_type == XLSX_MIME

    async def test_unknown_mime_raises_value_error(self, config):
        with pytest.raises(ValueError, match="Unsupported Office MIME type"):
            await extract_office("/fake/file.odt", "application/odt", config)

    async def test_docx_returns_extraction_output(self, config):
        with patch(
            "content_core.processors.document.extract_docx_content_detailed",
            new_callable=AsyncMock,
            return_value="# Report\n\nContent here",
        ):
            result = await extract_office("/fake/report.docx", DOCX_MIME, config)
            assert result.source_type == "file"
            assert result.identified_type == DOCX_MIME
            assert "Report" in result.content

    async def test_pptx_returns_slide_content(self, config):
        slide_content = "# Slide 1\n\n## Intro\n\nWelcome to the presentation"
        with patch(
            "content_core.processors.document.extract_pptx_content",
            new_callable=AsyncMock,
            return_value=slide_content,
        ):
            result = await extract_office("/fake/deck.pptx", PPTX_MIME, config)
            assert "Welcome to the presentation" in result.content

    async def test_xlsx_returns_table_content(self, config):
        table_content = "| Name | Age |\n| --- | --- |\n| Alice | 30 |"
        with patch(
            "content_core.processors.document.extract_xlsx_content",
            new_callable=AsyncMock,
            return_value=table_content,
        ):
            result = await extract_office("/fake/sheet.xlsx", XLSX_MIME, config)
            assert "Alice" in result.content
            assert "30" in result.content

    async def test_none_content_returns_empty_string(self, config):
        with patch(
            "content_core.processors.document.extract_docx_content_detailed",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await extract_office("/fake/empty.docx", DOCX_MIME, config)
            assert result.content == ""


ODT_MIME = "application/vnd.oasis.opendocument.text"
ODS_MIME = "application/vnd.oasis.opendocument.spreadsheet"
ODP_MIME = "application/vnd.oasis.opendocument.presentation"


class TestExtractOfficeOdfRouting:
    @pytest.mark.parametrize(
        "mime, extractor",
        [
            (ODT_MIME, "extract_odt_content"),
            (ODS_MIME, "extract_ods_content"),
            (ODP_MIME, "extract_odp_content"),
        ],
    )
    async def test_odf_calls_odf_extractor(self, config, mime, extractor):
        with patch(
            f"content_core.processors.document.{extractor}",
            new_callable=AsyncMock,
            return_value="## ODF content",
        ) as mock_extract:
            result = await extract_office("/fake/file.odf", mime, config)
            mock_extract.assert_called_once_with("/fake/file.odf")
            assert result.content == "## ODF content"
            assert result.source_type == "file"
            assert result.identified_type == mime

    async def test_unsupported_odf_mime_raises_value_error(self, config):
        with pytest.raises(ValueError, match="Unsupported Office MIME type"):
            await extract_office(
                "/fake/drawing.odg", "application/vnd.oasis.opendocument.graphics", config
            )


# ---------------------------------------------------------------------------
# odf.py parsing, with odfpy's `load` mocked to return in-memory documents
# ---------------------------------------------------------------------------
from odf.draw import Frame, Page, TextBox  # noqa: E402
from odf.opendocument import (  # noqa: E402
    OpenDocumentPresentation,
    OpenDocumentSpreadsheet,
    OpenDocumentText,
)
from odf.presentation import Notes  # noqa: E402
from odf.table import CoveredTableCell, Table, TableCell, TableRow  # noqa: E402
from odf.text import H, List, ListItem, P  # noqa: E402

from odf import teletype  # noqa: E402

from content_core.processors.document import odf as odf_processor  # noqa: E402
from content_core.processors.document.odf import (  # noqa: E402
    extract_odp_content,
    extract_ods_content,
    extract_odt_content,
)

LOAD = "content_core.processors.document.odf.load"


def _row(*values, repeat=None):
    row = TableRow(numberrowsrepeated=repeat) if repeat else TableRow()
    for value in values:
        cell = TableCell()
        if value:
            cell.addElement(P(text=value))
        row.addElement(cell)
    return row


def _table(name, *rows):
    table = Table(name=name)
    for row in rows:
        table.addElement(row)
    return table


def _slide(*texts):
    page = Page(masterpagename="Default")
    for text in texts:
        frame = Frame()
        box = TextBox()
        box.addElement(P(text=text))
        frame.addElement(box)
        page.addElement(frame)
    return page


class TestOdtContent:
    async def test_headings_paragraphs_lists_and_tables(self):
        doc = OpenDocumentText()
        doc.text.addElement(H(outlinelevel=1, text="Title"))
        doc.text.addElement(P(text="Intro paragraph."))
        doc.text.addElement(H(outlinelevel=2, text="Section"))
        doc.text.addElement(P(text="   "))
        items = List()
        for text in ("First", "Second"):
            item = ListItem()
            item.addElement(P(text=text))
            items.addElement(item)
        doc.text.addElement(items)
        doc.text.addElement(_table("T", _row("A", "B"), _row("1", "2")))

        with patch(LOAD, return_value=doc) as mock_load:
            content = await extract_odt_content("/fake/doc.odt")

        mock_load.assert_called_once_with("/fake/doc.odt")
        assert content == (
            "# Title\n\nIntro paragraph.\n\n## Section\n\n"
            "* First\n* Second\n\n"
            "| A | B |\n| --- | --- |\n| 1 | 2 |"
        )

    async def test_nested_list_is_indented(self):
        doc = OpenDocumentText()
        outer, inner = List(), List()
        inner_item = ListItem()
        inner_item.addElement(P(text="Child"))
        inner.addElement(inner_item)
        outer_item = ListItem()
        outer_item.addElement(P(text="Parent"))
        outer_item.addElement(inner)
        outer.addElement(outer_item)
        doc.text.addElement(outer)

        with patch(LOAD, return_value=doc):
            content = await extract_odt_content("/fake/doc.odt")

        assert content == "* Parent\n    * Child"

    async def test_whole_file_failure_propagates(self):
        with patch(LOAD, side_effect=ValueError("not an ODF file")):
            with pytest.raises(ValueError, match="not an ODF file"):
                await extract_odt_content("/fake/broken.odt")


class TestOdsContent:
    async def test_one_table_per_sheet(self):
        doc = OpenDocumentSpreadsheet()
        doc.spreadsheet.addElement(_table("People", _row("Name", "Age"), _row("Alice", "30")))
        doc.spreadsheet.addElement(_table("Empty"))

        with patch(LOAD, return_value=doc):
            content = await extract_ods_content("/fake/data.ods")

        assert content == (
            "# Sheet: People\n\n| Name | Age |\n| --- | --- |\n| Alice | 30 |\n\n# Sheet: Empty"
        )

    async def test_repeated_cells_and_rows_are_expanded_and_padding_trimmed(self):
        doc = OpenDocumentSpreadsheet()
        header = _row("Key", "Value")
        header.addElement(TableCell(numbercolumnsrepeated=16000))  # grid padding
        repeated = TableRow(numberrowsrepeated=2)
        cell = TableCell(numbercolumnsrepeated=2)
        cell.addElement(P(text="x"))
        repeated.addElement(cell)
        doc.spreadsheet.addElement(
            _table(
                "Grid",
                header,
                _row(repeat=3),  # interior empty rows are kept
                repeated,
                _row(repeat=1048000),  # trailing grid padding is dropped
            )
        )

        with patch(LOAD, return_value=doc):
            content = await extract_ods_content("/fake/grid.ods")

        assert content == (
            "# Sheet: Grid\n\n| Key | Value |\n| --- | --- |\n"
            "|  |  |\n|  |  |\n|  |  |\n| x | x |\n| x | x |"
        )

    async def test_covered_cells_and_pipes(self):
        doc = OpenDocumentSpreadsheet()
        row = _row("a|b")
        row.addElement(CoveredTableCell())
        row.addElement(_row("c").childNodes[0])
        doc.spreadsheet.addElement(_table("S", row))

        with patch(LOAD, return_value=doc):
            content = await extract_ods_content("/fake/s.ods")

        assert content == "# Sheet: S\n\n| a\\|b |  | c |\n| --- | --- | --- |"

    async def test_failed_sheet_is_skipped(self):
        doc = OpenDocumentSpreadsheet()
        doc.spreadsheet.addElement(_table("Bad", _row("x")))
        doc.spreadsheet.addElement(_table("Good", _row("y")))
        real = odf_processor._table_to_markdown

        def flaky(table, *args, **kwargs):
            if table.getAttribute("name") == "Bad":
                raise RuntimeError("corrupt sheet")
            return real(table, *args, **kwargs)

        with patch(LOAD, return_value=doc), patch(
            "content_core.processors.document.odf._table_to_markdown", side_effect=flaky
        ):
            content = await extract_ods_content("/fake/data.ods")

        assert "Bad" not in content
        assert content == "# Sheet: Good\n\n| y |\n| --- |"


class TestOdpContent:
    async def test_one_block_per_slide(self):
        doc = OpenDocumentPresentation()
        doc.presentation.addElement(_slide("Welcome", "Body text"))
        second = _slide("Second")
        notes = Notes()
        notes.addElement(_slide("Speaker notes").childNodes[0])
        second.addElement(notes)
        doc.presentation.addElement(second)

        with patch(LOAD, return_value=doc):
            content = await extract_odp_content("/fake/deck.odp")

        assert content == (
            "# Slide 1\n\nWelcome\n\nBody text\n\n# Slide 2\n\nSecond"
        )

    async def test_failed_slide_is_skipped(self):
        doc = OpenDocumentPresentation()
        doc.presentation.addElement(_slide("Broken"))
        doc.presentation.addElement(_slide("Fine"))
        real = odf_processor._paragraphs_of

        def flaky(node):
            if teletype.extractText(node) == "Broken":
                raise RuntimeError("corrupt slide")
            return real(node)

        with patch(LOAD, return_value=doc), patch(
            "content_core.processors.document.odf._paragraphs_of", side_effect=flaky
        ):
            content = await extract_odp_content("/fake/deck.odp")

        assert content == "# Slide 2\n\nFine"

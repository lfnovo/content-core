"""E2E tests for remote file extraction — require network access."""
import pytest

pytestmark = pytest.mark.e2e
from content_core.extraction import extract_content


@pytest.mark.asyncio
async def test_extract_content_from_pdf_url():
    """Tests extracting content from a remote PDF URL."""
    url = "https://arxiv.org/pdf/2408.09869"
    result = await extract_content(url=url)
    assert result.source_type == "url"
    assert result.identified_type == "application/pdf"
    assert len(result.content) > 100

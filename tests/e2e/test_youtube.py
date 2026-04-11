"""E2E tests for YouTube extraction — require network access."""
import pytest
from content_core.extraction import extract_content


@pytest.mark.asyncio
async def test_extract_content_from_youtube_url():
    """Tests extracting content from a YouTube URL."""
    youtube_url = "https://www.youtube.com/watch?v=pBy1zgt0XPc"
    result = await extract_content(dict(url=youtube_url))

    assert result.source_type == "url"
    assert result.identified_type == "youtube"
    assert "What is GitHub?" in result.title
    assert "github" in result.content.lower()
    assert "code" in result.content.lower()
    assert "git" in result.content.lower()
    assert len(result.content) > 50

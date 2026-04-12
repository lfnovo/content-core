"""E2E tests for media extraction — require OpenAI STT API."""
from pathlib import Path

import pytest
from content_core.extraction import extract_content


@pytest.fixture
def fixture_path():
    """Provides the path to the directory containing test input files."""
    return Path(__file__).parent.parent / "input_content"


@pytest.mark.asyncio
async def test_extract_content_from_mp3(fixture_path):
    """Tests content extraction (transcript) from an MP3 file."""
    mp3_file = fixture_path / "file.mp3"
    if not mp3_file.exists():
        pytest.skip(f"Fixture file not found: {mp3_file}")

    input_data = {"file_path": str(mp3_file)}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "file"
    assert result.title == "file.mp3"
    assert result.identified_type.startswith("audio/")
    assert "welcome" in result.content.lower()


@pytest.mark.asyncio
async def test_extract_content_from_mp4(fixture_path):
    """Tests content extraction (transcript) from an MP4 file."""
    mp4_file = fixture_path / "file.mp4"
    if not mp4_file.exists():
        pytest.skip(f"Fixture file not found: {mp4_file}")

    input_data = {"file_path": str(mp4_file)}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "file"
    assert result.title == "file.mp4"
    assert result.identified_type.startswith("video/")
    assert "welcome" in result.content.lower()

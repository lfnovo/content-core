"""
Unit tests for vision-based extraction processors.

Tests verify that:
1. Image processor analyzes images with vision model when configured
2. Image processor returns placeholder when no vision model configured
3. Video vision processor extracts frames and analyzes them
4. PDF vision processor converts pages and analyzes them
5. Graph routing selects vision processors when config is present
6. Backward compatibility maintained when no vision config
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_core.common import ProcessSourceState


def _mock_create_image_message(image_source, prompt="", **kwargs):
    """Mock create_image_message that doesn't read files."""
    return {"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,fakedata"}},
    ]}


class TestImageProcessor:
    """Tests for the image extraction processor."""

    @pytest.mark.asyncio
    async def test_image_extraction_with_vision_model(self):
        """Test image analysis when vision model is configured."""
        state = ProcessSourceState(
            file_path="/fake/image.png",
            vision_provider="openai",
            vision_model="gpt-4o",
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="A photo of a cat sitting on a table."))
        ]

        # Create mock modules for esperanto.utils.vision
        mock_vision_module = MagicMock()
        mock_vision_module.create_image_message = _mock_create_image_message

        mock_ai_factory = MagicMock()
        mock_model = MagicMock()
        mock_model.achat_complete = AsyncMock(return_value=mock_response)
        mock_ai_factory.create_language.return_value = mock_model

        with patch.dict(sys.modules, {
            "esperanto.utils.vision": mock_vision_module,
        }):
            with patch("esperanto.AIFactory", mock_ai_factory):
                from content_core.processors.image import extract_image

                result = await extract_image(state)

        assert "A photo of a cat sitting on a table." in result["content"]
        assert result["title"] == "image.png"
        mock_ai_factory.create_language.assert_called_once_with(
            "openai", "gpt-4o", config=None
        )

    @pytest.mark.asyncio
    async def test_image_extraction_without_vision_model(self):
        """Test image returns placeholder when no vision config."""
        state = ProcessSourceState(
            file_path="/fake/image.png",
        )

        from content_core.processors.image import extract_image

        result = await extract_image(state)

        assert "no vision model configured" in result["content"]
        assert result["title"] == "image.png"

    @pytest.mark.asyncio
    async def test_image_extraction_handles_error(self):
        """Test image processor handles analysis errors gracefully."""
        state = ProcessSourceState(
            file_path="/fake/image.png",
            vision_provider="openai",
            vision_model="gpt-4o",
        )

        mock_vision_module = MagicMock()
        mock_vision_module.create_image_message = _mock_create_image_message

        with patch.dict(sys.modules, {
            "esperanto.utils.vision": mock_vision_module,
        }):
            with patch("esperanto.AIFactory") as mock_factory:
                mock_factory.create_language.side_effect = Exception("API error")

                from content_core.processors.image import extract_image

                result = await extract_image(state)

        assert "analysis failed" in result["content"]


class TestVideoVisionProcessor:
    """Tests for the video vision extraction processor."""

    @pytest.mark.asyncio
    async def test_video_vision_extraction(self):
        """Test video vision processing with mocked ffmpeg and model."""
        state = ProcessSourceState(
            file_path="/fake/video.mp4",
            vision_provider="openai",
            vision_model="gpt-4o",
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="A person walking in a park."))
        ]

        with patch(
            "content_core.processors.video_vision.get_video_duration",
            new_callable=AsyncMock,
            return_value=30.0,
        ):
            with patch(
                "content_core.processors.video_vision.extract_frames",
                new_callable=AsyncMock,
                return_value=[("/tmp/frame_0001.jpg", 0.0), ("/tmp/frame_0002.jpg", 1.0)],
            ):
                mock_vision_module = MagicMock()
                mock_vision_module.create_image_message = _mock_create_image_message

                mock_ai_factory = MagicMock()
                mock_model_inst = MagicMock()
                mock_model_inst.achat_complete = AsyncMock(return_value=mock_response)
                mock_ai_factory.create_language.return_value = mock_model_inst

                with patch.dict(sys.modules, {
                    "esperanto.utils.vision": mock_vision_module,
                }):
                    with patch("esperanto.AIFactory", mock_ai_factory):
                        with patch(
                            "content_core.processors.video_vision.cleanup_temp_files"
                        ):
                            from content_core.processors.video_vision import (
                                extract_video_with_vision,
                            )

                            result = await extract_video_with_vision(state)

        assert "Video Analysis" in result["content"]
        assert result["title"] == "video.mp4"
        assert result["metadata"]["frames_analyzed"] == 2
        mock_ai_factory.create_language.assert_called_once_with(
            "openai", "gpt-4o", config=None
        )


class TestPdfVisionProcessor:
    """Tests for the PDF vision extraction processor."""

    @pytest.mark.asyncio
    async def test_pdf_vision_extraction(self):
        """Test PDF vision processing with mocked pdftoppm and model."""
        state = ProcessSourceState(
            file_path="/fake/document.pdf",
            identified_type="application/pdf",
            vision_provider="anthropic",
            vision_model="claude-sonnet-4-5-20250929",
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Page contains a table of financial data."))
        ]

        with patch(
            "content_core.processors.pdf_vision.convert_pdf_to_images",
            new_callable=AsyncMock,
            return_value=[("/tmp/page_0001.png", 1), ("/tmp/page_0002.png", 2)],
        ):
            mock_vision_module = MagicMock()
            mock_vision_module.create_image_message = _mock_create_image_message

            mock_ai_factory = MagicMock()
            mock_model_inst = MagicMock()
            mock_model_inst.achat_complete = AsyncMock(return_value=mock_response)
            mock_ai_factory.create_language.return_value = mock_model_inst

            with patch.dict(sys.modules, {
                "esperanto.utils.vision": mock_vision_module,
            }):
                with patch("esperanto.AIFactory", mock_ai_factory):
                    from content_core.processors.pdf_vision import (
                        extract_pdf_with_vision,
                    )

                    result = await extract_pdf_with_vision(state)

        assert "Document: document.pdf" in result["content"]
        assert "Page 1" in result["content"]
        assert "Page 2" in result["content"]
        mock_ai_factory.create_language.assert_called_once_with(
            "anthropic", "claude-sonnet-4-5-20250929", config=None
        )


class TestFrameParams:
    """Tests for adaptive frame/page sampling parameters."""

    def test_short_video_params(self):
        from content_core.processors.video_vision import calculate_frame_params

        fps, max_frames = calculate_frame_params(30.0)
        assert fps == 1.0
        assert max_frames == 60

    def test_medium_video_params(self):
        from content_core.processors.video_vision import calculate_frame_params

        fps, max_frames = calculate_frame_params(180.0)
        assert fps == 0.5
        assert max_frames == 150

    def test_long_video_params(self):
        from content_core.processors.video_vision import calculate_frame_params

        fps, max_frames = calculate_frame_params(600.0)
        assert fps == 0.2
        assert max_frames == 180

    def test_very_long_video_params(self):
        from content_core.processors.video_vision import calculate_frame_params

        fps, max_frames = calculate_frame_params(3600.0)
        assert fps == 0.1
        assert max_frames == 180


class TestPageParams:
    """Tests for adaptive PDF page sampling parameters."""

    def test_short_pdf_params(self):
        from content_core.processors.pdf_vision import calculate_page_params

        step, max_pages = calculate_page_params(10)
        assert step == 1
        assert max_pages == 20

    def test_medium_pdf_params(self):
        from content_core.processors.pdf_vision import calculate_page_params

        step, max_pages = calculate_page_params(50)
        assert step == 2
        assert max_pages == 50

    def test_long_pdf_params(self):
        from content_core.processors.pdf_vision import calculate_page_params

        step, max_pages = calculate_page_params(200)
        assert step == 5
        assert max_pages == 100

    def test_very_long_pdf_params(self):
        from content_core.processors.pdf_vision import calculate_page_params

        step, max_pages = calculate_page_params(1000)
        assert step == 10
        assert max_pages == 100


class TestGraphRouting:
    """Tests for extraction graph routing with vision config."""

    @pytest.mark.asyncio
    async def test_image_routing(self):
        """Test that images route to extract_image."""
        from content_core.content.extraction.graph import file_type_edge

        state = ProcessSourceState(
            file_path="/fake/photo.jpg",
            identified_type="image/jpeg",
        )
        result = await file_type_edge(state)
        assert result == "extract_image"

    @pytest.mark.asyncio
    async def test_video_routes_to_vision_when_configured(self):
        """Test video routes to vision processor when vision model is set."""
        from content_core.content.extraction.graph import file_type_edge

        state = ProcessSourceState(
            file_path="/fake/video.mp4",
            identified_type="video/mp4",
            vision_provider="openai",
            vision_model="gpt-4o",
        )
        result = await file_type_edge(state)
        assert result == "extract_video_with_vision"

    @pytest.mark.asyncio
    async def test_video_routes_to_audio_when_no_vision(self):
        """Test video routes to audio extraction without vision config."""
        from content_core.content.extraction.graph import file_type_edge

        state = ProcessSourceState(
            file_path="/fake/video.mp4",
            identified_type="video/mp4",
        )
        result = await file_type_edge(state)
        assert result == "extract_best_audio_from_video"

    @pytest.mark.asyncio
    async def test_pdf_routes_to_vision_when_configured(self):
        """Test PDF routes to vision processor when vision model is set."""
        from content_core.content.extraction.graph import file_type_edge

        state = ProcessSourceState(
            file_path="/fake/doc.pdf",
            identified_type="application/pdf",
            vision_provider="anthropic",
            vision_model="claude-sonnet-4-5-20250929",
        )
        result = await file_type_edge(state)
        assert result == "extract_pdf_with_vision"

    @pytest.mark.asyncio
    async def test_pdf_routes_to_fitz_when_no_vision(self):
        """Test PDF routes to PyMuPDF extraction without vision config."""
        from content_core.content.extraction.graph import file_type_edge

        state = ProcessSourceState(
            file_path="/fake/doc.pdf",
            identified_type="application/pdf",
        )
        result = await file_type_edge(state)
        assert result == "extract_pdf"

    @pytest.mark.asyncio
    async def test_audio_routing_unchanged(self):
        """Test audio routing is unchanged."""
        from content_core.content.extraction.graph import file_type_edge

        state = ProcessSourceState(
            file_path="/fake/audio.mp3",
            identified_type="audio/mpeg",
        )
        result = await file_type_edge(state)
        assert result == "extract_audio_data"

    @pytest.mark.asyncio
    async def test_text_routing_unchanged(self):
        """Test text routing is unchanged."""
        from content_core.content.extraction.graph import file_type_edge

        state = ProcessSourceState(
            file_path="/fake/notes.txt",
            identified_type="text/plain",
        )
        result = await file_type_edge(state)
        assert result == "extract_txt"


class TestStateModel:
    """Tests for vision fields in ProcessSourceState."""

    def test_state_has_vision_fields(self):
        """Test that state model accepts vision config fields."""
        state = ProcessSourceState(
            file_path="/fake/image.png",
            vision_provider="openai",
            vision_model="gpt-4o",
        )
        assert state.vision_provider == "openai"
        assert state.vision_model == "gpt-4o"

    def test_state_vision_fields_default_none(self):
        """Test that vision fields default to None."""
        state = ProcessSourceState(file_path="/fake/file.txt")
        assert state.vision_provider is None
        assert state.vision_model is None

    def test_input_has_vision_fields(self):
        """Test that input model accepts vision config fields."""
        from content_core.common import ProcessSourceInput

        input_state = ProcessSourceInput(
            file_path="/fake/image.png",
            vision_provider="anthropic",
            vision_model="claude-sonnet-4-5-20250929",
        )
        assert input_state.vision_provider == "anthropic"
        assert input_state.vision_model == "claude-sonnet-4-5-20250929"

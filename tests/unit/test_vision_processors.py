"""Unit tests for vision-based extraction processors (v2).

Tests verify that:
1. Image processor analyzes images with vision model when configured.
2. Image processor returns placeholder when no vision model configured.
3. Video vision processor extracts frames and analyzes them.
4. PDF vision processor converts pages and analyzes them.
5. extraction.py routes to vision processors when vision config is present.
6. Backward compatibility maintained when no vision config.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_core.config import ContentCoreConfig


def _mock_create_image_message(image_source, prompt="", **kwargs):
    """Mock create_image_message that doesn't read files."""
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,fakedata"}},
        ],
    }


def _vision_cfg(provider="openai", model="gpt-4o", **overrides) -> ContentCoreConfig:
    overrides.setdefault("document_engine", "simple")
    return ContentCoreConfig(
        vision_provider=provider, vision_model=model, **overrides
    )


def _no_vision_cfg(**overrides) -> ContentCoreConfig:
    overrides.setdefault("document_engine", "simple")
    return ContentCoreConfig(**overrides)


class TestImageProcessor:
    @pytest.mark.asyncio
    async def test_image_extraction_with_vision_model(self):
        cfg = _vision_cfg()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="A photo of a cat sitting on a table."))
        ]

        mock_vision_module = MagicMock()
        mock_vision_module.create_image_message = _mock_create_image_message

        mock_ai_factory = MagicMock()
        mock_model = MagicMock()
        mock_model.achat_complete = AsyncMock(return_value=mock_response)
        mock_ai_factory.create_language.return_value = mock_model

        with patch.dict(sys.modules, {"esperanto.utils.vision": mock_vision_module}):
            with patch("esperanto.AIFactory", mock_ai_factory):
                from content_core.processors.document.image import extract_image

                result = await extract_image("/fake/image.png", cfg)

        assert "A photo of a cat sitting on a table." in result.content
        assert result.title == "image.png"
        assert result.source_type == "file"
        mock_ai_factory.create_language.assert_called_once_with(
            "openai", "gpt-4o", config=None
        )

    @pytest.mark.asyncio
    async def test_image_extraction_without_vision_model(self):
        cfg = _no_vision_cfg()

        from content_core.processors.document.image import extract_image

        result = await extract_image("/fake/image.png", cfg)

        assert "no vision model configured" in result.content
        assert result.title == "image.png"

    @pytest.mark.asyncio
    async def test_image_extraction_handles_error(self):
        cfg = _vision_cfg()

        mock_vision_module = MagicMock()
        mock_vision_module.create_image_message = _mock_create_image_message

        with patch.dict(sys.modules, {"esperanto.utils.vision": mock_vision_module}):
            with patch("esperanto.AIFactory") as mock_factory:
                mock_factory.create_language.side_effect = Exception("API error")

                from content_core.processors.document.image import extract_image

                result = await extract_image("/fake/image.png", cfg)

        assert "analysis failed" in result.content


class TestVideoVisionProcessor:
    @pytest.mark.asyncio
    async def test_video_vision_extraction(self):
        cfg = _vision_cfg()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="A person walking in a park."))
        ]

        mock_vision_module = MagicMock()
        mock_vision_module.create_image_message = _mock_create_image_message

        mock_ai_factory = MagicMock()
        mock_model_inst = MagicMock()
        mock_model_inst.achat_complete = AsyncMock(return_value=mock_response)
        mock_ai_factory.create_language.return_value = mock_model_inst

        with patch(
            "content_core.processors.media.video_vision.get_video_duration",
            new_callable=AsyncMock,
            return_value=30.0,
        ), patch(
            "content_core.processors.media.video_vision.extract_frames",
            new_callable=AsyncMock,
            return_value=[("/tmp/frame_0001.jpg", 0.0), ("/tmp/frame_0002.jpg", 1.0)],
        ), patch(
            "content_core.processors.media.video_vision._transcribe_video_audio",
            new_callable=AsyncMock,
            return_value="",
        ), patch(
            "content_core.processors.media.video_vision.cleanup_temp_files"
        ), patch.dict(
            sys.modules, {"esperanto.utils.vision": mock_vision_module}
        ), patch("esperanto.AIFactory", mock_ai_factory):
            from content_core.processors.media.video_vision import (
                extract_video_with_vision,
            )

            result = await extract_video_with_vision("/fake/video.mp4", cfg)

        assert "Video Analysis" in result.content
        assert result.title == "video.mp4"
        assert result.metadata["frames_analyzed"] == 2
        mock_ai_factory.create_language.assert_called_once_with(
            "openai", "gpt-4o", config=None
        )


class TestPdfVisionProcessor:
    @pytest.mark.asyncio
    async def test_pdf_vision_extraction(self):
        cfg = _vision_cfg("anthropic", "claude-sonnet-4-5-20250929")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Page contains a table of financial data."))
        ]

        mock_vision_module = MagicMock()
        mock_vision_module.create_image_message = _mock_create_image_message

        mock_ai_factory = MagicMock()
        mock_model_inst = MagicMock()
        mock_model_inst.achat_complete = AsyncMock(return_value=mock_response)
        mock_ai_factory.create_language.return_value = mock_model_inst

        with patch(
            "content_core.processors.document.pdf_vision.convert_pdf_to_images",
            new_callable=AsyncMock,
            return_value=[("/tmp/page_0001.png", 1), ("/tmp/page_0002.png", 2)],
        ), patch.dict(
            sys.modules, {"esperanto.utils.vision": mock_vision_module}
        ), patch("esperanto.AIFactory", mock_ai_factory):
            from content_core.processors.document.pdf_vision import (
                extract_pdf_with_vision,
            )

            result = await extract_pdf_with_vision("/fake/document.pdf", cfg)

        assert "Document: document.pdf" in result.content
        assert "Page 1" in result.content
        assert "Page 2" in result.content
        mock_ai_factory.create_language.assert_called_once_with(
            "anthropic", "claude-sonnet-4-5-20250929", config=None
        )


class TestFrameParams:
    def test_short_video_params(self):
        from content_core.processors.media.video_vision import calculate_frame_params

        fps, max_frames = calculate_frame_params(30.0)
        assert fps == 1.0
        assert max_frames == 60

    def test_medium_video_params(self):
        from content_core.processors.media.video_vision import calculate_frame_params

        fps, max_frames = calculate_frame_params(180.0)
        assert fps == 0.5
        assert max_frames == 150

    def test_long_video_params(self):
        from content_core.processors.media.video_vision import calculate_frame_params

        fps, max_frames = calculate_frame_params(600.0)
        assert fps == 0.2
        assert max_frames == 180

    def test_very_long_video_params(self):
        from content_core.processors.media.video_vision import calculate_frame_params

        fps, max_frames = calculate_frame_params(3600.0)
        assert fps == 0.1
        assert max_frames == 180


class TestPageParams:
    def test_short_pdf_params(self):
        from content_core.processors.document.pdf_vision import calculate_page_params

        step, max_pages = calculate_page_params(10)
        assert step == 1
        assert max_pages == 10

    def test_medium_pdf_params(self):
        from content_core.processors.document.pdf_vision import calculate_page_params

        step, max_pages = calculate_page_params(50)
        assert step == 1
        assert max_pages == 50

    def test_long_pdf_params(self):
        from content_core.processors.document.pdf_vision import calculate_page_params

        step, max_pages = calculate_page_params(200)
        assert step == 1
        assert max_pages == 200

    def test_very_long_pdf_params(self):
        from content_core.processors.document.pdf_vision import calculate_page_params

        step, max_pages = calculate_page_params(1000)
        assert step == 1
        assert max_pages == 1000


class TestExtractionRouting:
    """Vision-aware routing inside `extraction.py::_extract_file`."""

    @pytest.mark.asyncio
    async def test_image_routes_to_extract_image(self):
        from content_core.common.state import ExtractionOutput
        from content_core.extraction import _extract_file

        cfg = _no_vision_cfg()

        with patch(
            "content_core.content.identification.get_file_type",
            new_callable=AsyncMock,
            return_value="image/jpeg",
        ), patch(
            "content_core.extraction.extract_image",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="img", title="photo.jpg"),
        ) as mock_image:
            result = await _extract_file("/fake/photo.jpg", cfg)

        mock_image.assert_awaited_once()
        assert result.content == "img"
        assert result.identified_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_pdf_routes_to_vision_when_configured(self):
        from content_core.common.state import ExtractionOutput
        from content_core.extraction import _extract_file

        cfg = _vision_cfg("anthropic", "claude-sonnet-4-5-20250929")

        with patch(
            "content_core.content.identification.get_file_type",
            new_callable=AsyncMock,
            return_value="application/pdf",
        ), patch(
            "content_core.extraction.extract_pdf_with_vision",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="vision pdf", title="doc.pdf"),
        ) as mock_vision, patch(
            "content_core.extraction.extract_pdf_file",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="plain pdf", title="doc.pdf"),
        ) as mock_plain:
            result = await _extract_file("/fake/doc.pdf", cfg)

        mock_vision.assert_awaited_once()
        mock_plain.assert_not_awaited()
        assert "vision pdf" in result.content

    @pytest.mark.asyncio
    async def test_pdf_routes_to_plain_when_no_vision(self):
        from content_core.common.state import ExtractionOutput
        from content_core.extraction import _extract_file

        cfg = _no_vision_cfg()

        with patch(
            "content_core.content.identification.get_file_type",
            new_callable=AsyncMock,
            return_value="application/pdf",
        ), patch(
            "content_core.extraction.extract_pdf_with_vision",
            new_callable=AsyncMock,
        ) as mock_vision, patch(
            "content_core.extraction.extract_pdf_file",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="plain pdf", title="doc.pdf"),
        ) as mock_plain:
            result = await _extract_file("/fake/doc.pdf", cfg)

        mock_plain.assert_awaited_once()
        mock_vision.assert_not_awaited()
        assert "plain pdf" in result.content

    @pytest.mark.asyncio
    async def test_video_routes_to_vision_when_configured(self):
        from content_core.common.state import ExtractionOutput
        from content_core.extraction import _extract_file

        cfg = _vision_cfg()

        with patch(
            "content_core.content.identification.get_file_type",
            new_callable=AsyncMock,
            return_value="video/mp4",
        ), patch(
            "content_core.extraction.extract_video_with_vision",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="vision video", title="v.mp4"),
        ) as mock_vision, patch(
            "content_core.extraction.extract_video",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="audio video", title="v.mp4"),
        ) as mock_plain:
            result = await _extract_file("/fake/v.mp4", cfg)

        mock_vision.assert_awaited_once()
        mock_plain.assert_not_awaited()
        assert "vision video" in result.content

    @pytest.mark.asyncio
    async def test_video_routes_to_audio_when_no_vision(self):
        from content_core.common.state import ExtractionOutput
        from content_core.extraction import _extract_file

        cfg = _no_vision_cfg()

        with patch(
            "content_core.content.identification.get_file_type",
            new_callable=AsyncMock,
            return_value="video/mp4",
        ), patch(
            "content_core.extraction.extract_video_with_vision",
            new_callable=AsyncMock,
        ) as mock_vision, patch(
            "content_core.extraction.extract_video",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="audio video", title="v.mp4"),
        ) as mock_plain:
            result = await _extract_file("/fake/v.mp4", cfg)

        mock_plain.assert_awaited_once()
        mock_vision.assert_not_awaited()
        assert "audio video" in result.content


class TestConfigVisionFields:
    def test_config_accepts_vision_fields(self):
        cfg = ContentCoreConfig(
            vision_provider="openai",
            vision_model="gpt-4o",
            vision_config={"api_key": "fake"},
        )
        assert cfg.vision_provider == "openai"
        assert cfg.vision_model == "gpt-4o"
        assert cfg.vision_config == {"api_key": "fake"}

    def test_config_vision_defaults_to_none(self):
        cfg = ContentCoreConfig()
        assert cfg.vision_provider is None
        assert cfg.vision_model is None
        assert cfg.vision_config is None

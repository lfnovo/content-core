"""Tests for EngineResolver and configuration resolution order.

Resolution order (v2.0 - ENV only):
1. Explicit engine param in extract_content() call
2. ENV var for specific MIME type (CCORE_ENGINE_APPLICATION_PDF)
3. ENV var for wildcard MIME type (CCORE_ENGINE_IMAGE)
4. ENV var for category (CCORE_ENGINE_DOCUMENTS)
5. Legacy config (document_engine/url_engine)
6. Auto-detect from registry
"""

from unittest.mock import MagicMock, patch

import pytest

from content_core.config import reset_config
from content_core.engine_config.resolver import (
    EngineResolver,
    _get_category_for_mime_type,
    _get_wildcard_mime_type,
)
from content_core.engine_config.schema import ExtractionConfig, FallbackConfig


class TestCategoryMapping:
    """Test MIME type to category mapping."""

    def test_pdf_is_documents(self):
        """PDF should map to documents category."""
        assert _get_category_for_mime_type("application/pdf") == "documents"

    def test_html_is_urls(self):
        """HTML should map to urls category."""
        assert _get_category_for_mime_type("text/html") == "urls"

    def test_youtube_is_urls(self):
        """YouTube special type should map to urls category."""
        assert _get_category_for_mime_type("youtube") == "urls"

    def test_image_wildcard_is_documents(self):
        """Image types should map to documents category."""
        assert _get_category_for_mime_type("image/png") == "documents"
        assert _get_category_for_mime_type("image/jpeg") == "documents"

    def test_audio_wildcard(self):
        """Audio types should map to audio category."""
        assert _get_category_for_mime_type("audio/mp3") == "audio"
        assert _get_category_for_mime_type("audio/wav") == "audio"

    def test_video_wildcard(self):
        """Video types should map to video category."""
        assert _get_category_for_mime_type("video/mp4") == "video"

    def test_unknown_mime_type(self):
        """Unknown MIME types should return None."""
        assert _get_category_for_mime_type("application/unknown") is None


class TestWildcardMimeType:
    """Test wildcard MIME type extraction."""

    def test_image_wildcard(self):
        """Should extract wildcard from image type."""
        assert _get_wildcard_mime_type("image/png") == "image/*"

    def test_no_slash(self):
        """Types without slash should return None."""
        assert _get_wildcard_mime_type("youtube") is None

    def test_application_wildcard(self):
        """Should extract wildcard from application type."""
        assert _get_wildcard_mime_type("application/pdf") == "application/*"


class TestEngineResolver:
    """Test EngineResolver resolution order."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_config()
        self.config = ExtractionConfig(
            engines={},  # No YAML engines in v2.0
            fallback=FallbackConfig(),
            document_engine="auto",
            url_engine="auto",
        )

    def teardown_method(self):
        reset_config()

    def test_explicit_engine_takes_priority(self):
        """Explicit engine param should take highest priority."""
        resolver = EngineResolver(self.config)
        with patch.object(resolver, "_registry"):
            engines = resolver.resolve("application/pdf", explicit="pymupdf4llm")
            assert engines == ["pymupdf4llm"]

    def test_explicit_engine_list(self):
        """Explicit engine list should be returned as-is."""
        resolver = EngineResolver(self.config)
        with patch.object(resolver, "_registry"):
            engines = resolver.resolve(
                "application/pdf", explicit=["docling-vlm", "docling"]
            )
            assert engines == ["docling-vlm", "docling"]

    def test_env_mime_type_override(self):
        """ENV var for specific MIME type should be used."""
        resolver = EngineResolver(self.config)
        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=["marker"],
        ):
            engines = resolver.resolve("application/pdf")
            assert engines == ["marker"]

    def test_env_wildcard_override(self):
        """ENV var for wildcard MIME type should be used."""
        resolver = EngineResolver(self.config)
        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_wildcard",
            return_value=["docling-vlm"],
        ):
            engines = resolver.resolve("image/png")
            assert engines == ["docling-vlm"]

    def test_env_category_override(self):
        """ENV var for category should be used."""
        resolver = EngineResolver(self.config)
        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_wildcard",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_category",
            return_value=["marker"],
        ):
            engines = resolver.resolve("application/pdf")
            assert engines == ["marker"]

    def test_legacy_document_engine(self):
        """Legacy document_engine should be used for documents."""
        config = ExtractionConfig(
            engines={},
            document_engine="docling",
            url_engine="jina",
        )
        resolver = EngineResolver(config)
        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_wildcard",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_category",
            return_value=None,
        ):
            engines = resolver.resolve("application/pdf")
            assert engines == ["docling"]

    def test_legacy_url_engine(self):
        """Legacy url_engine should be used for URLs."""
        config = ExtractionConfig(
            engines={},
            document_engine="docling",
            url_engine="jina",
        )
        resolver = EngineResolver(config)
        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_wildcard",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_category",
            return_value=None,
        ):
            engines = resolver.resolve("text/html")
            assert engines == ["jina"]

    def test_auto_detect_from_registry(self):
        """Should auto-detect from registry when no config matches."""
        config = ExtractionConfig(
            engines={},
            document_engine="auto",
            url_engine="auto",
        )
        resolver = EngineResolver(config)

        # Mock the registry
        mock_processor1 = MagicMock()
        mock_processor1.name = "docling"
        mock_processor1.is_available.return_value = True

        mock_processor2 = MagicMock()
        mock_processor2.name = "pymupdf"
        mock_processor2.is_available.return_value = True

        mock_registry = MagicMock()
        mock_registry.find_for_mime_type.return_value = [
            mock_processor1,
            mock_processor2,
        ]

        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_wildcard",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_category",
            return_value=None,
        ), patch.object(resolver, "_registry", mock_registry):
            engines = resolver.resolve("application/pdf")
            assert engines == ["docling", "pymupdf"]

    def test_no_engines_raises_error(self):
        """Should raise ValueError when no engines are found."""
        config = ExtractionConfig(
            engines={},
            document_engine="auto",
            url_engine="auto",
        )
        resolver = EngineResolver(config)

        mock_registry = MagicMock()
        mock_registry.find_for_mime_type.return_value = []
        mock_registry.list_names.return_value = ["docling", "pymupdf"]

        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_wildcard",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_category",
            return_value=None,
        ), patch.object(resolver, "_registry", mock_registry):
            with pytest.raises(ValueError) as exc_info:
                resolver.resolve("application/unknown")
            assert "No engines available" in str(exc_info.value)


class TestEngineOptions:
    """Test engine options retrieval."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_get_docling_options(self):
        """Should return docling options from config."""
        config = ExtractionConfig(engines={})
        resolver = EngineResolver(config)

        with patch.dict("os.environ", {}, clear=True):
            options = resolver.get_engine_options("docling")
            assert "do_ocr" in options
            assert "output_format" in options

    def test_get_marker_options(self):
        """Should return marker options from config."""
        config = ExtractionConfig(engines={})
        resolver = EngineResolver(config)

        with patch.dict("os.environ", {}, clear=True):
            options = resolver.get_engine_options("marker")
            assert "use_llm" in options
            assert "force_ocr" in options

    def test_get_pymupdf_options(self):
        """Should return pymupdf options from config."""
        config = ExtractionConfig(engines={})
        resolver = EngineResolver(config)

        with patch.dict("os.environ", {}, clear=True):
            options = resolver.get_engine_options("pymupdf")
            assert "enable_formula_ocr" in options
            assert "formula_threshold" in options

    def test_get_engine_options_unknown(self):
        """Should return empty dict for unknown engine."""
        config = ExtractionConfig(engines={})
        resolver = EngineResolver(config)

        options = resolver.get_engine_options("unknown")
        assert options == {}


class TestBackwardCompatibility:
    """Test backward compatibility with legacy config."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_legacy_document_engine_from_config(self):
        """Legacy document_engine in config should work."""
        config = ExtractionConfig(
            engines={},
            document_engine="docling",
        )
        resolver = EngineResolver(config)

        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_wildcard",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_category",
            return_value=None,
        ):
            engines = resolver.resolve("application/pdf")
            assert engines == ["docling"]

    def test_minimal_config_works(self):
        """Config with just document_engine: auto should work."""
        config = ExtractionConfig()  # All defaults
        resolver = EngineResolver(config)

        mock_processor = MagicMock()
        mock_processor.name = "docling"
        mock_processor.is_available.return_value = True

        mock_registry = MagicMock()
        mock_registry.find_for_mime_type.return_value = [mock_processor]

        with patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_mime_type",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_wildcard",
            return_value=None,
        ), patch(
            "content_core.engine_config.resolver.get_engine_chain_from_env_for_category",
            return_value=None,
        ), patch.object(resolver, "_registry", mock_registry):
            engines = resolver.resolve("application/pdf")
            assert engines == ["docling"]

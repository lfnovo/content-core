"""Tests for configuration functions and environment variable handling."""
from unittest.mock import patch
from content_core.config import (
    get_document_engine,
    get_url_engine,
    get_firecrawl_api_url,
    set_firecrawl_api_url,
    DEFAULT_FIRECRAWL_API_URL,
    ALLOWED_DOCUMENT_ENGINES,
    ALLOWED_URL_ENGINES,
    CONFIG,
)


class TestDocumentEngineSelection:
    """Test document engine selection with environment variables."""
    
    def test_default_document_engine(self):
        """Test default document engine when no env var is set."""
        with patch.dict('os.environ', {}, clear=False):
            # Remove the env var if it exists
            if 'CCORE_DOCUMENT_ENGINE' in __import__('os').environ:
                del __import__('os').environ['CCORE_DOCUMENT_ENGINE']
            engine = get_document_engine()
            assert engine == "auto"  # Default from config
    
    def test_valid_document_engine_env_var(self):
        """Test valid document engine environment variable override."""
        for engine in ALLOWED_DOCUMENT_ENGINES:
            with patch.dict('os.environ', {'CCORE_DOCUMENT_ENGINE': engine}):
                assert get_document_engine() == engine
    
    def test_invalid_document_engine_env_var(self):
        """Test invalid document engine environment variable falls back to default."""
        with patch.dict('os.environ', {'CCORE_DOCUMENT_ENGINE': 'invalid_engine'}):
            engine = get_document_engine()
            assert engine == "auto"  # Should fallback to default
    
    def test_case_sensitive_document_engine_env_var(self):
        """Test that document engine environment variable is case sensitive."""
        with patch.dict('os.environ', {'CCORE_DOCUMENT_ENGINE': 'AUTO'}):  # uppercase
            engine = get_document_engine()
            assert engine == "auto"  # Should fallback to default


class TestUrlEngineSelection:
    """Test URL engine selection with environment variables."""
    
    def test_default_url_engine(self):
        """Test default URL engine when no env var is set."""
        with patch.dict('os.environ', {}, clear=False):
            # Remove the env var if it exists
            if 'CCORE_URL_ENGINE' in __import__('os').environ:
                del __import__('os').environ['CCORE_URL_ENGINE']
            engine = get_url_engine()
            assert engine == "auto"  # Default from config
    
    def test_valid_url_engine_env_var(self):
        """Test valid URL engine environment variable override."""
        for engine in ALLOWED_URL_ENGINES:
            with patch.dict('os.environ', {'CCORE_URL_ENGINE': engine}):
                assert get_url_engine() == engine
    
    def test_invalid_url_engine_env_var(self):
        """Test invalid URL engine environment variable falls back to default."""
        with patch.dict('os.environ', {'CCORE_URL_ENGINE': 'invalid_engine'}):
            engine = get_url_engine()
            assert engine == "auto"  # Should fallback to default
    
    def test_case_sensitive_url_engine_env_var(self):
        """Test that URL engine environment variable is case sensitive."""
        with patch.dict('os.environ', {'CCORE_URL_ENGINE': 'FIRECRAWL'}):  # uppercase
            engine = get_url_engine()
            assert engine == "auto"  # Should fallback to default


class TestEngineConstants:
    """Test that engine constants contain expected values."""
    
    def test_document_engine_constants(self):
        """Test document engine allowed values."""
        expected = {"auto", "simple", "docling"}
        assert ALLOWED_DOCUMENT_ENGINES == expected
    
    def test_url_engine_constants(self):
        """Test URL engine allowed values."""
        expected = {"auto", "simple", "firecrawl", "jina", "crawl4ai"}
        assert ALLOWED_URL_ENGINES == expected


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_string_document_engine(self):
        """Test empty string for document engine env var."""
        with patch.dict('os.environ', {'CCORE_DOCUMENT_ENGINE': ''}):
            # Empty string should be falsy and use default
            engine = get_document_engine()
            assert engine == "auto"
    
    def test_empty_string_url_engine(self):
        """Test empty string for URL engine env var."""
        with patch.dict('os.environ', {'CCORE_URL_ENGINE': ''}):
            # Empty string should be falsy and use default
            engine = get_url_engine()
            assert engine == "auto"
    
    def test_whitespace_engine_values(self):
        """Test whitespace in engine values are treated as invalid."""
        with patch.dict('os.environ', {'CCORE_DOCUMENT_ENGINE': ' auto '}):
            engine = get_document_engine()
            assert engine == "auto"  # Should fallback to default


class TestFirecrawlApiUrl:
    """Test Firecrawl API URL configuration."""

    def test_default_firecrawl_api_url(self):
        """Test default Firecrawl API URL when nothing is configured."""
        # Clear env var and config
        with patch.dict('os.environ', {}, clear=False):
            if 'FIRECRAWL_API_BASE_URL' in __import__('os').environ:
                del __import__('os').environ['FIRECRAWL_API_BASE_URL']
            # Clear config override
            if 'extraction' in CONFIG and 'firecrawl' in CONFIG['extraction']:
                CONFIG['extraction']['firecrawl']['api_url'] = None
            url = get_firecrawl_api_url()
            assert url == DEFAULT_FIRECRAWL_API_URL
            assert url == "https://api.firecrawl.dev"

    def test_env_var_override(self):
        """Test environment variable overrides default."""
        custom_url = "http://localhost:3002"
        with patch.dict('os.environ', {'FIRECRAWL_API_BASE_URL': custom_url}):
            url = get_firecrawl_api_url()
            assert url == custom_url

    def test_yaml_config_override(self):
        """Test YAML config overrides default when env var not set."""
        custom_url = "http://firecrawl.internal:3002"
        with patch.dict('os.environ', {}, clear=False):
            if 'FIRECRAWL_API_BASE_URL' in __import__('os').environ:
                del __import__('os').environ['FIRECRAWL_API_BASE_URL']
            # Set config
            CONFIG.setdefault('extraction', {}).setdefault('firecrawl', {})['api_url'] = custom_url
            try:
                url = get_firecrawl_api_url()
                assert url == custom_url
            finally:
                # Clean up
                CONFIG['extraction']['firecrawl']['api_url'] = None

    def test_env_var_takes_precedence_over_config(self):
        """Test environment variable takes precedence over YAML config."""
        env_url = "http://env-firecrawl:3002"
        config_url = "http://config-firecrawl:3002"
        CONFIG.setdefault('extraction', {}).setdefault('firecrawl', {})['api_url'] = config_url
        try:
            with patch.dict('os.environ', {'FIRECRAWL_API_BASE_URL': env_url}):
                url = get_firecrawl_api_url()
                assert url == env_url
        finally:
            CONFIG['extraction']['firecrawl']['api_url'] = None

    def test_set_firecrawl_api_url(self):
        """Test programmatic override via set_firecrawl_api_url."""
        custom_url = "http://programmatic:3002"
        with patch.dict('os.environ', {}, clear=False):
            if 'FIRECRAWL_API_BASE_URL' in __import__('os').environ:
                del __import__('os').environ['FIRECRAWL_API_BASE_URL']
            try:
                set_firecrawl_api_url(custom_url)
                url = get_firecrawl_api_url()
                assert url == custom_url
            finally:
                # Clean up
                CONFIG['extraction']['firecrawl']['api_url'] = None
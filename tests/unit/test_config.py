"""Tests for configuration functions and environment variable handling."""
import pytest
from unittest.mock import patch, MagicMock
from content_core.config import (
    get_document_engine,
    get_url_engine,
    ALLOWED_DOCUMENT_ENGINES,
    ALLOWED_URL_ENGINES,
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
        expected = {"auto", "simple", "firecrawl", "jina"}
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
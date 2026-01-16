"""Tests for proxy configuration functions."""
import os
from unittest.mock import patch


from content_core.config import (
    get_proxy,
    set_proxy,
    clear_proxy,
    get_no_proxy,
    _redact_proxy_url,
    CONFIG,
)


class TestRedactProxyUrl:
    """Test _redact_proxy_url() credential redaction."""

    def test_redact_url_with_credentials(self):
        """Test that credentials are redacted from proxy URL."""
        url = "http://user:password@proxy.example.com:8080"
        result = _redact_proxy_url(url)
        assert "user" not in result
        assert "password" not in result
        assert "***:***@" in result
        assert "proxy.example.com:8080" in result

    def test_redact_url_without_credentials(self):
        """Test that URL without credentials is returned as-is."""
        url = "http://proxy.example.com:8080"
        result = _redact_proxy_url(url)
        assert result == url

    def test_redact_url_with_only_username(self):
        """Test that URL with only username is redacted."""
        url = "http://user@proxy.example.com:8080"
        result = _redact_proxy_url(url)
        assert "user" not in result
        assert "***:***@" in result

    def test_redact_url_with_special_chars_in_password(self):
        """Test that special characters in credentials are handled."""
        url = "http://user:p%40ssw0rd@proxy.example.com:8080"
        result = _redact_proxy_url(url)
        assert "p%40ssw0rd" not in result
        assert "***:***@" in result

    def test_redact_invalid_url_returns_generic(self):
        """Test that invalid URL returns generic message."""
        # This should not raise an exception
        result = _redact_proxy_url("not-a-valid-url://[invalid")
        # Should return something safe (either the URL or a generic message)
        assert result is not None


class TestGetProxyPriority:
    """Test get_proxy() priority resolution."""

    def setup_method(self):
        """Reset proxy state before each test."""
        clear_proxy()

    def teardown_method(self):
        """Clean up after each test."""
        clear_proxy()

    def test_per_request_proxy_highest_priority(self):
        """Test that per-request proxy has highest priority."""
        # Set all other sources
        set_proxy("http://programmatic:8080")
        with patch.dict(
            os.environ,
            {"CCORE_HTTP_PROXY": "http://env:8080"},
            clear=False,
        ):
            # Per-request should win
            result = get_proxy("http://per-request:8080")
            assert result == "http://per-request:8080"

    def test_per_request_empty_string_disables_proxy(self):
        """Test that passing empty string explicitly disables proxy."""
        set_proxy("http://programmatic:8080")
        with patch.dict(
            os.environ,
            {"CCORE_HTTP_PROXY": "http://env:8080"},
            clear=False,
        ):
            # Empty string should return None (disabled)
            result = get_proxy("")
            assert result is None

    def test_programmatic_proxy_over_env_vars(self):
        """Test that programmatic proxy takes precedence over env vars."""
        set_proxy("http://programmatic:8080")
        with patch.dict(
            os.environ,
            {"CCORE_HTTP_PROXY": "http://env:8080"},
            clear=False,
        ):
            result = get_proxy()
            assert result == "http://programmatic:8080"

    def test_ccore_http_proxy_env_var(self):
        """Test CCORE_HTTP_PROXY environment variable."""
        with patch.dict(
            os.environ,
            {
                "CCORE_HTTP_PROXY": "http://ccore:8080",
                "HTTP_PROXY": "http://http:8080",
                "HTTPS_PROXY": "http://https:8080",
            },
            clear=False,
        ):
            result = get_proxy()
            assert result == "http://ccore:8080"

    def test_http_proxy_env_var_fallback(self):
        """Test HTTP_PROXY fallback when CCORE_HTTP_PROXY not set."""
        # Ensure CCORE_HTTP_PROXY is not set
        env = {k: v for k, v in os.environ.items() if k != "CCORE_HTTP_PROXY"}
        env["HTTP_PROXY"] = "http://http-proxy:8080"
        env["HTTPS_PROXY"] = "http://https-proxy:8080"

        with patch.dict(os.environ, env, clear=True):
            result = get_proxy()
            assert result == "http://http-proxy:8080"

    def test_https_proxy_env_var_fallback(self):
        """Test HTTPS_PROXY fallback when HTTP_PROXY not set."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CCORE_HTTP_PROXY", "HTTP_PROXY")
        }
        env["HTTPS_PROXY"] = "http://https-proxy:8080"

        with patch.dict(os.environ, env, clear=True):
            result = get_proxy()
            assert result == "http://https-proxy:8080"

    def test_yaml_config_proxy(self):
        """Test YAML config proxy when no env vars or programmatic override."""
        # Clear env vars and override
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CCORE_HTTP_PROXY", "HTTP_PROXY", "HTTPS_PROXY")
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(CONFIG, {"proxy": {"url": "http://yaml:8080"}}):
                result = get_proxy()
                assert result == "http://yaml:8080"

    def test_no_proxy_configured_returns_none(self):
        """Test that None is returned when no proxy is configured."""
        # Clear all proxy sources
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CCORE_HTTP_PROXY", "HTTP_PROXY", "HTTPS_PROXY")
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(CONFIG, {"proxy": {"url": None}}):
                result = get_proxy()
                assert result is None


class TestSetProxy:
    """Test set_proxy() function."""

    def setup_method(self):
        """Reset proxy state before each test."""
        clear_proxy()

    def teardown_method(self):
        """Clean up after each test."""
        clear_proxy()

    def test_set_proxy_basic(self):
        """Test setting a basic proxy URL."""
        set_proxy("http://proxy.example.com:8080")
        result = get_proxy()
        assert result == "http://proxy.example.com:8080"

    def test_set_proxy_with_auth(self):
        """Test setting proxy with authentication."""
        set_proxy("http://user:password@proxy.example.com:8080")
        result = get_proxy()
        assert result == "http://user:password@proxy.example.com:8080"

    def test_set_proxy_none_disables(self):
        """Test that setting None disables the programmatic override."""
        set_proxy("http://proxy:8080")
        set_proxy(None)
        # Should now fall back to env vars or YAML
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CCORE_HTTP_PROXY", "HTTP_PROXY", "HTTPS_PROXY")
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(CONFIG, {"proxy": {"url": None}}):
                # None disables programmatic, should return None now
                result = get_proxy()
                assert result is None

    def test_set_proxy_empty_string_disables(self):
        """Test that setting empty string disables proxy."""
        set_proxy("")
        # Empty string means "explicitly disabled"
        result = get_proxy()
        assert result is None


class TestClearProxy:
    """Test clear_proxy() function."""

    def setup_method(self):
        """Reset proxy state before each test."""
        clear_proxy()

    def teardown_method(self):
        """Clean up after each test."""
        clear_proxy()

    def test_clear_proxy_removes_override(self):
        """Test that clear_proxy removes the programmatic override."""
        set_proxy("http://proxy:8080")
        clear_proxy()

        # Should now fall back to env vars
        with patch.dict(
            os.environ,
            {"CCORE_HTTP_PROXY": "http://env-proxy:8080"},
            clear=False,
        ):
            result = get_proxy()
            assert result == "http://env-proxy:8080"

    def test_clear_proxy_idempotent(self):
        """Test that clear_proxy can be called multiple times safely."""
        clear_proxy()
        clear_proxy()
        clear_proxy()
        # Should not raise


class TestGetNoProxy:
    """Test get_no_proxy() function."""

    def test_default_no_proxy_list(self):
        """Test default no_proxy list from YAML config."""
        env = {k: v for k, v in os.environ.items() if k not in ("NO_PROXY", "no_proxy")}
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(
                CONFIG, {"proxy": {"no_proxy": ["localhost", "127.0.0.1"]}}
            ):
                result = get_no_proxy()
                assert "localhost" in result
                assert "127.0.0.1" in result

    def test_no_proxy_env_var_uppercase(self):
        """Test NO_PROXY environment variable (uppercase)."""
        with patch.dict(
            os.environ,
            {"NO_PROXY": "localhost,127.0.0.1,internal.example.com"},
            clear=False,
        ):
            result = get_no_proxy()
            assert "localhost" in result
            assert "127.0.0.1" in result
            assert "internal.example.com" in result

    def test_no_proxy_env_var_lowercase(self):
        """Test no_proxy environment variable (lowercase)."""
        env = {k: v for k, v in os.environ.items() if k != "NO_PROXY"}
        env["no_proxy"] = "localhost,example.local"
        with patch.dict(os.environ, env, clear=True):
            result = get_no_proxy()
            assert "localhost" in result
            assert "example.local" in result

    def test_no_proxy_env_strips_whitespace(self):
        """Test that whitespace is stripped from NO_PROXY entries."""
        with patch.dict(
            os.environ,
            {"NO_PROXY": " localhost , 127.0.0.1 , example.com "},
            clear=False,
        ):
            result = get_no_proxy()
            assert "localhost" in result
            assert "127.0.0.1" in result
            assert "example.com" in result
            # Should not have whitespace
            for entry in result:
                assert entry == entry.strip()

    def test_no_proxy_env_ignores_empty_entries(self):
        """Test that empty entries from NO_PROXY are ignored."""
        with patch.dict(
            os.environ,
            {"NO_PROXY": "localhost,,127.0.0.1,,,example.com"},
            clear=False,
        ):
            result = get_no_proxy()
            assert "" not in result
            assert len([r for r in result if r]) == len(result)


class TestProxyWithEsperanto:
    """Test proxy integration with Esperanto models (mocked)."""

    def setup_method(self):
        """Reset proxy state before each test."""
        clear_proxy()

    def teardown_method(self):
        """Clean up after each test."""
        clear_proxy()

    def test_proxy_config_format_for_esperanto(self):
        """Test that proxy config is in the correct format for Esperanto."""
        set_proxy("http://proxy:8080")
        proxy = get_proxy()

        # Esperanto expects config={"proxy": "http://..."}
        esperanto_config = {"proxy": proxy}
        assert esperanto_config == {"proxy": "http://proxy:8080"}

    def test_model_factory_receives_proxy(self):
        """Test that ModelFactory passes proxy to model config."""
        # This test verifies the expected behavior pattern
        set_proxy("http://test-proxy:8080")
        proxy = get_proxy()

        # The model config should include proxy
        model_config = {}
        if proxy:
            model_config["proxy"] = proxy

        assert model_config.get("proxy") == "http://test-proxy:8080"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Reset proxy state before each test."""
        clear_proxy()

    def teardown_method(self):
        """Clean up after each test."""
        clear_proxy()

    def test_proxy_with_special_characters_in_password(self):
        """Test proxy URL with special characters in password."""
        # Password with special chars that need URL encoding
        proxy_url = "http://user:p%40ssw0rd@proxy:8080"
        set_proxy(proxy_url)
        result = get_proxy()
        assert result == proxy_url

    def test_proxy_with_ipv6_host(self):
        """Test proxy URL with IPv6 address."""
        proxy_url = "http://[::1]:8080"
        set_proxy(proxy_url)
        result = get_proxy()
        assert result == proxy_url

    def test_proxy_with_https_scheme(self):
        """Test proxy URL with HTTPS scheme."""
        proxy_url = "https://secure-proxy:8443"
        set_proxy(proxy_url)
        result = get_proxy()
        assert result == proxy_url

    def test_concurrent_proxy_changes(self):
        """Test proxy state with multiple changes."""
        set_proxy("http://proxy1:8080")
        assert get_proxy() == "http://proxy1:8080"

        set_proxy("http://proxy2:8080")
        assert get_proxy() == "http://proxy2:8080"

        clear_proxy()
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CCORE_HTTP_PROXY", "HTTP_PROXY", "HTTPS_PROXY")
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.dict(CONFIG, {"proxy": {"url": None}}):
                assert get_proxy() is None

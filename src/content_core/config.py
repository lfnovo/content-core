import os
import pkgutil
from typing import Any, Dict, cast

import yaml  # type: ignore[import]
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Allowed engine values for validation
ALLOWED_DOCUMENT_ENGINES = {"auto", "simple", "docling"}
ALLOWED_URL_ENGINES = {"auto", "simple", "firecrawl", "jina", "crawl4ai"}

# Allowed retry operation types
ALLOWED_RETRY_OPERATIONS = {
    "youtube",
    "url_api",
    "url_network",
    "audio",
    "llm",
    "download",
}

# Timeout validation bounds (seconds)
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 3600

# Default retry configurations (used when not in config file)
DEFAULT_RETRY_CONFIG = {
    "youtube": {"max_attempts": 5, "base_delay": 2, "max_delay": 60},
    "url_api": {"max_attempts": 3, "base_delay": 1, "max_delay": 30},
    "url_network": {"max_attempts": 3, "base_delay": 0.5, "max_delay": 10},
    "audio": {"max_attempts": 3, "base_delay": 2, "max_delay": 30},
    "llm": {"max_attempts": 3, "base_delay": 1, "max_delay": 30},
    "download": {"max_attempts": 3, "base_delay": 1, "max_delay": 15},
}


def _warn_invalid_timeout(var_name: str, value: str, reason: str):
    """Log a warning for invalid timeout overrides."""
    from content_core.logging import logger

    logger.warning(
        f"Invalid {var_name}: '{value}'. {reason} "
        f"(expected {MIN_TIMEOUT_SECONDS}-{MAX_TIMEOUT_SECONDS} seconds). "
        f"Using timeout from config."
    )


def _parse_timeout_env(var_name: str):
    """
    Parse timeout overrides from environment variables.

    Returns:
        int | None: Parsed timeout in seconds, or None if not provided/invalid.
    """
    value = os.environ.get(var_name)
    if value is None or value == "":
        return None

    try:
        timeout = int(value)
    except ValueError:
        _warn_invalid_timeout(var_name, value, "Must be an integer value")
        return None

    if timeout < MIN_TIMEOUT_SECONDS or timeout > MAX_TIMEOUT_SECONDS:
        _warn_invalid_timeout(
            var_name,
            value,
            f"Must be between {MIN_TIMEOUT_SECONDS} and {MAX_TIMEOUT_SECONDS} seconds",
        )
        return None

    return timeout


def apply_timeout_env_overrides(config: dict):
    """
    Apply environment variable overrides for Esperanto timeouts.

    Priority order (highest to lowest):
    1. YAML configuration defaults
    2. Environment variables (ESPERANTO_LLM_TIMEOUT / ESPERANTO_STT_TIMEOUT) used as fallback when YAML does not set a timeout
    """
    if not isinstance(config, dict):
        return

    llm_timeout = _parse_timeout_env("ESPERANTO_LLM_TIMEOUT")
    if llm_timeout is not None:
        for alias in ("default_model", "cleanup_model", "summary_model"):
            alias_cfg = config.setdefault(alias, {})
            model_cfg = alias_cfg.setdefault("config", {})
            if "timeout" not in model_cfg or model_cfg["timeout"] is None:
                model_cfg["timeout"] = llm_timeout

    stt_timeout = _parse_timeout_env("ESPERANTO_STT_TIMEOUT")
    if stt_timeout is not None:
        stt_cfg = config.setdefault("speech_to_text", {})
        if "timeout" not in stt_cfg or stt_cfg["timeout"] is None:
            stt_cfg["timeout"] = stt_timeout


def load_config() -> Dict[str, Any]:
    config_path = os.environ.get("CCORE_CONFIG_PATH") or os.environ.get(
        "CCORE_MODEL_CONFIG_PATH"
    )
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r") as file:
                return yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading configuration file from {config_path}: {e}")
            print("Using internal default settings.")

    default_config_data = pkgutil.get_data("content_core", "models_config.yaml")
    if default_config_data:
        base = yaml.safe_load(default_config_data)
    else:
        base = {}
    # load new cc_config.yaml defaults
    cc_default = pkgutil.get_data("content_core", "cc_config.yaml")
    if cc_default:
        cc_cfg = yaml.safe_load(cc_default)
        # merge extraction section
        base["extraction"] = cc_cfg.get("extraction", {})
        # merge proxy section
        base["proxy"] = cc_cfg.get("proxy", {})
    return base or {}


CONFIG: Dict[str, Any] = load_config()
apply_timeout_env_overrides(CONFIG)


# Environment variable engine selectors for MCP/Raycast users
def get_document_engine():
    """Get document engine with environment variable override and validation."""
    env_engine = os.environ.get("CCORE_DOCUMENT_ENGINE")
    if env_engine:
        if env_engine not in ALLOWED_DOCUMENT_ENGINES:
            # Import logger here to avoid circular imports
            from content_core.logging import logger

            logger.warning(
                f"Invalid CCORE_DOCUMENT_ENGINE: '{env_engine}'. "
                f"Allowed values: {', '.join(sorted(ALLOWED_DOCUMENT_ENGINES))}. "
                f"Using default from config."
            )
            return CONFIG.get("extraction", {}).get("document_engine", "auto")
        return env_engine
    return CONFIG.get("extraction", {}).get("document_engine", "auto")


def get_url_engine():
    """Get URL engine with environment variable override and validation."""
    env_engine = os.environ.get("CCORE_URL_ENGINE")
    if env_engine:
        if env_engine not in ALLOWED_URL_ENGINES:
            # Import logger here to avoid circular imports
            from content_core.logging import logger

            logger.warning(
                f"Invalid CCORE_URL_ENGINE: '{env_engine}'. "
                f"Allowed values: {', '.join(sorted(ALLOWED_URL_ENGINES))}. "
                f"Using default from config."
            )
            return CONFIG.get("extraction", {}).get("url_engine", "auto")
        return env_engine
    return CONFIG.get("extraction", {}).get("url_engine", "auto")


def get_audio_concurrency():
    """
    Get audio concurrency with environment variable override and validation.

    Returns the configured number of concurrent audio transcriptions, with automatic
    validation and fallback to safe defaults.

    Configuration priority (highest to lowest):
    1. CCORE_AUDIO_CONCURRENCY environment variable
    2. extraction.audio.concurrency in YAML config
    3. Default value: 3

    Returns:
        int: Number of concurrent transcriptions (1-10)

    Validation:
        - Values must be integers between 1 and 10 (inclusive)
        - Invalid values (out of range, non-integer, etc.) automatically fall back to default
        - A warning is logged when invalid values are detected

    Examples:
        >>> import os
        >>> os.environ["CCORE_AUDIO_CONCURRENCY"] = "5"
        >>> get_audio_concurrency()
        5

        >>> os.environ["CCORE_AUDIO_CONCURRENCY"] = "20"  # Too high
        >>> get_audio_concurrency()  # Falls back to default
        3
    """
    env_concurrency = os.environ.get("CCORE_AUDIO_CONCURRENCY")
    if env_concurrency:
        try:
            concurrency = int(env_concurrency)
            if concurrency < 1 or concurrency > 10:
                # Import logger here to avoid circular imports
                from content_core.logging import logger

                logger.warning(
                    f"Invalid CCORE_AUDIO_CONCURRENCY: '{env_concurrency}'. "
                    f"Must be between 1 and 10. "
                    f"Using default from config."
                )
                return (
                    CONFIG.get("extraction", {}).get("audio", {}).get("concurrency", 3)
                )
            return concurrency
        except ValueError:
            # Import logger here to avoid circular imports
            from content_core.logging import logger

            logger.warning(
                f"Invalid CCORE_AUDIO_CONCURRENCY: '{env_concurrency}'. "
                f"Must be a valid integer. "
                f"Using default from config."
            )
            return CONFIG.get("extraction", {}).get("audio", {}).get("concurrency", 3)
    return CONFIG.get("extraction", {}).get("audio", {}).get("concurrency", 3)


# Programmatic config overrides: use in notebooks or scripts
def set_document_engine(engine: str):
    """Override the document extraction engine ('auto', 'simple', or 'docling')."""
    CONFIG.setdefault("extraction", {})["document_engine"] = engine


def set_url_engine(engine: str):
    """Override the URL extraction engine ('auto', 'simple', 'firecrawl', 'jina', 'crawl4ai', or 'docling')."""
    CONFIG.setdefault("extraction", {})["url_engine"] = engine


def set_docling_output_format(fmt: str):
    """Override Docling output_format ('markdown', 'html', or 'json')."""
    extraction = CONFIG.setdefault("extraction", {})
    docling_cfg = extraction.setdefault("docling", {})
    docling_cfg["output_format"] = fmt


def set_pymupdf_ocr_enabled(enabled: bool):
    """Enable or disable PyMuPDF OCR for formula-heavy pages."""
    extraction = CONFIG.setdefault("extraction", {})
    pymupdf_cfg = extraction.setdefault("pymupdf", {})
    pymupdf_cfg["enable_formula_ocr"] = enabled


def set_pymupdf_formula_threshold(threshold: int):
    """Set the minimum number of formulas per page to trigger OCR."""
    extraction = CONFIG.setdefault("extraction", {})
    pymupdf_cfg = extraction.setdefault("pymupdf", {})
    pymupdf_cfg["formula_threshold"] = threshold


def set_pymupdf_ocr_fallback(enabled: bool):
    """Enable or disable fallback to standard extraction when OCR fails."""
    extraction = CONFIG.setdefault("extraction", {})
    pymupdf_cfg = extraction.setdefault("pymupdf", {})
    pymupdf_cfg["ocr_fallback"] = enabled


def set_audio_concurrency(concurrency: int):
    """
    Override the audio concurrency setting (1-10).

    Args:
        concurrency (int): Number of concurrent audio transcriptions (1-10)

    Raises:
        ValueError: If concurrency is not between 1 and 10
    """
    if not isinstance(concurrency, int) or concurrency < 1 or concurrency > 10:
        raise ValueError(
            f"Audio concurrency must be an integer between 1 and 10, got: {concurrency}"
        )
    extraction = CONFIG.setdefault("extraction", {})
    audio_cfg = extraction.setdefault("audio", {})
    audio_cfg["concurrency"] = concurrency


def get_retry_config(operation_type: str) -> dict:
    """
    Get retry configuration for a specific operation type.

    Configuration priority (highest to lowest):
    1. Environment variables (CCORE_{TYPE}_MAX_RETRIES, CCORE_{TYPE}_BASE_DELAY, CCORE_{TYPE}_MAX_DELAY)
    2. YAML config (retry.{type}.{param})
    3. Hardcoded defaults

    Args:
        operation_type: One of 'youtube', 'url_api', 'url_network', 'audio', 'llm', 'download'

    Returns:
        dict: Configuration with 'max_attempts', 'base_delay', 'max_delay'

    Examples:
        >>> get_retry_config("youtube")
        {'max_attempts': 5, 'base_delay': 2, 'max_delay': 60}

        >>> import os
        >>> os.environ["CCORE_YOUTUBE_MAX_RETRIES"] = "10"
        >>> get_retry_config("youtube")
        {'max_attempts': 10, 'base_delay': 2, 'max_delay': 60}
    """
    if operation_type not in ALLOWED_RETRY_OPERATIONS:
        from content_core.logging import logger

        logger.warning(
            f"Unknown retry operation type: '{operation_type}'. "
            f"Allowed values: {', '.join(sorted(ALLOWED_RETRY_OPERATIONS))}. "
            f"Using default config for 'url_network'."
        )
        operation_type = "url_network"

    # Get defaults
    defaults = DEFAULT_RETRY_CONFIG.get(
        operation_type, DEFAULT_RETRY_CONFIG["url_network"]
    )

    # Get from YAML config (falls back to defaults)
    retry_config = cast(Dict[str, Any], CONFIG.get("retry", {}))
    yaml_config = cast(Dict[str, Any], retry_config.get(operation_type, {}))
    max_attempts = int(yaml_config.get("max_attempts", defaults["max_attempts"]))
    base_delay: float = float(yaml_config.get("base_delay", defaults["base_delay"]))
    max_delay: float = float(yaml_config.get("max_delay", defaults["max_delay"]))

    # Environment variable overrides
    env_prefix = f"CCORE_{operation_type.upper()}"

    env_max_retries = os.environ.get(f"{env_prefix}_MAX_RETRIES")
    if env_max_retries:
        try:
            val = int(env_max_retries)
            if 1 <= val <= 20:
                max_attempts = val
            else:
                from content_core.logging import logger

                logger.warning(
                    f"Invalid {env_prefix}_MAX_RETRIES: '{env_max_retries}'. "
                    f"Must be between 1 and 20. Using config value: {max_attempts}"
                )
        except ValueError:
            from content_core.logging import logger

            logger.warning(
                f"Invalid {env_prefix}_MAX_RETRIES: '{env_max_retries}'. "
                f"Must be a valid integer. Using config value: {max_attempts}"
            )

    env_base_delay = os.environ.get(f"{env_prefix}_BASE_DELAY")
    if env_base_delay:
        try:
            val = float(env_base_delay)
            if 0.1 <= val <= 60:
                base_delay = float(val)
            else:
                from content_core.logging import logger

                logger.warning(
                    f"Invalid {env_prefix}_BASE_DELAY: '{env_base_delay}'. "
                    f"Must be between 0.1 and 60. Using config value: {base_delay}"
                )
        except ValueError:
            from content_core.logging import logger

            logger.warning(
                f"Invalid {env_prefix}_BASE_DELAY: '{env_base_delay}'. "
                f"Must be a valid number. Using config value: {base_delay}"
            )

    env_max_delay = os.environ.get(f"{env_prefix}_MAX_DELAY")
    if env_max_delay:
        try:
            val = float(env_max_delay)
            if 1 <= val <= 300:
                max_delay = float(val)
            else:
                from content_core.logging import logger

                logger.warning(
                    f"Invalid {env_prefix}_MAX_DELAY: '{env_max_delay}'. "
                    f"Must be between 1 and 300. Using config value: {max_delay}"
                )
        except ValueError:
            from content_core.logging import logger

            logger.warning(
                f"Invalid {env_prefix}_MAX_DELAY: '{env_max_delay}'. "
                f"Must be a valid number. Using config value: {max_delay}"
            )

    return {
        "max_attempts": max_attempts,
        "base_delay": base_delay,
        "max_delay": max_delay,
    }


# Proxy configuration
# Priority: Per-request > Programmatic (_PROXY_OVERRIDE) > Env var > YAML config
_PROXY_OVERRIDE: str | None = None


def _redact_proxy_url(proxy_url: str) -> str:
    """
    Redact credentials from a proxy URL for safe logging.

    Args:
        proxy_url: The proxy URL that may contain credentials

    Returns:
        The proxy URL with credentials redacted (e.g., http://***:***@host:port)
    """
    from urllib.parse import urlparse, urlunparse

    try:
        parsed = urlparse(proxy_url)
        if parsed.username or parsed.password:
            # Reconstruct URL with redacted credentials
            redacted_netloc = "***:***@" + parsed.hostname
            if parsed.port:
                redacted_netloc += f":{parsed.port}"
            return urlunparse(
                (parsed.scheme, redacted_netloc, parsed.path, "", "", "")
            )
        return proxy_url
    except Exception:
        # If parsing fails, return a generic message
        return "<proxy configured>"


def get_proxy(request_proxy: str | None = None) -> str | None:
    """
    Get the proxy URL with priority resolution.

    Configuration priority (highest to lowest):
    1. Per-request proxy (passed as argument)
    2. Programmatic override via set_proxy()
    3. Environment variables (CCORE_HTTP_PROXY, HTTP_PROXY, HTTPS_PROXY)
    4. YAML config (proxy.url)

    Args:
        request_proxy: Optional per-request proxy override. Pass empty string "" to
                      explicitly disable proxy for this request.

    Returns:
        str | None: Proxy URL or None if no proxy configured

    Examples:
        >>> get_proxy()  # Returns from env/config or None
        'http://proxy.example.com:8080'

        >>> get_proxy("http://custom-proxy:8080")  # Per-request override
        'http://custom-proxy:8080'

        >>> get_proxy("")  # Explicitly disable proxy for this request
        None
    """
    # 1. Per-request override (highest priority)
    if request_proxy is not None:
        if request_proxy == "":
            return None  # Explicitly disabled
        from content_core.logging import logger

        logger.debug(f"Using per-request proxy: {_redact_proxy_url(request_proxy)}")
        return request_proxy

    # 2. Programmatic override
    global _PROXY_OVERRIDE
    if _PROXY_OVERRIDE is not None:
        if _PROXY_OVERRIDE == "":
            return None  # Explicitly disabled
        from content_core.logging import logger

        logger.debug(f"Using programmatic proxy: {_redact_proxy_url(_PROXY_OVERRIDE)}")
        return _PROXY_OVERRIDE

    # 3. Environment variables
    env_proxy = (
        os.environ.get("CCORE_HTTP_PROXY")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("HTTPS_PROXY")
    )
    if env_proxy:
        from content_core.logging import logger

        logger.debug(f"Using environment proxy: {_redact_proxy_url(env_proxy)}")
        return env_proxy

    # 4. YAML config
    yaml_proxy = CONFIG.get("proxy", {}).get("url")
    if yaml_proxy:
        from content_core.logging import logger

        logger.debug(f"Using YAML config proxy: {_redact_proxy_url(yaml_proxy)}")
        return yaml_proxy

    return None


def set_proxy(proxy_url: str | None) -> None:
    """
    Set the proxy URL programmatically.

    This sets a global proxy override that takes precedence over environment
    variables and YAML config, but can still be overridden per-request.

    Args:
        proxy_url: Proxy URL (e.g., 'http://proxy:8080' or 'http://user:pass@proxy:8080')
                  Pass None or empty string to disable proxy.

    Examples:
        >>> set_proxy("http://proxy.example.com:8080")  # Enable proxy
        >>> set_proxy("http://user:pass@proxy:8080")    # With authentication
        >>> set_proxy(None)                              # Disable proxy
        >>> set_proxy("")                                # Also disables proxy
    """
    global _PROXY_OVERRIDE
    _PROXY_OVERRIDE = proxy_url
    from content_core.logging import logger

    if proxy_url:
        logger.debug(f"Proxy set programmatically: {proxy_url}")
    else:
        logger.debug("Proxy disabled programmatically")


def clear_proxy() -> None:
    """
    Clear the programmatic proxy override.

    After calling this, proxy resolution falls back to environment variables
    and YAML config.

    Examples:
        >>> set_proxy("http://proxy:8080")
        >>> clear_proxy()  # Now uses env vars or YAML config
    """
    global _PROXY_OVERRIDE
    _PROXY_OVERRIDE = None
    from content_core.logging import logger

    logger.debug("Programmatic proxy override cleared")


def get_no_proxy() -> list:
    """
    Get the list of hosts that should bypass the proxy.

    Returns:
        list: List of hostnames/patterns to bypass proxy

    Examples:
        >>> get_no_proxy()
        ['localhost', '127.0.0.1']
    """
    # Check environment variable first
    env_no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
    if env_no_proxy:
        return [h.strip() for h in env_no_proxy.split(",") if h.strip()]

    # Fall back to YAML config
    return CONFIG.get("proxy", {}).get("no_proxy", ["localhost", "127.0.0.1"])

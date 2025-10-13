import os
import pkgutil
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Allowed engine values for validation
ALLOWED_DOCUMENT_ENGINES = {"auto", "simple", "docling"}
ALLOWED_URL_ENGINES = {"auto", "simple", "firecrawl", "jina"}


def load_config():
    config_path = os.environ.get("CCORE_CONFIG_PATH") or os.environ.get("CCORE_MODEL_CONFIG_PATH")
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
        docling_cfg = yaml.safe_load(cc_default)
        # merge extraction section
        base["extraction"] = docling_cfg.get("extraction", {})
    return base


CONFIG = load_config()

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
                return CONFIG.get("extraction", {}).get("audio", {}).get("concurrency", 3)
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
    """Override the URL extraction engine ('auto', 'simple', 'firecrawl', 'jina', or 'docling')."""
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
        raise ValueError(f"Audio concurrency must be an integer between 1 and 10, got: {concurrency}")
    extraction = CONFIG.setdefault("extraction", {})
    audio_cfg = extraction.setdefault("audio", {})
    audio_cfg["concurrency"] = concurrency

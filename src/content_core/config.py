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

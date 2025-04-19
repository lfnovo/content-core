import os
import pkgutil
import os  # needed for load_config env/path checks
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def load_config():
    config_path = os.environ.get("CCORE_CONFIG_PATH") or os.environ.get("CCORE_MODEL_CONFIG_PATH")
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r") as file:
                return yaml.safe_load(file)
        except Exception as e:
            print(f"Erro ao carregar o arquivo de configuração de {config_path}: {e}")
            print("Usando configurações padrão internas.")

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

# Programmatic config overrides: use in notebooks or scripts
def set_extraction_engine(engine: str):
    """Override the extraction engine ('legacy' or 'docling')."""
    CONFIG.setdefault("extraction", {})["engine"] = engine

def set_docling_output_format(fmt: str):
    """Override Docling output_format ('markdown', 'html', or 'json')."""
    extraction = CONFIG.setdefault("extraction", {})
    docling_cfg = extraction.setdefault("docling", {})
    docling_cfg["output_format"] = fmt

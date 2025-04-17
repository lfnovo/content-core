import os
import pkgutil

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def load_config():
    config_path = os.environ.get("CCORE_MODEL_CONFIG_PATH")
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r") as file:
                return yaml.safe_load(file)
        except Exception as e:
            print(f"Erro ao carregar o arquivo de configuração de {config_path}: {e}")
            print("Usando configurações padrão internas.")

    default_config_data = pkgutil.get_data("content_core", "models_config.yaml")
    if default_config_data:
        return yaml.safe_load(default_config_data)
    return {}


CONFIG = load_config()

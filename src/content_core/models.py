from esperanto import AIFactory

from .config import CONFIG


class ModelFactory:
    _instances = {}

    @staticmethod
    def get_model(model_alias):
        if model_alias not in ModelFactory._instances:
            config = CONFIG.get(model_alias, {})
            if not config:
                raise ValueError(
                    f"Configuração para o modelo {model_alias} não encontrada."
                )

            provider = config.get("provider")
            model_name = config.get("model_name")
            model_config = config.get("config", {}).copy()

            # Proxy is configured via HTTP_PROXY/HTTPS_PROXY env vars (handled by Esperanto)

            if model_alias == "speech_to_text":
                # For STT models, pass timeout in config dict
                timeout = config.get("timeout")
                stt_config = {"timeout": timeout} if timeout else {}
                ModelFactory._instances[model_alias] = AIFactory.create_speech_to_text(
                    provider, model_name, stt_config
                )
            else:
                ModelFactory._instances[model_alias] = AIFactory.create_language(
                    provider, model_name, config=model_config
                )

        return ModelFactory._instances[model_alias]

    @staticmethod
    def clear_cache():
        """Clear all cached model instances."""
        ModelFactory._instances.clear()

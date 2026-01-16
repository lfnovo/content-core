from esperanto import AIFactory

from .config import CONFIG, get_proxy


class ModelFactory:
    _instances = {}
    _proxy_at_creation = {}  # Track proxy used when model was created

    @staticmethod
    def get_model(model_alias):
        current_proxy = get_proxy()

        # Check if we need to recreate the model due to proxy change
        if model_alias in ModelFactory._instances:
            cached_proxy = ModelFactory._proxy_at_creation.get(model_alias)
            if cached_proxy != current_proxy:
                # Proxy changed, invalidate cached instance
                del ModelFactory._instances[model_alias]
                del ModelFactory._proxy_at_creation[model_alias]

        if model_alias not in ModelFactory._instances:
            config = CONFIG.get(model_alias, {})
            if not config:
                raise ValueError(
                    f"Configuração para o modelo {model_alias} não encontrada."
                )

            provider = config.get("provider")
            model_name = config.get("model_name")
            model_config = config.get("config", {}).copy()

            # Add proxy to model config if configured
            if current_proxy:
                model_config["proxy"] = current_proxy

            if model_alias == "speech_to_text":
                # For STT models, pass timeout in config dict
                timeout = config.get("timeout")
                stt_config = {"timeout": timeout} if timeout else {}
                if current_proxy:
                    stt_config["proxy"] = current_proxy
                ModelFactory._instances[model_alias] = AIFactory.create_speech_to_text(
                    provider, model_name, stt_config
                )
            else:
                ModelFactory._instances[model_alias] = AIFactory.create_language(
                    provider, model_name, config=model_config
                )

            # Track what proxy was used
            ModelFactory._proxy_at_creation[model_alias] = current_proxy

        return ModelFactory._instances[model_alias]

    @staticmethod
    def clear_cache():
        """Clear all cached model instances. Useful when proxy configuration changes."""
        ModelFactory._instances.clear()
        ModelFactory._proxy_at_creation.clear()

"""Model factory for Esperanto integration.

Uses configuration from config.py (ENV-based) to create LLM and STT models.
"""

from esperanto import AIFactory

from .config import get_model_config


class ModelFactory:
    """Factory for creating and caching Esperanto models.

    Models are created lazily and cached for reuse. Configuration comes from
    environment variables via get_model_config().
    """

    _instances = {}

    @staticmethod
    def get_model(model_alias: str):
        """Get a model instance by alias.

        Args:
            model_alias: One of 'speech_to_text', 'default_model', 'cleanup_model', 'summary_model'

        Returns:
            Esperanto model instance (SpeechToText or LanguageModel)

        Raises:
            ValueError: If model_alias is unknown
        """
        if model_alias not in ModelFactory._instances:
            config = get_model_config(model_alias)
            if not config:
                raise ValueError(
                    f"Configuration for model {model_alias} not found."
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
        """Clear all cached model instances.

        Call this when configuration changes (e.g., after reset_config()).
        """
        ModelFactory._instances.clear()

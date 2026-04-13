from typing import Optional

from esperanto import AIFactory

from content_core.config import ContentCoreConfig, get_default_config


class ModelFactory:
    _instances = {}

    @staticmethod
    def get_model(model_alias: str, config: Optional[ContentCoreConfig] = None):
        """Get or create a cached model instance.

        Args:
            model_alias: One of 'speech_to_text', 'summary_model', 'default_model'
            config: Optional ContentCoreConfig. If provided, bypasses cache and
                    uses config values. If None, uses default config.
        """
        if config is not None:
            # Build from explicit config — not cached (config may vary per call)
            return ModelFactory._build_from_config(model_alias, config)

        if model_alias not in ModelFactory._instances:
            cfg = get_default_config()
            ModelFactory._instances[model_alias] = ModelFactory._build_from_config(
                model_alias, cfg
            )

        return ModelFactory._instances[model_alias]

    @staticmethod
    def _build_from_config(model_alias: str, cfg: ContentCoreConfig):
        """Build a model instance from a ContentCoreConfig."""
        if model_alias == "speech_to_text":
            stt_config = {"timeout": cfg.stt_timeout} if cfg.stt_timeout else {}
            return AIFactory.create_speech_to_text(
                cfg.stt_provider, cfg.stt_model, stt_config
            )
        elif model_alias == "summary_model":
            provider = cfg.llm_provider
            model_name = cfg.summary_model or cfg.llm_model
            return AIFactory.create_language(provider, model_name, config={"timeout": 120, "max_tokens": 4096})
        elif model_alias == "default_model":
            return AIFactory.create_language(cfg.llm_provider, cfg.llm_model, config={"timeout": 120, "max_tokens": 4096})
        else:
            raise ValueError(f"Unknown model alias: {model_alias}")

    @staticmethod
    def clear_cache():
        """Clear all cached model instances."""
        ModelFactory._instances.clear()

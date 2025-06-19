from esperanto import AIFactory
from .config import CONFIG

class ModelFactory:
    _instances = {}

    @staticmethod
    def get_model(model_alias):
        if model_alias not in ModelFactory._instances:
            config = CONFIG.get(model_alias, {})
            if not config:
                raise ValueError(f"Configuração para o modelo {model_alias} não encontrada.")

            provider = config.get('provider')
            model_name = config.get('model_name')
            model_config = config.get('config', {})

            if model_alias == 'speech_to_text':
                ModelFactory._instances[model_alias] = AIFactory.create_speech_to_text(provider, model_name)
            else:
                ModelFactory._instances[model_alias] = AIFactory.create_language(provider, model_name, config=model_config)

        return ModelFactory._instances[model_alias]

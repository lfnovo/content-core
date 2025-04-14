from esperanto import AIFactory
from esperanto.providers.stt import SpeechToTextModel

SPEECH_TO_TEXT_MODEL: SpeechToTextModel = AIFactory.create_speech_to_text(
    "openai", "whisper-1"
)

DEFAULT_MODEL = AIFactory.create_language(
    "openai",
    "gpt-4o-mini",
    config={
        "temperature": 0.5,
        "top_p": 1,
        "max_tokens": 2000,
    },
)

CLEANUP_MODEL = AIFactory.create_language(
    "openai",
    "gpt-4o-mini",
    config={
        "temperature": 0,
        "max_tokens": 8000,
        "output_format": "json",
        # "stream": True, # TODO: handle streaming
    },
)  # Fix deprecation

SUMMARY_MODEL = AIFactory.create_language(
    "openai",
    "gpt-4o-mini",
    config={
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 2000,
    },
)

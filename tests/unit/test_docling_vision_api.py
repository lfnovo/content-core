"""Unit tests for env-configured Docling picture description via an
OpenAI-compatible endpoint (CCORE_DOCLING_VISION_*)."""

import pytest

from content_core.processors.document import docling as docling_module

pytest.importorskip("docling")


def _clear(monkeypatch):
    for var in (
        docling_module.VISION_URL_ENV,
        docling_module.VISION_API_KEY_ENV,
        docling_module.VISION_MODEL_ENV,
        docling_module.VISION_PROMPT_ENV,
        docling_module.VISION_MAX_TOKENS_ENV,
        docling_module.VISION_TIMEOUT_ENV,
        docling_module.VISION_TOKEN_PARAM_ENV,
    ):
        monkeypatch.delenv(var, raising=False)


def test_no_url_keeps_inline_default(monkeypatch):
    _clear(monkeypatch)
    assert docling_module._picture_description_options_from_env() is None
    if docling_module.PictureDescriptionApiOptions is not None:
        monkeypatch.setenv(docling_module.VISION_MODEL_ENV, "some-model")
        # URL is the master switch: a model name alone must not enable the API
        assert docling_module._picture_description_options_from_env() is None


def test_url_builds_api_options(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(
        docling_module.VISION_URL_ENV, "http://localhost:1234/v1/chat/completions"
    )
    monkeypatch.setenv(docling_module.VISION_MODEL_ENV, "my-local-vlm")
    monkeypatch.setenv(docling_module.VISION_API_KEY_ENV, "secret")
    monkeypatch.setenv(docling_module.VISION_MAX_TOKENS_ENV, "800")
    monkeypatch.setenv(docling_module.VISION_TIMEOUT_ENV, "120")
    monkeypatch.setenv(docling_module.VISION_PROMPT_ENV, "Describe it.")

    options = docling_module._picture_description_options_from_env()

    assert options is not None
    assert "localhost:1234" in str(options.url)
    assert options.params["model"] == "my-local-vlm"
    assert options.params["max_completion_tokens"] == 800
    assert options.headers["Authorization"] == "Bearer secret"
    assert options.timeout == 120
    assert options.prompt == "Describe it."


def test_missing_api_key_sends_no_authorization_header(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(
        docling_module.VISION_URL_ENV, "http://localhost:1234/v1/chat/completions"
    )
    options = docling_module._picture_description_options_from_env()
    assert options is not None
    assert "Authorization" not in options.headers


def test_malformed_numeric_env_falls_back_to_defaults(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(
        docling_module.VISION_URL_ENV, "http://localhost:1234/v1/chat/completions"
    )
    monkeypatch.setenv(docling_module.VISION_MAX_TOKENS_ENV, "banana")
    monkeypatch.setenv(docling_module.VISION_TIMEOUT_ENV, "not-a-number")

    with pytest.warns(UserWarning):
        options = docling_module._picture_description_options_from_env()

    assert options is not None
    assert options.params["max_completion_tokens"] == 400
    assert options.timeout == 20


def test_token_param_name_is_selectable(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(
        docling_module.VISION_URL_ENV, "http://localhost:1234/v1/chat/completions"
    )
    monkeypatch.setenv(docling_module.VISION_TOKEN_PARAM_ENV, "max_tokens")
    options = docling_module._picture_description_options_from_env()
    assert options is not None
    assert "max_tokens" in options.params
    assert "max_completion_tokens" not in options.params

"""Unit tests for Docling picture description via an OpenAI-compatible endpoint
(docling_vision_* settings / CCORE_DOCLING_VISION_* env vars)."""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from content_core.config import ContentCoreConfig
from content_core.processors.document import docling as docling_module

pytest.importorskip("docling")

URL = "http://localhost:1234/v1/chat/completions"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    """Keep the caller's CCORE_DOCLING_VISION_* env vars and config file out."""
    for var in list(os.environ):
        if var.startswith("CCORE_DOCLING_VISION_"):
            monkeypatch.delenv(var)
    monkeypatch.setattr("content_core.config.CONFIG_FILE", tmp_path / "config.toml")


def test_url_with_credentials_is_not_logged():
    config = ContentCoreConfig(docling_vision_url="https://user:pw@vlm.example.com/v1/chat/completions?key=abc")
    with patch.object(docling_module, "logger") as logger:
        docling_module._picture_description_api_options(config)
    logged = " ".join(str(c) for c in logger.debug.call_args_list)
    assert "vlm.example.com" in logged
    assert "pw" not in logged and "abc" not in logged


def test_no_url_keeps_inline_default():
    # URL is the switch: a model name alone must not enable the API path
    config = ContentCoreConfig(docling_vision_url=None, docling_vision_model="some-model")
    assert docling_module._picture_description_api_options(config) is None


def test_url_builds_api_options():
    config = ContentCoreConfig(
        docling_vision_url=URL,
        docling_vision_model="my-local-vlm",
        docling_vision_api_key="secret",
        docling_vision_max_tokens=800,
        docling_vision_timeout=120,
        docling_vision_prompt="Describe it.",
    )

    options = docling_module._picture_description_api_options(config)

    assert options is not None
    assert "localhost:1234" in str(options.url)
    assert options.params["model"] == "my-local-vlm"
    assert options.params["max_completion_tokens"] == 800
    assert options.headers["Authorization"] == "Bearer secret"
    assert options.timeout == 120
    assert options.prompt == "Describe it."


def test_defaults_keep_docling_prompt_and_timeout():
    config = ContentCoreConfig(docling_vision_url=URL, docling_vision_api_key=None)
    options = docling_module._picture_description_api_options(config)
    default = docling_module.PictureDescriptionApiOptions()

    assert options is not None
    assert "Authorization" not in options.headers
    assert "model" not in options.params
    assert options.params["max_completion_tokens"] == 400
    assert options.prompt == default.prompt
    assert options.timeout == 20


def test_token_param_name_is_selectable():
    config = ContentCoreConfig(docling_vision_url=URL, docling_vision_token_param="max_tokens")
    options = docling_module._picture_description_api_options(config)
    assert options is not None
    assert "max_tokens" in options.params
    assert "max_completion_tokens" not in options.params


def test_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("CCORE_DOCLING_VISION_URL", URL)
    monkeypatch.setenv("CCORE_DOCLING_VISION_MODEL", "env-vlm")
    monkeypatch.setenv("CCORE_DOCLING_VISION_MAX_TOKENS", "256")
    monkeypatch.setenv("CCORE_DOCLING_VISION_TIMEOUT", "45.5")
    monkeypatch.setenv("CCORE_DOCLING_VISION_TOKEN_PARAM", "max_tokens")

    options = docling_module._picture_description_api_options(ContentCoreConfig())

    assert options is not None
    assert options.params == {"max_tokens": 256, "model": "env-vlm"}
    assert options.timeout == 45.5


@pytest.mark.parametrize(
    "field,value",
    [
        ("docling_vision_max_tokens", "banana"),
        ("docling_vision_max_tokens", 0),
        ("docling_vision_timeout", "not-a-number"),
        ("docling_vision_token_param", "max_length"),
    ],
)
def test_invalid_settings_are_rejected(field, value):
    with pytest.raises(ValidationError):
        ContentCoreConfig(**{field: value})


async def _run_extract(config):
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "content"
    pipeline_cls = MagicMock()
    with patch.object(docling_module, "DocumentConverter") as converter_cls, patch.object(
        docling_module, "DOCLING_AVAILABLE", True
    ), patch.object(docling_module, "PdfPipelineOptions", pipeline_cls), patch.object(
        docling_module, "PdfFormatOption", MagicMock()
    ), patch.object(docling_module, "InputFormat", MagicMock()):
        converter_cls.return_value.convert.return_value = mock_result
        await docling_module.extract_docling("/fake/doc.pdf", config)
    return pipeline_cls.call_args[1]


async def test_extract_wires_api_options_when_url_set():
    config = ContentCoreConfig(docling_vision=True, docling_vision_url=URL)
    kwargs = await _run_extract(config)
    assert kwargs["enable_remote_services"] is True
    assert "localhost:1234" in str(kwargs["picture_description_options"].url)


async def test_extract_stays_local_without_vision():
    # The URL alone does not turn picture description on
    config = ContentCoreConfig(docling_vision=False, docling_vision_url=URL)
    kwargs = await _run_extract(config)
    assert kwargs["enable_remote_services"] is False
    assert "picture_description_options" not in kwargs

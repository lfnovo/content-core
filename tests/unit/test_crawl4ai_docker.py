"""Crawl4AI Docker API client: bearer token header and mode selection."""

from typing import ClassVar
from unittest.mock import patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.url import crawl4ai as crawl4ai_module


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    async def json(self):
        return self._payload


class _FakeSession:
    """Records ClientSession kwargs and post() calls."""

    instances: ClassVar[list] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.posts = []
        _FakeSession.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return _FakeResponse(
            {
                "results": [
                    {
                        "metadata": {"title": "Docker Title"},
                        "markdown": {"raw_markdown": "# Hello"},
                    }
                ]
            }
        )


@pytest.fixture
def fake_session():
    _FakeSession.instances = []
    with patch.object(crawl4ai_module.aiohttp, "ClientSession", _FakeSession):
        yield _FakeSession


@pytest.mark.asyncio
async def test_docker_sends_bearer_header_when_token_given(fake_session):
    result = await crawl4ai_module._fetch_url_crawl4ai_docker(
        "https://example.com", "http://crawl:11235/", api_token="secret"
    )

    session = fake_session.instances[0]
    assert session.kwargs["headers"] == {"Authorization": "Bearer secret"}
    assert session.posts[0][0] == "http://crawl:11235/crawl"
    assert result == {"title": "Docker Title", "content": "# Hello"}


@pytest.mark.asyncio
async def test_docker_sends_no_auth_header_when_token_absent(fake_session):
    await crawl4ai_module._fetch_url_crawl4ai_docker(
        "https://example.com", "http://crawl:11235"
    )

    session = fake_session.instances[0]
    assert session.kwargs["headers"] is None


@pytest.mark.asyncio
async def test_token_from_config_reaches_docker_client(fake_session, monkeypatch):
    monkeypatch.delenv("CRAWL4AI_API_URL", raising=False)
    monkeypatch.delenv("CRAWL4AI_API_TOKEN", raising=False)
    cfg = ContentCoreConfig(
        crawl4ai_api_url="http://crawl:11235", crawl4ai_api_token="from-config"
    )

    await crawl4ai_module.extract_url_crawl4ai("https://example.com", cfg)

    assert fake_session.instances[0].kwargs["headers"] == {
        "Authorization": "Bearer from-config"
    }


@pytest.mark.asyncio
async def test_env_token_takes_precedence_over_config(fake_session, monkeypatch):
    monkeypatch.setenv("CRAWL4AI_API_URL", "http://crawl:11235")
    monkeypatch.setenv("CRAWL4AI_API_TOKEN", "from-env")
    cfg = ContentCoreConfig(crawl4ai_api_token="from-config")

    await crawl4ai_module.extract_url_crawl4ai("https://example.com", cfg)

    assert fake_session.instances[0].kwargs["headers"] == {
        "Authorization": "Bearer from-env"
    }


@pytest.mark.asyncio
async def test_local_mode_ignores_token(fake_session, monkeypatch):
    monkeypatch.delenv("CRAWL4AI_API_URL", raising=False)
    monkeypatch.setenv("CRAWL4AI_API_TOKEN", "unused")
    cfg = ContentCoreConfig()

    with patch.object(
        crawl4ai_module, "_fetch_url_crawl4ai_local", return_value={"title": "t", "content": "c"}
    ) as local:
        result = await crawl4ai_module.extract_url_crawl4ai("https://example.com", cfg)

    local.assert_awaited_once_with("https://example.com")
    assert result == {"title": "t", "content": "c"}
    assert fake_session.instances == []


def test_config_default_token_is_none():
    assert ContentCoreConfig().crawl4ai_api_token is None

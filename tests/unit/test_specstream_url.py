"""SpecStream Extract API client: proxy settings, base URL, request and reply shape."""

from typing import ClassVar

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.url import specstream as specstream_module


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
    payload: ClassVar[dict] = {
        "data": {
            "results": [
                {
                    "url": "https://example.com",
                    "status": "ok",
                    "title": "Example",
                    "text": "# Hello",
                }
            ]
        }
    }

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
        return _FakeResponse(self.payload)


@pytest.fixture
def fake_session(monkeypatch):
    _FakeSession.instances = []
    monkeypatch.delenv("SPECSTREAM_API_URL", raising=False)
    monkeypatch.delenv("SPECSTREAM_API_KEY", raising=False)
    monkeypatch.setattr(specstream_module.aiohttp, "ClientSession", _FakeSession)
    yield _FakeSession


@pytest.mark.asyncio
async def test_session_honors_proxy_environment(fake_session):
    await specstream_module.extract_url_specstream(
        "https://example.com", ContentCoreConfig(specstream_api_key="k")
    )

    assert fake_session.instances[0].kwargs["trust_env"] is True


@pytest.mark.asyncio
async def test_trailing_slash_in_api_url_is_stripped(fake_session):
    cfg = ContentCoreConfig(specstream_api_url="https://self.hosted/", specstream_api_key="k")

    await specstream_module.extract_url_specstream("https://example.com", cfg)

    assert fake_session.instances[0].posts[0][0] == "https://self.hosted/v1/extract"


@pytest.mark.asyncio
async def test_sends_urls_list_and_reads_first_result(fake_session):
    result = await specstream_module.extract_url_specstream(
        "https://example.com", ContentCoreConfig(specstream_api_key="from-config")
    )

    session = fake_session.instances[0]
    url, kwargs = session.posts[0]
    assert url == "https://api.specstream.ai/v1/extract"
    assert kwargs["json"] == {"urls": ["https://example.com"], "format": "markdown"}
    assert session.kwargs["headers"] == {"Authorization": "Bearer from-config"}
    assert result == {"title": "Example", "content": "# Hello"}


@pytest.mark.asyncio
async def test_env_key_and_url_take_precedence_over_config(fake_session, monkeypatch):
    monkeypatch.setenv("SPECSTREAM_API_URL", "https://env.example")
    monkeypatch.setenv("SPECSTREAM_API_KEY", "from-env")
    cfg = ContentCoreConfig(specstream_api_key="from-config")

    await specstream_module.extract_url_specstream("https://example.com", cfg)

    session = fake_session.instances[0]
    assert session.kwargs["headers"] == {"Authorization": "Bearer from-env"}
    assert session.posts[0][0] == "https://env.example/v1/extract"


@pytest.mark.asyncio
async def test_page_not_read_raises(fake_session, monkeypatch):
    monkeypatch.setattr(
        _FakeSession,
        "payload",
        {"data": {"results": [{"url": "https://example.com", "status": "blocked"}]}},
    )

    with pytest.raises(RuntimeError, match="blocked"):
        await specstream_module._fetch_url_specstream.retry_with(stop=lambda _: True)(
            "https://example.com", ContentCoreConfig(specstream_api_key="k")
        )

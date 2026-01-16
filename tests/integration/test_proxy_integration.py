"""
Integration tests for proxy functionality using a simple aiohttp-based proxy.

These tests start a real proxy server and verify that requests
are properly routed through the configured proxy.

Usage:
    uv run pytest tests/integration/test_proxy_integration.py -v
"""
import asyncio
import socket
from typing import Optional

import aiohttp
import pytest
from aiohttp import web

from content_core.config import clear_proxy, get_proxy, set_proxy


# Mark all tests in this module
pytestmark = [
    pytest.mark.proxy,
    pytest.mark.integration,
]


class SimpleProxyServer:
    """
    A simple HTTP proxy server for testing purposes.

    This proxy logs all requests that pass through it, allowing tests
    to verify that requests are being properly routed through the proxy.
    """

    def __init__(self, port: int = 0):
        self._requested_port = port
        self.port: Optional[int] = None
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.requests: list = []
        self._started = False

    async def _proxy_handler(self, request: web.Request) -> web.Response:
        """Handle proxy requests by forwarding them and logging."""
        # For HTTP proxies, aiohttp sends:
        # - Path: relative path (e.g., /get, /path)
        # - Host header: target domain (e.g., httpbin.org)
        raw_path = request.path_qs
        host = request.headers.get("Host", "")

        # Construct target URL from Host header and path
        if raw_path.startswith("http://") or raw_path.startswith("https://"):
            # Full URL in path (some clients do this)
            target_url = raw_path
        else:
            # Standard proxy format: Host header + path
            target_url = f"http://{host}{raw_path}"

        # Log the request
        req_info = {
            "method": request.method,
            "url": target_url,
            "host": host,
            "path": raw_path,
            "headers": dict(request.headers),
        }
        self.requests.append(req_info)

        # For CONNECT requests (HTTPS tunneling), we just acknowledge
        if request.method == "CONNECT":
            return web.Response(status=200, text="Connection established")

        try:
            async with aiohttp.ClientSession() as session:
                # Forward the request (without proxy to avoid loop)
                headers = {
                    k: v for k, v in request.headers.items()
                    if k.lower() not in ("proxy-connection", "proxy-authorization")
                }

                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=await request.read() if request.can_read_body else None,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    body = await resp.read()
                    return web.Response(
                        status=resp.status,
                        headers={
                            k: v for k, v in resp.headers.items()
                            if k.lower() not in ("transfer-encoding", "content-encoding", "content-length")
                        },
                        body=body,
                    )
        except Exception as e:
            # Return error but still count as proxy was used
            return web.Response(
                status=502,
                text=f"Proxy error: {str(e)}",
            )

    @web.middleware
    async def _proxy_middleware(self, request: web.Request, handler):
        """Middleware to intercept ALL requests including proxy requests."""
        # This middleware catches everything before routing
        return await self._proxy_handler(request)

    async def start(self) -> "SimpleProxyServer":
        """Start the proxy server."""
        # Use middleware to catch all requests, bypassing router
        self.app = web.Application(middlewares=[self._proxy_middleware])

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        # Use port 0 to let OS assign an available port
        self.site = web.TCPSite(self.runner, "127.0.0.1", self._requested_port)
        await self.site.start()

        # Get the actual port
        assert self.site._server is not None
        sockets = self.site._server.sockets
        if sockets:
            self.port = sockets[0].getsockname()[1]

        self._started = True
        return self

    async def stop(self):
        """Stop the proxy server."""
        if self.runner:
            await self.runner.cleanup()
        self._started = False

    def clear_requests(self):
        """Clear the logged requests."""
        self.requests.clear()

    def get_requests(self) -> list:
        """Get logged requests."""
        return self.requests.copy()

    @property
    def proxy_url(self) -> str:
        """Get the proxy URL."""
        return f"http://127.0.0.1:{self.port}"

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


@pytest.fixture
async def proxy_server():
    """Fixture that provides a running proxy server for tests."""
    server = SimpleProxyServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture(autouse=True)
def clean_proxy_state():
    """Ensure proxy state is clean before and after each test."""
    clear_proxy()
    yield
    clear_proxy()


class TestSimpleProxyServer:
    """Tests for the SimpleProxyServer itself."""

    @pytest.mark.asyncio
    async def test_proxy_server_starts(self, proxy_server):
        """Test that proxy server starts and has a port."""
        assert proxy_server.port is not None
        assert proxy_server.port > 0

    @pytest.mark.asyncio
    async def test_proxy_server_accepts_connections(self, proxy_server):
        """Test that proxy server accepts connections."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(("127.0.0.1", proxy_server.port))
            assert result == 0, "Could not connect to proxy server"
        finally:
            sock.close()


class TestProxyConfiguration:
    """Tests for proxy configuration functions."""

    @pytest.mark.asyncio
    async def test_set_proxy_configures_correctly(self, proxy_server):
        """Test that set_proxy sets the proxy URL correctly."""
        set_proxy(proxy_server.proxy_url)
        assert get_proxy() == proxy_server.proxy_url

    @pytest.mark.asyncio
    async def test_per_request_override(self, proxy_server):
        """Test that per-request proxy overrides global setting."""
        set_proxy("http://other-proxy:9999")

        # Per-request should override
        result = get_proxy(proxy_server.proxy_url)
        assert result == proxy_server.proxy_url

    @pytest.mark.asyncio
    async def test_empty_string_disables(self, proxy_server):
        """Test that empty string disables proxy."""
        set_proxy(proxy_server.proxy_url)

        # Empty string should return None
        result = get_proxy("")
        assert result is None


class TestProxyIntegration:
    """Integration tests for proxy functionality with real HTTP requests."""

    @pytest.mark.asyncio
    async def test_aiohttp_request_through_proxy(self, proxy_server):
        """Test that aiohttp requests go through the proxy."""
        set_proxy(proxy_server.proxy_url)
        proxy_server.clear_requests()

        proxy = get_proxy()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    "http://httpbin.org/get",
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    await response.text()
            except Exception:
                # Request might fail, but we just want to verify proxy was used
                pass

        # Check that request went through proxy
        requests = proxy_server.get_requests()
        assert len(requests) > 0, "No requests were logged through the proxy"
        assert any("httpbin.org" in r.get("url", "") for r in requests)

    @pytest.mark.asyncio
    async def test_url_fetch_through_proxy(self, proxy_server):
        """Test that URL fetching uses the proxy."""
        from content_core.processors.url import _fetch_url_html

        proxy_server.clear_requests()

        try:
            # Pass proxy directly to the function
            await _fetch_url_html("http://example.com", proxy=proxy_server.proxy_url)
        except Exception:
            pass  # Request might fail, we just check proxy routing

        requests = proxy_server.get_requests()
        assert len(requests) > 0, "URL fetch did not route through proxy"
        assert any("example.com" in r.get("url", "") for r in requests)

    @pytest.mark.asyncio
    async def test_url_mime_type_through_proxy(self, proxy_server):
        """Test that MIME type detection uses the proxy."""
        from content_core.processors.url import _fetch_url_mime_type

        proxy_server.clear_requests()

        try:
            # Pass proxy directly to the function
            await _fetch_url_mime_type("http://example.com", proxy=proxy_server.proxy_url)
        except Exception:
            pass

        requests = proxy_server.get_requests()
        assert len(requests) > 0, "MIME type fetch did not route through proxy"

    @pytest.mark.asyncio
    async def test_proxy_not_used_when_disabled(self, proxy_server):
        """Test that requests don't go through proxy when disabled."""
        set_proxy(proxy_server.proxy_url)
        proxy_server.clear_requests()

        # Explicitly disable proxy for this request
        proxy = get_proxy("")  # Empty string = disabled
        assert proxy is None

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    "http://httpbin.org/get",
                    proxy=proxy,  # None = no proxy
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    await response.text()
            except Exception:
                pass

        # No requests should go through our proxy
        requests = proxy_server.get_requests()
        httpbin_requests = [r for r in requests if "httpbin.org" in r.get("url", "")]
        assert len(httpbin_requests) == 0, "Request went through proxy when it should not have"

    @pytest.mark.asyncio
    async def test_multiple_requests_all_logged(self, proxy_server):
        """Test that multiple requests are all logged by proxy."""
        set_proxy(proxy_server.proxy_url)
        proxy_server.clear_requests()

        proxy = get_proxy()
        urls = [
            "http://httpbin.org/get",
            "http://httpbin.org/headers",
            "http://httpbin.org/ip",
        ]

        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(
                        url,
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as response:
                        await response.text()
                except Exception:
                    pass

        requests = proxy_server.get_requests()
        assert len(requests) >= 3, f"Expected 3+ requests, got {len(requests)}"


class TestProxyWithContentCore:
    """Integration tests with Content Core extraction functions."""

    @pytest.mark.asyncio
    async def test_extract_url_function_uses_proxy(self, proxy_server):
        """Test that the high-level extract_url function uses proxy."""
        from content_core.processors.url import extract_url
        from content_core.common import ProcessSourceState

        proxy_server.clear_requests()

        # Create state with proxy and force "simple" engine (BeautifulSoup)
        # to avoid Firecrawl which doesn't support client-side proxy
        state = ProcessSourceState(
            url="http://example.com",
            proxy=proxy_server.proxy_url,
            url_engine="simple",  # Force simple engine to test proxy
        )

        try:
            await extract_url(state)
        except Exception:
            pass  # May fail, we just verify proxy was used

        requests = proxy_server.get_requests()
        assert len(requests) > 0, "extract_url did not route through proxy"

    @pytest.mark.asyncio
    async def test_url_provider_uses_proxy(self, proxy_server):
        """Test that url_provider function uses proxy for HEAD requests."""
        from content_core.processors.url import url_provider
        from content_core.common import ProcessSourceState

        proxy_server.clear_requests()

        state = ProcessSourceState(
            url="http://example.com/test.html",
            proxy=proxy_server.proxy_url,
        )

        try:
            await url_provider(state)
        except Exception:
            pass

        requests = proxy_server.get_requests()
        assert len(requests) > 0, "url_provider did not route through proxy"


# pytest markers configuration
def pytest_configure(config):
    config.addinivalue_line("markers", "proxy: marks tests as proxy integration tests")

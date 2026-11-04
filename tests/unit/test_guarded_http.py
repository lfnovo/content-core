"""Unit tests for the guarded HTTP session (common/http.py).

A local aiohttp server stands in for the remote site, so no network is needed.
"""

import ipaddress
import socket

import pytest
from aiohttp import web

from content_core.common.exceptions import InvalidInputError
from content_core.common.http import (
    BlockedAddressError,
    GuardedResolver,
    check_url_host,
    guarded_request_url,
    guarded_session,
    is_blocked_address,
)
from content_core.processors.url.bs4 import _fetch_url_html


@pytest.fixture
async def site():
    """Local server: /ok answers, /redirect?to=<target> redirects to <target>."""

    async def ok(request):
        return web.Response(text="<html><body>fine</body></html>")

    async def redirect(request):
        raise web.HTTPFound(request.query["to"])

    app = web.Application()
    app.router.add_get("/ok", ok)
    app.router.add_get("/redirect", redirect)
    runner = web.AppRunner(app)
    await runner.setup()
    tcp = web.TCPSite(runner, "127.0.0.1", 0)
    await tcp.start()
    port = tcp._server.sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    await runner.cleanup()


@pytest.mark.parametrize(
    "address,blocked",
    [
        ("169.254.169.254", True),
        ("169.254.0.1", True),
        ("fe80::1", True),
        ("::ffff:169.254.169.254", True),
        ("fd00:ec2::254", True),
        ("127.0.0.1", False),
        ("10.0.0.5", False),
        ("192.168.1.10", False),
        ("8.8.8.8", False),
        ("::1", False),
    ],
)
def test_is_blocked_address(address, blocked):
    assert is_blocked_address(ipaddress.ip_address(address)) is blocked


def test_check_url_host_rejects_metadata_literal():
    with pytest.raises(BlockedAddressError):
        check_url_host("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(BlockedAddressError):
        check_url_host("http://[fd00:ec2::254]/latest/")


def test_check_url_host_allows_hostnames_and_private_ips():
    check_url_host("https://example.com/page")
    check_url_host("http://192.168.1.10:11434/")


def test_blocked_address_error_is_invalid_input():
    # Typed as invalid input, so retry logic treats it as permanent.
    assert issubclass(BlockedAddressError, InvalidInputError)


async def test_guarded_session_fetches_allowed_url(site):
    async with guarded_session() as session:
        async with session.get(guarded_request_url(f"{site}/ok")) as resp:
            assert resp.status == 200


async def test_guarded_session_follows_allowed_redirect(site):
    async with guarded_session() as session:
        async with session.get(f"{site}/redirect", params={"to": "/ok"}) as resp:
            assert resp.status == 200
            assert "fine" in await resp.text()


async def test_redirect_to_metadata_address_is_refused(site):
    async with guarded_session() as session:
        with pytest.raises(BlockedAddressError):
            async with session.get(
                f"{site}/redirect",
                params={"to": "http://169.254.169.254/latest/meta-data/"},
            ):
                pass


async def test_bs4_fetch_refuses_redirect_to_metadata(site):
    with pytest.raises(BlockedAddressError):
        await _fetch_url_html(
            f"{site}/redirect?to=http://169.254.169.254/latest/meta-data/"
        )


async def test_bs4_fetch_refuses_metadata_literal():
    with pytest.raises(BlockedAddressError):
        await _fetch_url_html("http://169.254.169.254/latest/meta-data/")


class _FakeResolver:
    def __init__(self, addresses):
        self.addresses = addresses

    async def resolve(self, host, port=0, family=socket.AF_INET):
        return [
            {
                "hostname": host,
                "host": a,
                "port": port,
                "family": family,
                "proto": 0,
                "flags": 0,
            }
            for a in self.addresses
        ]

    async def close(self):
        pass


async def test_resolver_refuses_host_resolving_only_to_link_local():
    resolver = GuardedResolver()
    resolver._resolver = _FakeResolver(["169.254.169.254"])
    with pytest.raises(BlockedAddressError):
        await resolver.resolve("metadata.attacker.test", 80)


async def test_resolver_drops_link_local_and_keeps_the_rest():
    resolver = GuardedResolver()
    resolver._resolver = _FakeResolver(["169.254.169.254", "93.184.216.34"])
    results = await resolver.resolve("mixed.test", 80)
    assert [r["host"] for r in results] == ["93.184.216.34"]


async def test_redirect_to_hostname_resolving_to_link_local_is_refused(
    site, monkeypatch
):
    real_resolve = GuardedResolver.resolve

    async def resolve(self, host, port=0, family=socket.AF_INET):
        if host == "metadata.attacker.test":
            self._resolver = _FakeResolver(["169.254.169.254"])
        return await real_resolve(self, host, port, family)

    monkeypatch.setattr(GuardedResolver, "resolve", resolve)
    # No proxy: the hostname must be resolved locally for this check.
    async with guarded_session(trust_env=False) as session:
        with pytest.raises(BlockedAddressError):
            async with session.get(
                f"{site}/redirect",
                params={"to": "http://metadata.attacker.test/latest/"},
            ):
                pass

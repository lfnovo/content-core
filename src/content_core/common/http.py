"""HTTP sessions for fetching user-supplied URLs.

Callers (Open Notebook, the MCP server) pass URLs they did not choose, and the
fetch runs from inside their network. ``guarded_session()`` refuses to connect
to link-local addresses (169.254.0.0/16, fe80::/10, which includes cloud
metadata services such as 169.254.169.254) and to AWS's IPv6 metadata address,
on the first request and on every redirect hop:

- hostnames are checked by the connector's resolver, on the addresses the
  connection will actually use (no re-resolution between check and connect);
- IP literals skip the resolver, so they are checked before the request and
  on each redirect ``Location``.

Private and loopback addresses stay allowed: self-hosted deployments
legitimately fetch from their own network. When the session goes through an
HTTP(S) proxy (``trust_env``), the target hostname is resolved by the proxy,
so only IP literals are checked locally.
"""

import ipaddress
import socket
from types import SimpleNamespace
from typing import Any

import aiohttp
from aiohttp.abc import AbstractResolver, ResolveResult
from yarl import URL

from content_core.common.exceptions import InvalidInputError

# AWS IMDSv6 is a Unique Local Address, not link-local.
_AWS_IMDS_V6 = ipaddress.ip_address("fd00:ec2::254")

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class BlockedAddressError(InvalidInputError):
    """Raised when a URL, or a redirect it leads to, targets a blocked address."""


def is_blocked_address(ip: IPAddress) -> bool:
    """True for link-local and cloud-metadata addresses."""
    if ip.is_link_local:
        return True
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None and mapped.is_link_local:
            return True
        # Compare without scope id so fd00:ec2::254%eth0 is caught too.
        if int(ip) == int(_AWS_IMDS_V6):
            return True
    return False


def _parse_ip(host: str) -> IPAddress | None:
    try:
        return ipaddress.ip_address(host.strip("[]").split("%", 1)[0])
    except ValueError:
        return None


def check_url_host(url: str | URL) -> None:
    """Raise BlockedAddressError if ``url``'s host is a blocked IP literal."""
    host = URL(str(url)).host or ""
    ip = _parse_ip(host)
    if ip is not None and is_blocked_address(ip):
        raise BlockedAddressError(
            f"Refusing to fetch {url}: link-local and cloud-metadata "
            "addresses are not allowed"
        )


class GuardedResolver(AbstractResolver):
    """Resolver that drops blocked addresses and fails if none remain."""

    def __init__(self) -> None:
        self._resolver = aiohttp.DefaultResolver()

    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> list[ResolveResult]:
        results = await self._resolver.resolve(host, port, family)
        allowed = [
            r
            for r in results
            if not ((ip := _parse_ip(r["host"])) and is_blocked_address(ip))
        ]
        if not allowed:
            raise BlockedAddressError(
                f"Refusing to fetch from {host}: it resolves to a link-local or "
                "cloud-metadata address"
            )
        return allowed

    async def close(self) -> None:
        await self._resolver.close()


async def _on_request_redirect(
    session: aiohttp.ClientSession,
    ctx: SimpleNamespace,
    params: aiohttp.TraceRequestRedirectParams,
) -> None:
    location = params.response.headers.get("Location") or params.response.headers.get(
        "URI"
    )
    if location:
        check_url_host(params.response.url.join(URL(location)))


def guarded_session(**kwargs: Any) -> aiohttp.ClientSession:
    """A ClientSession that refuses blocked addresses on every hop.

    Use it for any request whose URL comes from the caller. The initial URL's
    IP literal is checked by ``guarded_request_url``; pass the URL through it
    before the request.
    """
    trace = aiohttp.TraceConfig()
    trace.on_request_redirect.append(_on_request_redirect)
    kwargs.setdefault("trust_env", True)
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(resolver=GuardedResolver()),
        trace_configs=[trace],
        **kwargs,
    )


def guarded_request_url(url: str) -> str:
    """Check ``url``'s host before the first request; returns it unchanged."""
    check_url_host(url)
    return url

"""MCP server advertises the content-core package version."""

from importlib.metadata import version as pkg_version


def test_mcp_server_uses_content_core_version():
    from content_core.mcp.server import _package_version, mcp

    assert _package_version() == pkg_version("content-core")
    assert mcp.version == _package_version()

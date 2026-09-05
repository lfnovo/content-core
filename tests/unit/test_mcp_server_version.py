"""MCP server advertises the content-core package version."""

import importlib.metadata

import fastmcp


def test_mcp_server_uses_content_core_version():
    from content_core.mcp.server import mcp

    expected = importlib.metadata.version("content-core")

    assert mcp.version == expected
    assert mcp.version != fastmcp.__version__

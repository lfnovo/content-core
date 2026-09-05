"""MCP server advertises the content-core package version."""

import importlib.metadata


def test_mcp_server_uses_content_core_version():
    from content_core.mcp.server import mcp

    assert mcp.version == importlib.metadata.version("content-core")

"""Logging isolation tests (issue #47).

loguru's `logger` is a process-wide singleton, so these tests run each scenario
in a **subprocess** — configuring logging in-process would leak handler state
into every other test in the session.
"""
import subprocess
import sys

import pytest

# A "host application" that owns its logging config, then imports content_core.
HOST_APP = """
import sys
from loguru import logger

# The host app owns the single remove()/add() pair.
logger.remove()
logger.add(sys.stderr, level="DEBUG", format="{level} | {message}")

import content_core  # must not touch the config above

__EXTRA__

logger.debug("HOST_DEBUG_SURVIVES")
"""


def run_host_app(extra=""):
    """Run the host-app snippet in a fresh interpreter, return CompletedProcess."""
    # str.replace, not str.format — the snippet contains loguru format braces.
    return subprocess.run(
        [sys.executable, "-c", HOST_APP.replace("__EXTRA__", extra)],
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture(scope="module")
def default_import():
    return run_host_app()


def test_host_handler_survives_import(default_import):
    """Importing content_core must not clobber the host's DEBUG handler."""
    assert default_import.returncode == 0, default_import.stderr
    assert "HOST_DEBUG_SURVIVES" in default_import.stderr


def test_import_is_silent_by_default(default_import):
    """content_core must emit no log output of its own on import."""
    assert default_import.returncode == 0, default_import.stderr
    assert default_import.stdout == ""
    for line in default_import.stderr.splitlines():
        assert "content_core" not in line, f"leaked library log line: {line!r}"


# Exercises real library code, which logs at DEBUG from inside the
# content_core namespace — loguru's enable/disable keys off the record's module,
# so the log call must genuinely originate inside the package.
DO_WORK = (
    "import asyncio\n"
    "asyncio.run(content_core.extract(content='plain text'))\n"
)
# Marker: the DEBUG line content_core.processors.text emits for plain text.
LIBRARY_LOG = "No HTML detected"


def test_library_logs_are_disabled_by_default():
    """Log calls from inside the content_core namespace stay silent."""
    proc = run_host_app(extra=DO_WORK)
    assert proc.returncode == 0, proc.stderr
    assert LIBRARY_LOG not in proc.stderr


def test_configure_logging_enables_library_logs():
    """After the app calls configure_logging(), library logs appear again."""
    proc = run_host_app(extra="content_core.configure_logging(debug=True)\n" + DO_WORK)
    assert proc.returncode == 0, proc.stderr
    # Once via the host sink, once via the sink configure_logging added.
    assert proc.stderr.count(LIBRARY_LOG) == 2, proc.stderr
    # The host's own handler must still be alive alongside it.
    assert "HOST_DEBUG_SURVIVES" in proc.stderr


def test_configure_logging_does_not_duplicate_output():
    """Repeat calls must not stack sinks and double every line."""
    proc = run_host_app(
        extra="content_core.configure_logging(debug=True)\n" * 2 + DO_WORK
    )
    assert proc.returncode == 0, proc.stderr
    # Once from the host's DEBUG sink, once from configure_logging's sink —
    # the second configure_logging call must have replaced the first's sink.
    assert proc.stderr.count(LIBRARY_LOG) == 2, proc.stderr


def test_cli_debug_flag_reaches_mcp_entrypoint():
    """`content-core --debug mcp` must end up at DEBUG, not be reset to INFO.

    Regression: moving the logging setup into `main()` made it reconfigure at
    the default level, silently discarding the CLI's --debug flag.
    """
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys\n"
            "from unittest.mock import patch\n"
            "from click.testing import CliRunner\n"
            "from content_core.cli import cli\n"
            "with patch('content_core.mcp.server.mcp.run'), \\\n"
            "     patch('content_core.logging.configure_logging') as cfg:\n"
            "    import content_core.mcp.server as srv\n"
            "    with patch.object(srv, 'configure_logging', cfg):\n"
            "        res = CliRunner().invoke(cli, ['--debug', 'mcp'])\n"
            "    assert res.exit_code == 0, res.output\n"
            "print([c.kwargs.get('debug') for c in cfg.call_args_list])\n",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    # The MCP entrypoint must have been configured with debug=True.
    assert "True" in proc.stdout, proc.stdout


def test_mcp_entrypoint_configures_itself_without_click_context():
    """The bare `content-core-mcp` console script still configures logging."""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from unittest.mock import patch\n"
            "import content_core.mcp.server as srv\n"
            "with patch.object(srv, 'mcp'), \\\n"
            "     patch.object(srv, 'configure_logging') as cfg:\n"
            "    srv.main()\n"
            "assert cfg.call_count == 1, cfg.call_args_list\n"
            "print('debug=', cfg.call_args.kwargs.get('debug'))\n",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "debug= False" in proc.stdout, proc.stdout


def test_mcp_server_import_does_not_configure_logging():
    """Importing the MCP server module must not reconfigure logging either."""
    proc = run_host_app(extra="import content_core.mcp.server  # noqa: F401\n")
    assert proc.returncode == 0, proc.stderr
    assert "HOST_DEBUG_SURVIVES" in proc.stderr
    assert proc.stdout == "", f"MCP import wrote to stdout: {proc.stdout!r}"

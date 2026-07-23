import os
import sys

from loguru import logger

# Id of the stderr sink this module added, so repeat calls replace it.
_sink_id = None


def configure_logging(debug=False):
    """
    Enable and configure `content_core` logging.

    This is an *application-level* opt-in. As a library, ``content_core``
    disables its own logging at import time (``logger.disable("content_core")``)
    and never touches the host application's handlers. Call this only from an
    application entrypoint (CLI, MCP server, your own ``main()``).

    The sink it installs is deliberately unfiltered — an application entrypoint
    wants third-party loguru records too. A host application that already owns
    its own handlers should therefore NOT call this (it would get a second,
    duplicating stderr sink); it should just call ``logger.enable("content_core")``.

    Note: this adds a stderr sink to loguru's global logger; it deliberately does
    NOT call the blanket ``logger.remove()``, so any handlers the host app
    registered survive. It only drops loguru's own auto-added default sink (id 0,
    absent as soon as the host has called ``logger.remove()``) and any sink a
    previous ``configure_logging`` call added, so repeat calls do not duplicate
    output.

    Args:
        debug (bool): If True, force level DEBUG. Otherwise use the
            ``LOGURU_LEVEL`` environment variable, defaulting to INFO.
    """
    global _sink_id

    logger.enable("content_core")

    if _sink_id is not None:
        try:
            logger.remove(_sink_id)
        except ValueError:
            pass
        _sink_id = None

    # Drop loguru's default stderr sink so our sink does not double every line.
    # Raises ValueError when the host app has already removed it — nothing to do.
    try:
        logger.remove(0)
    except ValueError:
        pass

    level = "DEBUG" if debug else os.environ.get("LOGURU_LEVEL", "INFO")
    _sink_id = logger.add(sys.stderr, level=level)

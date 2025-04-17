import sys
from loguru import logger

def configure_logging(debug=False):
    """
    Configure the global logger for the application.
    
    Args:
        debug (bool): If True, set logging level to DEBUG; otherwise, set to INFO.
    """
    logger.remove()  # Remove any existing handlers
    logger.add(sys.stderr, level="DEBUG" if debug else "INFO")

# Initial configuration with default level (INFO)
configure_logging(debug=False)

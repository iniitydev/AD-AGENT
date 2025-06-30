# src/logger.py
import logging
import sys
from src.config import settings

# Configure logging
# Clear any existing handlers on the root logger
# This is important in some environments (like Uvicorn with --reload) to prevent duplicate logs
logging.getLogger().handlers = []

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout, # Default to stdout
)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance.
    """
    logger = logging.getLogger(name)
    # Ensure logger level is also set if it was already created with a different level
    logger.setLevel(settings.LOG_LEVEL.upper())
    return logger

# Example usage (optional, can be removed)
if __name__ == "__main__":
    # Test the logger
    settings.LOG_LEVEL = "DEBUG" # Temporarily override for testing

    # Re-initialize logging if LOG_LEVEL changed after initial basicConfig
    # This is a bit of a hack for standalone script testing; in app, settings are fixed on start
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    logger = get_logger(__name__)
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")

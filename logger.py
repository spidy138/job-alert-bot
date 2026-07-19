import logging
import sys

# Define VERBOSE level (below DEBUG)
VERBOSE = 5
logging.addLevelName(VERBOSE, "VERBOSE")

def setup_logger(level: str) -> logging.Logger:
    """
    Setup and return configured logger.

    Args:
        level: "INFO", "DEBUG", or "VERBOSE"

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("job_alert")

    # Clear existing handlers
    logger.handlers.clear()

    # Map level string to logging constant
    level_map = {
        "VERBOSE": VERBOSE,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
    }

    logger.setLevel(level_map.get(level, logging.INFO))

    # Console handler with formatted output
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level_map.get(level, logging.INFO))

    # Format: YYYY-MM-DD HH:MM:SS | LEVEL | message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

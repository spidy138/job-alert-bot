import logging
import pytest
from logger import setup_logger

def test_setup_logger_info_level():
    logger = setup_logger("INFO")
    assert logger.level == logging.INFO
    assert logger.name == "job_alert"

def test_setup_logger_debug_level():
    logger = setup_logger("DEBUG")
    assert logger.level == logging.DEBUG

def test_setup_logger_verbose_level():
    """VERBOSE is custom level below DEBUG"""
    logger = setup_logger("VERBOSE")
    assert logger.level == 5  # VERBOSE = 5, below DEBUG (10)

def test_logger_format():
    """Verify log format includes timestamp"""
    logger = setup_logger("INFO")
    handler = logger.handlers[0]
    formatter = handler.formatter
    # Format should contain timestamp, level, message
    assert "%(asctime)s" in formatter._fmt
    assert "%(levelname)s" in formatter._fmt

"""
Application Logging Configuration.

This module provides a centralized, structured logging setup for the Search Engine CLI.
It ensures that all application logs (crawling progress, indexing status, and search
queries) are formatted consistently and streamed to standard output for immediate
terminal feedback.
"""

import logging
import sys


def setup_logging() -> logging.Logger:
    """
    Configures industry-standard structured logging for the application.

    Initializes a singleton-like logger instance. It explicitly checks for
    existing handlers to prevent log duplication, which commonly occurs during
    multiple module imports or when running the Pytest test suite.

    Returns:
        logging.Logger: The configured application logger instance.
    """
    # Renamed from green_fintech to reflect the current domain
    logger = logging.getLogger("search_engine")

    # Only attach a new handler if none exist to prevent duplicate terminal lines
    if not logger.handlers:
        # INFO is the default level; DEBUG can be toggled later via Typer CLI flags
        logger.setLevel(logging.INFO)

        # Streamlined format specifically for clean CLI consumption
        # Removed the %(name)s parameter to keep the terminal output uncluttered
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Stream logs to stdout so they appear naturally in the shell
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# Instantiate a global logger instance to be imported across the application
logger = setup_logging()

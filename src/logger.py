"""
Application Logging Configuration.

Provides a centralized, rich-formatted logging setup for the Search Engine CLI.
"""

import logging

from rich.logging import RichHandler


def setup_logging() -> logging.Logger:
    """
    Configures industry-standard rich logging for the application.
    """
    logger = logging.getLogger("search_engine")

    if not logger.handlers:
        # Default to INFO to keep the standard terminal output clean
        logger.setLevel(logging.INFO)

        # RichHandler automatically aligns levels, colorizes output, and formats time
        rich_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,  # Allows us to use [green] tags in our log strings!
            show_path=False,  # Hides the file path to keep CLI output uncluttered
            log_time_format="%H:%M:%S"
        )

        # We don't need a complex string formatter because Rich handles the layout
        formatter = logging.Formatter("%(message)s")
        rich_handler.setFormatter(formatter)
        logger.addHandler(rich_handler)

    return logger


def set_verbose_mode() -> None:
    """Dynamically switches the logger to DEBUG level for deep diagnostics."""
    logger = logging.getLogger("search_engine")
    logger.setLevel(logging.DEBUG)


logger = setup_logging()

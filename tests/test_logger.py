import logging

from src.logger import set_verbose_mode, setup_logging


def test_logger_prevents_duplicate_handlers() -> None:
    """
    Test that calling setup_logging multiple times
    does not attach duplicate stream handlers.
    """
    # The first call (or the import itself) adds the initial handler
    logger = setup_logging()
    initial_handler_count = len(logger.handlers)

    assert initial_handler_count > 0

    # Call it a second time. The `if not logger.handlers:` evaluates to False.
    setup_logging()

    # The count must remain exactly the same to prevent terminal spam
    assert len(logger.handlers) == initial_handler_count


def test_set_verbose_mode() -> None:
    """Test that the verbose toggle sets the logger level to DEBUG."""
    logger = logging.getLogger("search_engine")

    # Trigger the function
    set_verbose_mode()

    # Assert the logging level changed
    assert logger.level == logging.DEBUG

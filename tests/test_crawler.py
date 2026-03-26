from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import RequestException

from src.crawler import PoliteCrawler


def test_crawler_extracts_quotes_successfully(mock_requests_get: MagicMock) -> None:
    """Test that the crawler successfully extracts quotes using the mocked HTML."""
    crawler = PoliteCrawler()
    quotes = crawler.fetch_quotes("http://fake-url.com")

    assert len(quotes) == 2
    assert "Albert Einstein" in quotes[0]["author"]
    assert "Harry" in quotes[1]["text"]
    mock_requests_get.assert_called_once_with(
        "http://fake-url.com", timeout=10)


def test_crawler_ignores_malformed_quotes() -> None:
    """
    Test that the crawler safely ignores quote blocks that are missing
    either the text span or the author tag, triggering the False branch.
    """
    malformed_html = """
    <html>
        <body>
            <div class="quote">
                <span class="text">"I have no author."</span>
            </div>
            <div class="quote">
                <small class="author">Ghost Writer</small>
            </div>
            <div class="quote">
            </div>
            <div class="quote">
                <span class="text">"I am a valid quote."</span>
                <small class="author">Valid Author</small>
            </div>
        </body>
    </html>
    """
    crawler = PoliteCrawler()

    # Bypass the network layer and test the parsing engine directly
    extracted_data = crawler._parse_html(malformed_html)

    # It should ignore the 3 malformed blocks and only extract the 1 valid block
    assert len(extracted_data) == 1
    assert extracted_data[0]["author"] == "Valid Author"
    assert extracted_data[0]["text"] == '"I am a valid quote."'


@patch("src.crawler.time.sleep")
@patch("src.crawler.time.time")
def test_crawler_enforces_6_second_politeness(
    mock_time: MagicMock,
    mock_sleep: MagicMock,
    mock_requests_get: MagicMock
) -> None:
    """Test that the crawler strictly enforces the 6-second delay between requests."""

    # Simulate time passing:
    # t=100.0 (End of Request 1)
    # t=102.0 (Start of Request 2, checking politeness)
    # t=102.1 (Consumed internally by logger.info generating its timestamp)
    # t=106.0 (End of Request 2)
    mock_time.side_effect = [100.0, 102.0, 102.1, 106.0]

    crawler = PoliteCrawler()

    # First request: last_request_time is 0.0, so it skips the sleep.
    crawler.fetch_quotes("http://fake-url.com/page/1")
    assert mock_sleep.call_count == 0

    # Second request: starts at t=102.0.
    # elapsed_time = 102.0 - 100.0 = 2.0.
    # 6.0 - 2.0 = 4.0. It MUST sleep for exactly 4.0 seconds.
    crawler.fetch_quotes("http://fake-url.com/page/2")
    mock_sleep.assert_called_once_with(4.0)


@patch("src.crawler.time.sleep")
@patch("src.crawler.time.time")
def test_crawler_skips_sleep_if_time_elapsed(
    mock_time: MagicMock,
    mock_sleep: MagicMock,
    mock_requests_get: MagicMock
) -> None:
    """Test that the crawler skips sleep if the 6-second window has naturally passed."""

    # Simulate time passing:
    # t=100.0 (End of Request 1)
    # t=110.0 (Start of Request 2. 10 seconds have passed!)
    # t=112.0 (End of Request 2)
    mock_time.side_effect = [100.0, 110.0, 112.0]

    crawler = PoliteCrawler()

    # First request finishes at t=100.0
    crawler.fetch_quotes("http://fake-url.com/page/1")

    # Second request starts at t=110.0.
    # elapsed_time = 10.0s. time_to_wait = -4.0s.
    # The `if time_to_wait > 0:` block evaluates to False!
    crawler.fetch_quotes("http://fake-url.com/page/2")

    # Sleep should NEVER be called because time_to_wait was negative
    assert mock_sleep.call_count == 0


def test_crawler_handles_http_errors(mocker: MagicMock) -> None:
    """Test that the crawler returns an empty list gracefully on HTTP failures."""
    # Create a mock that raises a RequestException
    mock_failed_get = mocker.patch(
        "requests.get", side_effect=RequestException("404 Not Found"))

    crawler = PoliteCrawler()
    quotes = crawler.fetch_quotes("http://fake-url.com/does-not-exist")

    # It should catch the error and return an empty list rather than crashing the app
    assert quotes == []
    mock_failed_get.assert_called_once()

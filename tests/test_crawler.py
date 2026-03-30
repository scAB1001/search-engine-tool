from unittest.mock import MagicMock, patch

import pytest
import requests

# TODO: Test for RequestException / place in conftest
from requests.exceptions import ConnectionError, RequestException

from src.crawler import PoliteCrawler


def test_crawler_extracts_quotes_successfully(mock_requests_get: MagicMock) -> None:
    """Test that the crawler successfully extracts quotes using the mocked HTML."""
    crawler = PoliteCrawler()
    result = crawler.fetch_quotes("http://fake-url.com")

    # Extract the list from the dictionary
    quotes = result["quotes"]

    assert len(quotes) == 2
    assert "Albert Einstein" in quotes[0]["author"]
    assert "Harry" in quotes[1]["text"]
    mock_requests_get.assert_called_once_with(
        "http://fake-url.com",
        headers={
            "User-Agent": "QuotesSearchEngineBot/1.0 (Educational Project)"},
        timeout=10.0
    )

def test_crawler_ignores_malformed_quotes(malformed_html_response: str) -> None:
    """
    Test that the crawler safely ignores quote blocks that are missing
    either the text span or the author tag, triggering the False branch.
    """
    # TODO: Move all html for testing to fixtures or alike
    crawler = PoliteCrawler()
    result = crawler._parse_html(malformed_html_response)

    # Extract the list from the dictionary
    extracted_quotes = result["quotes"]

    assert len(extracted_quotes) == 1
    assert extracted_quotes[0]["author"] == "Valid Author"
    assert extracted_quotes[0]["text"] == '"I am a valid quote."'


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


def test_crawler_rejects_non_html(mock_requests_get: MagicMock) -> None:
    """Test that the crawler safely aborts if the URL points to a non-HTML file."""
    # Simulate hitting a PDF or JSON endpoint
    mock_requests_get.return_value.headers = {
        "Content-Type": "application/pdf"}

    crawler = PoliteCrawler()
    results = crawler.fetch_quotes("http://fake-url.com/document.pdf")

    # It should immediately reject it without crashing or parsing
    assert results == {"quotes": [], "next_page": None}
    assert mock_requests_get.call_count == 1


def test_parse_html_extracts_relational_data(relational_html_response) -> None:
    """Test that the parser successfully extracts tags and author URLs."""
    crawler = PoliteCrawler()
    result = crawler._parse_html(relational_html_response)

    quote = result["quotes"][0]
    assert quote["author_url"] == "/author/Albert-Einstein"
    assert quote["tags"] == ["science"]
    assert result["next_page"] is None


def test_parse_html_handles_empty_pagination() -> None:
    """
    Test that the crawler safely stops when hitting the 'No quotes found!' edge case.
    """
    html = '<div class="col-md-8">No quotes found!</div>'
    crawler = PoliteCrawler()
    result = crawler._parse_html(html)

    assert result["quotes"] == []
    assert result["next_page"] is None


def test_fetch_author_handles_false_positive(mock_requests_get: MagicMock) -> None:
    """Test that the author scraper rejects 200 OK pages with missing data."""
    # Override the global fixture's text with our empty edge case
    html = '<div class="author-details"><h3 class="author-title"></h3></div>'
    mock_requests_get.return_value.text = html

    crawler = PoliteCrawler()
    author_data = crawler.fetch_author_metadata("http://fake.com/author")

    assert author_data == {}


def test_fetch_author_metadata_success(
    mock_requests_get: MagicMock,
    author_html_response: str
) -> None:
    """Test that author metadata is successfully parsed from the DOM."""
    # Inject the HTML fixture into the Network fixture
    mock_requests_get.return_value.text = author_html_response

    crawler = PoliteCrawler()
    author = crawler.fetch_author_metadata("http://fake-url.com/author")

    assert author["name"] == "Albert Einstein"
    assert author["born_date"] == "March 14, 1879"
    assert "Germany" in author["born_location"]
    assert "physicist" in author["description"]


@pytest.mark.parametrize("exception, expected_sleep_time, expected_calls", [
    (requests.exceptions.HTTPError("404 Not Found"), 0.0, 1),
    (requests.exceptions.Timeout("Connection timed out"), 10.0, 3),
    (requests.exceptions.ConnectionError("Connection refused"), 2.0, 3)
])
@patch("src.crawler.time.sleep")
def test_crawler_network_exceptions(
    mock_sleep: MagicMock,
    mock_requests_get: MagicMock,
    exception: Exception,
    expected_sleep_time: float,
    expected_calls: int
) -> None:
    """Test that fetch_quotes adheres to retry logic using parametrization."""
    mock_requests_get.side_effect = exception

    crawler = PoliteCrawler()
    results = crawler.fetch_quotes("http://fake-url.com")

    assert results == {"quotes": [], "next_page": None}
    assert mock_requests_get.call_count == expected_calls

    if expected_sleep_time > 0:
        assert mock_sleep.call_count == expected_calls - 1
        mock_sleep.assert_called_with(expected_sleep_time)
    else:
        assert mock_sleep.call_count == 0


@pytest.mark.parametrize("exception, expected_sleep_time, expected_calls", [
    (requests.exceptions.HTTPError("404 Not Found"), 0.0, 1),
    (requests.exceptions.Timeout("Connection timed out"), 10.0, 3),
    (requests.exceptions.ConnectionError("Connection refused"), 2.0, 3)
])
@patch("src.crawler.time.sleep")
def test_fetch_author_metadata_exceptions(
    mock_sleep: MagicMock,
    mock_requests_get: MagicMock,
    exception: Exception,
    expected_sleep_time: float,
    expected_calls: int
) -> None:
    """Test that fetch_author_metadata adheres to retry logic using parametrization."""
    mock_requests_get.side_effect = exception

    crawler = PoliteCrawler()
    assert crawler.fetch_author_metadata("http://fake-url.com/author") == {}

    assert mock_requests_get.call_count == expected_calls

    if expected_sleep_time > 0:
        assert mock_sleep.call_count == expected_calls - 1
        mock_sleep.assert_called_with(expected_sleep_time)
    else:
        assert mock_sleep.call_count == 0

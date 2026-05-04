from unittest.mock import MagicMock, patch

import pytest
import requests

from src.crawler import PoliteCrawler


def test_crawler_extracts_quotes_successfully(mock_requests_get: MagicMock) -> None:
    """Test that the crawler successfully extracts quotes using the mocked HTML."""
    crawler = PoliteCrawler()
    result = crawler.fetch_quotes("http://fake-url.com")

    quotes = result["quotes"]

    # The updated conftest fixture only contains 1 quote, but includes a next_page link
    assert len(quotes) == 1
    assert "Albert Einstein" in quotes[0]["author"]
    assert result["next_page"] == "/page/2/"

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
    crawler = PoliteCrawler()
    result = crawler._parse_html(malformed_html_response)

    extracted_quotes = result["quotes"]

    assert len(extracted_quotes) == 1
    assert extracted_quotes[0]["author"] == "Valid Author"
    assert extracted_quotes[0]["text"] == '"I am a valid quote."'


@patch("src.crawler.random.uniform")
@patch("src.crawler.time.sleep")
@patch("src.crawler.time.time")
def test_crawler_enforces_6_second_politeness(
    mock_time: MagicMock,
    mock_sleep: MagicMock,
    mock_random: MagicMock,
    mock_requests_get: MagicMock
) -> None:
    """Test that the crawler strictly enforces the 6-second delay + jitter."""
    mock_random.return_value = 1.0

    # t=100.0 (End of Request 1)
    # t=102.0 (Start of Request 2, checking politeness)
    # t=102.1 (Consumed internally by logger.info)
    # t=106.0 (End of Request 2)
    mock_time.side_effect = [100.0, 102.0, 102.1, 106.0]

    crawler = PoliteCrawler()

    crawler.fetch_quotes("http://fake-url.com/page/1")
    assert mock_sleep.call_count == 0

    crawler.fetch_quotes("http://fake-url.com/page/2")
    mock_sleep.assert_called_once_with(5.0)


@patch("src.crawler.time.sleep")
@patch("src.crawler.time.time")
def test_crawler_skips_sleep_if_time_elapsed(
    mock_time: MagicMock,
    mock_sleep: MagicMock,
    mock_requests_get: MagicMock
) -> None:
    """Test that the crawler skips sleep if the 6-second window has naturally passed."""
    mock_time.side_effect = [100.0, 110.0, 112.0]

    crawler = PoliteCrawler()
    crawler.fetch_quotes("http://fake-url.com/page/1")
    crawler.fetch_quotes("http://fake-url.com/page/2")

    assert mock_sleep.call_count == 0


def test_crawler_rejects_non_html(mock_requests_get: MagicMock) -> None:
    """Test that the crawler safely aborts if the URL points to a non-HTML file."""
    mock_requests_get.return_value.headers = {
        "Content-Type": "application/pdf"}

    crawler = PoliteCrawler()
    results = crawler.fetch_quotes("http://fake-url.com/document.pdf")

    assert results == {"quotes": [], "next_page": None}
    assert mock_requests_get.call_count == 1


def test_parse_html_extracts_relational_data(mock_html_response: str) -> None:
    """Test that the parser successfully extracts tags, author URLs, and pagination."""
    crawler = PoliteCrawler()
    # Uses the unified mock_html_response instead of the deleted relational fixture
    result = crawler._parse_html(mock_html_response)

    quote = result["quotes"][0]
    assert quote["author_url"] == "/author/Albert-Einstein"
    assert quote["tags"] == ["change", "thinking"]
    assert result["next_page"] == "/page/2/"


def test_crawler_handles_no_quotes_page(mock_requests_get: MagicMock) -> None:
    """Test that the crawler safely stops when no quotes are found on the page."""
    # Provide HTML without any quote blocks to simulate the end of pagination
    mock_requests_get.return_value.text = "<html><body>No quotes found!</body></html>"

    crawler = PoliteCrawler()
    # Actually call the network-dependent method
    result = crawler.fetch_quotes("http://fake-url.com/page/99")

    assert result["quotes"] == []
    assert result["next_page"] is None


def test_fetch_author_handles_false_positive(mock_requests_get: MagicMock) -> None:
    """Test that the author scraper rejects 200 OK pages with missing data."""
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


# ==========================================
# TEST PoliteCrawler.fetch_headers
# ==========================================

@patch("src.crawler.requests.head")
def test_fetch_headers_success(
    mock_head: MagicMock,
    mock_requests_get: MagicMock
) -> None:
    """Test fetch_headers returns headers on a successful HEAD request."""
    mock_response = MagicMock()
    mock_response.headers = {
        "Content-Type": "text/html",
        "Last-Modified": "Wed, 21 Oct 2015 07:28:00 GMT"
    }
    mock_head.return_value = mock_response

    crawler = PoliteCrawler()
    headers = crawler.fetch_headers("http://test.com")

    assert headers == mock_response.headers
    mock_head.assert_called_once_with(
        "http://test.com",
        headers=crawler.headers,
        timeout=10.0
    )


@patch("src.crawler.requests.head")
def test_fetch_headers_failure(
    mock_head: MagicMock,
    mock_requests_get: MagicMock
) -> None:
    """Test fetch_headers returns None and logs warning on request exception."""
    mock_head.side_effect = requests.exceptions.Timeout("Connection timed out")

    crawler = PoliteCrawler()
    headers = crawler.fetch_headers("http://test.com")

    assert headers is None
    # Also check that logger.warning was called (optional, but can be captured)
    # The line `logger.warning(...)` is executed, covering that branch.


def test_fetch_headers_enforces_politeness():
    """Test that fetch_headers respects the politeness window."""
    with patch('src.crawler.time.sleep') as mock_sleep, \
         patch('src.crawler.random.uniform', return_value=0.5), \
         patch('src.crawler.requests.head') as mock_head:

        mock_head.return_value = MagicMock(headers={})
        crawler = PoliteCrawler()

        # First request: initial last_request_time == 0 -> no politeness delay
        with patch('time.time', return_value=100.0):
            crawler.fetch_headers("http://test1.com")
        mock_sleep.assert_not_called()

        # Second request: only 4 seconds have passed -> must sleep
        mock_sleep.reset_mock()
        with patch('time.time', return_value=104.0):
            crawler.fetch_headers("http://test2.com")
        mock_sleep.assert_called_once_with(2.5)   # (6 - 4) + 0.5 = 2.5

        # Third request: now 7 seconds have passed -> no sleep
        mock_sleep.reset_mock()
        with patch('time.time', return_value=111.0):
            crawler.fetch_headers("http://test3.com")
        mock_sleep.assert_not_called()

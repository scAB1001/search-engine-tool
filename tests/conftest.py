import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.indexer import InvertedIndex
from src.search import SearchEngine


@pytest.fixture
def mock_html_response():
    """Provides a static HTML string representing the target website."""
    return """
    <html>
        <body>
            <div class ="col-md-8">
                <div class="quote" itemscope="" itemtype="http://schema.org/CreativeWork">
                    <span class="text" itemprop="text">
                        “The world as we have created it is a process of our thinking.
                        It cannot be changed without changing our thinking.”
                    </span>
                    <span>by
                        <small class="author" itemprop="author">Albert Einstein</small>
                        <a href="/author/Albert-Einstein">(about)</a>
                    </span>
                    <div class="tags">
                        Tags:
                        <a class="tag" href="/tag/change/page/1/">change</a>
                        <a class="tag" href="/tag/thinking/page/1/">thinking</a>
                    </div>
                </div>
                <nav>
                    <ul class="pager">
                        <li class="next"><a href="/page/2/">
                            Next <span aria-hidden="true">&rarr;</span>
                        </a></li>
                    </ul>
                </nav>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def malformed_html_response():
    """Provides HTML with missing tags/authors to test parser resilience."""
    return """
    <html>
        <body>
            <div class="quote"><span class="text">"I have no author."</span></div>
            <div class="quote"><small class="author">Ghost Writer</small></div>
            <div class="quote"></div>
            <div class="quote">
                <span class="text">"I am a valid quote."</span>
                <small class="author">Valid Author</small>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def author_html_response():
    """Provides HTML representing a successful author metadata page."""
    return """
    <div class="author-details">
        <h3 class="author-title">Albert Einstein</h3>
        <span class="author-born-date">March 14, 1879</span>
        <span class="author-born-location">in Ulm, Germany</span>
        <div class="author-description">A theoretical physicist.</div>
    </div>
    """


@pytest.fixture
def mock_requests_get(mocker, mock_html_response):
    """
    Intercepts requests.get globally.
    Defaults to the happy-path HTML, but allows tests to override the
    return_value or side_effect for pagination and error testing.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_response.text = mock_html_response

    return mocker.patch("requests.get", return_value=mock_response)


@pytest.fixture
def mock_index_file(tmp_path: Path) -> Path:
    """
    Creates a temporary, valid index.json file matching the BM25 Enterprise Schema.
    """
    file_path = tmp_path / "index.json"
    dummy_data = {
        "metadata": {"total_documents": 1},
        "document_registry": {
            "page_1_quote_0": {
                "text": "good friends are good",
                "author": "Tester",
                "url": "http://test",
                "length": 4
            }
        },
        "index": {
            "good": {
                "idf": 0.5,
                "collection_frequency": 2,
                "postings": {
                    "page_1_quote_0": {
                        "tf": 0.5,
                        "positions": [0, 3],
                        "zones": ["text"]
                    }
                }
            }
        }
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f)
    return file_path


@pytest.fixture
def populated_index() -> InvertedIndex:
    """Provides a pre-built index for testing search logic."""
    index = InvertedIndex()
    index.add_document("page_1", "good friends are good",
                       "Author A", ["tag1"], "http://url1")
    index.add_document("page_2", "good food is tasty",
                       "Author B", ["tag2"], "http://url2")
    index.add_document("page_3", "bad enemies are bad",
                       "Author C", ["tag3"], "http://url3")
    index.build_index()
    return index


@pytest.fixture
def blank_index() -> InvertedIndex:
    """Provides a fresh, empty InvertedIndex instance."""
    return InvertedIndex()


@pytest.fixture
def empty_index_file(tmp_path: Path) -> Path:
    """Provides a valid index file with zero documents for sitemap testing."""
    empty_index = tmp_path / "empty.json"
    empty_index.write_text(
        '{"metadata": {"total_documents": 0}, "document_registry": {}, "index": {}}'
    )
    return empty_index


@pytest.fixture
def multi_url_index_file(tmp_path: Path) -> Path:
    """Provides an index with varying URL depths to test sitemap prioritization."""
    multi_url_index = tmp_path / "multi.json"
    multi_url_index.write_text(json.dumps({
        "metadata": {"total_documents": 3},
        "document_registry": {
            "doc1": {"url": "https://test.com/"},           # Priority 1.0
            "doc2": {"url": "https://test.com/page/2/"},    # Priority 0.8
            "doc3": {"url": "https://test.com/about"}       # Priority 0.5
        },
        "index": {}
    }))
    return multi_url_index


@pytest.fixture
def engine(populated_index: InvertedIndex) -> SearchEngine:
    """Provides a pre-configured SearchEngine instance for search tests."""
    return SearchEngine(populated_index)


@pytest.fixture
def mock_get_path() -> MagicMock:
    """Centralized fixture to mock the index path resolution across all CLI tests."""
    with patch("src.main.get_index_path") as mock:
        yield mock

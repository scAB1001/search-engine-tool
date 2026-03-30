import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_html_response():
    """
    Provides a static HTML string representing the target website
    for deterministic testing.
    """
    return """
    <html>
        <body>
            <div class ="col-md-8">
                <div class="quote" itemscope=""
                     itemtype="http://schema.org/CreativeWork">
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
                        <meta class="keywords" itemprop="keywords"
                              content="change,deep-thoughts,thinking,world">
                        <a class="tag" href="/tag/change/page/1/">change</a>
                        <a class="tag" href="/tag/deep-thoughts/page/1/">
                            deep-thoughts
                        </a>
                        <a class="tag" href="/tag/thinking/page/1/">thinking</a>
                        <a class="tag" href="/tag/world/page/1/">world</a>
                    </div>
                </div>
                <div class="quote" itemscope=""
                     itemtype="http://schema.org/CreativeWork">
                    <span class="text" itemprop="text">
                        “It is our choices, Harry, that show what we truly are,
                        far more than our abilities.”
                    </span>
                    <span>by
                        <small class="author" itemprop="author">J.K. Rowling</small>
                        <a href="/author/J-K-Rowling">(about)</a>
                    </span>
                </div>
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


@pytest.fixture
def relational_html_response():
    """Provides HTML with author URLs and tags to test relational parsing."""
    return """
    <div class="quote">
        <span class="text">"Test Quote"</span>
        <span>by <small class="author">Albert Einstein</small>
        <a href="/author/Albert-Einstein">(about)</a></span>
        <div class="tags">
            <a class="tag" href="/tag/science/page/1/">science</a>
        </div>
    </div>
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
    Returns a mock response object with status 200, our fake HTML,
    and a valid MIME type to pass V2 Crawler checks.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html_response

    # Global MIME type validation bypass
    mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}

    # Patch the requests.get function wherever it is imported
    return mocker.patch("requests.get", return_value=mock_response)


@pytest.fixture
def mock_index_file(tmp_path: Path) -> Path:
    """Creates a temporary, valid index.json file for CLI happy paths."""
    file_path = tmp_path / "index.json"
    dummy_data = {
        "metadata": {"total_documents": 1},
        "index": {
            "good": {
                "idf": 0.5,
                "postings": {
                    "page_1": {"tf": 0.5, "positions": [0, 3]}
                }
            }
        }
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f)
    return file_path

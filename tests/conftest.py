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

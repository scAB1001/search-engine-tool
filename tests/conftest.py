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
            <div class="quote">
                <span class="text">
                    "The world as we have created it is a process of our thinking.
                    It cannot be changed without changing our thinking."
                </span>
                <small class="author">Albert Einstein</small>
            </div>
            <div class="quote">
                <span class="text">
                    "It is our choices, Harry, that show what we truly are,
                    far more than our abilities."
                </span>
                <small class="author">J.K. Rowling</small>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_requests_get(mocker, mock_html_response):
    """
    Intercepts requests.get globally.
    Returns a mock response object with status 200 and our fake HTML.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html_response

    # Patch the requests.get function wherever it is imported
    return mocker.patch("requests.get", return_value=mock_response)

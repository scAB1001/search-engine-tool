import time

import requests
from bs4 import BeautifulSoup

from src.logger import logger


class PoliteCrawler:
    """
    A web crawler that strictly adheres to a politeness window
    and gracefully handles network exceptions.
    """

    def __init__(self, delay_seconds: float = 6.0) -> None:
        self.delay_seconds = delay_seconds
        self.last_request_time = 0.0

    def _enforce_politeness(self) -> None:
        """
        Calculates and executes the necessary sleep time to respect the crawl delay.
        """
        if self.last_request_time == 0.0:
            return  # First request, no need to wait

        elapsed_time = time.time() - self.last_request_time
        time_to_wait = self.delay_seconds - elapsed_time

        if time_to_wait > 0:
            logger.info(
                f"Politeness window active. Sleeping for {time_to_wait:.2f} seconds...")
            time.sleep(time_to_wait)

    def fetch_quotes(self, url: str) -> list[dict[str, str]]:
        """
        Fetches and parses a single page of quotes.
        Returns a list of dictionaries containing the text and author.
        """
        self._enforce_politeness()

        try:
            # We use a 10-second timeout to prevent hanging on dead network connections
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx/5xx)

            # Record the exact time the request finished
            self.last_request_time = time.time()

            return self._parse_html(response.text)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}. Error: {e}")
            return []  # Fail gracefully

    def _parse_html(self, html_content: str) -> list[dict[str, str]]:
        """Extracts quote text and authors from the raw HTML using BeautifulSoup."""
        soup = BeautifulSoup(html_content, "html.parser")
        extracted_data = []

        # Target the specific CSS classes from https://quotes.toscrape.com/
        quote_blocks = soup.find_all("div", class_="quote")

        for block in quote_blocks:
            text_span = block.find("span", class_="text")
            author_small = block.find("small", class_="author")

            if text_span and author_small:
                extracted_data.append({
                    "text": text_span.get_text(strip=True),
                    "author": author_small.get_text(strip=True)
                })

        return extracted_data

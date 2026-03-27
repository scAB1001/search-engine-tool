import time

import requests
from bs4 import BeautifulSoup
from bs4.filter import SoupStrainer

from src.logger import logger


class PoliteCrawler:
    """
    A web crawler that strictly adheres to a politeness window
    and gracefully handles network exceptions.
    """

    def __init__(self, delay_seconds: float = 6.0) -> None:
        self.delay_seconds = delay_seconds
        self.last_request_time: float = 0.0
        # Identify our crawler to the server administrators
        self.headers = {
            "User-Agent": "QuotesSearchEngineBot/1.0 (Educational Project)"}

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
        Fetches and parses quotes from a given URL, utilising a retry mechanism
        for transient network failures and strict timeout limits.
        """
        self._enforce_politeness()
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            try:
                # Use a 10-second timeout to prevent hanging on dead network connections
                response = requests.get(url, headers=self.headers, timeout=10.0)
                response.raise_for_status()  # Raises HTTPError for responses 4xx/5xx

                # Record the exact time the request finished
                self.last_request_time = time.time()

                # Response Headers Verification
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    logger.warning(
                        f"Skipping {url}: Expected text/html, got {content_type}")
                    return []

                return self._parse_html(response.text)

            except requests.exceptions.Timeout as e:
                # Granular Exception Handling - 10s wait for Timeouts
                logger.warning(
                    f"Timeout on attempt {attempt}/{max_retries} "
                    f"for {url}: {e}. Waiting 10s.")
                if attempt == max_retries:
                    logger.error(f"Max retries reached for {url}. Abandoning.")
                    return []
                time.sleep(10.0)

            except requests.exceptions.ConnectionError as e:
                # Granular Exception Handling - 2s wait for Connection Errors
                logger.warning(
                    f"Connection error on attempt {attempt}/{max_retries} "
                    f"for {url}: {e}"
                )
                if attempt == max_retries:
                    logger.error(f"Max retries reached for {url}. Abandoning.")
                    return []
                time.sleep(2.0)

            except requests.exceptions.HTTPError as e:
                # 4xx or 5xx errors. Pointless retrying a 404.
                logger.error(f"HTTP Error for {url}: {e}")
                return []

        return []

    def _parse_html(self, html_content: str) -> list[dict[str, str]]:
        """
        Parses HTML using lxml, SoupStrainer for memory efficiency,
        and CSS selectors for precise extraction.
        """
        # Strain out navbars, footers, and scripts before RAM ingestion.
        # Strain for quotes and the 'next' button so our loop can still paginate later.
        strainer = SoupStrainer(class_=["quote", "next"])

        # Bypass the bottleneck by using 'html.parser' instead of the C-based 'lxml'
        soup = BeautifulSoup(html_content, "lxml", parse_only=strainer)

        parsed_data = []

        # Use CSS Selectors (.select) instead of .find_all
        for quote_block in soup.select(".quote"):

            # Extract data with .stripped_strings generator
            text_node = quote_block.select_one(".text")
            text = " ".join(text_node.stripped_strings) if text_node else ""

            author_node = quote_block.select_one(".author")
            author = " ".join(
                author_node.stripped_strings) if author_node else ""

            if text and author:
                parsed_data.append({
                    "text": text,
                    "author": author
                })

            # Physically destroy the node to free RAM
            quote_block.decompose()

        return parsed_data

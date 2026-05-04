import random
import time
from typing import Any

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
            "User-Agent": "QuotesSearchEngineBot/1.0 (Educational Project)"
        }

    def _enforce_politeness(self) -> None:
        """
        Ensures a strict minimum of 6 seconds between requests, plus a randomized
        jitter to avoid monotonous, detectable crawler patterns.
        """
        if self.last_request_time == 0.0:
            return

        elapsed_time = time.time() - self.last_request_time
        time_to_wait = 6.0 - elapsed_time

        if time_to_wait > 0:
            # Inject 0.0 to 2.0 seconds of random jitter
            jitter = random.uniform(0.0, 2.0)
            total_sleep = time_to_wait + jitter

            logger.debug(
                f"Politeness window active. Sleeping for "
                f"[yellow]{total_sleep:.2f}s[/yellow] (includes {jitter:.2f}s jitter)."
            )
            time.sleep(total_sleep)

    def _record_request(self) -> None:
        """Call this immediately after a request completes (success or failure)."""
        self.last_request_time = time.time()

    def fetch_quotes(self, url: str) -> dict[str, Any]:
        """
        Fetches and parses quotes from a given URL, utilizing a retry mechanism
        for transient network failures and strict timeout limits.
        """
        self._enforce_politeness()
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            try:
                # Use a 10-second timeout to prevent hanging on dead network connections
                response = requests.get(
                    url, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                self._record_request()

                # Response Headers Verification
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    logger.warning(
                        f"Skipping [cyan]{url}[/cyan]: Expected HTML, got "
                        f"[yellow]{content_type}[/yellow]"
                    )
                    return {"quotes": [], "next_page": None}

                return self._parse_html(response.text)

            except requests.exceptions.Timeout:
                # Granular Exception Handling - 10s wait for Timeouts
                self._record_request()
                logger.warning(
                    f"Timeout fetching [cyan]{url}[/cyan]"
                    f"(Attempt {attempt}/{max_retries}). Waiting 10s...")
                if attempt == max_retries:
                    logger.error(f"Max retries reached for {url}. Abandoning.")
                    return {"quotes": [], "next_page": None}
                time.sleep(10.0)

            except requests.exceptions.ConnectionError:
                # Granular Exception Handling - 2s wait for Connection Errors
                self._record_request()
                logger.warning(
                    f"Connection error fetching [cyan]{url}[/cyan] "
                    f"(Attempt {attempt}/{max_retries}). Waiting 2s..."
                )
                if attempt == max_retries:
                    logger.error(
                        f"Failed to fetch [cyan]{url}[/cyan]: Max retries exhausted."
                    )
                    return {"quotes": [], "next_page": None}
                time.sleep(2.0)

            except requests.exceptions.HTTPError as e:
                # 4xx or 5xx errors. Pointless retrying a 404.
                self._record_request()
                logger.error(f"HTTP Error for [cyan]{url}[/cyan]: {e}")
                return {"quotes": [], "next_page": None}

        # TODO: Create annotation for the empty quote state and others
        return {"quotes": [], "next_page": None}  # pragma: no cover

    def fetch_headers(self, url: str) -> dict[str, str] | None:
        """
        Perform a HEAD request respecting the politeness window.
        Returns the headers dictionary, or None on failure.
        """
        self._enforce_politeness()
        try:
            response = requests.head(url, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            self._record_request()
            return dict(response.headers)
        except Exception as e:
            self._record_request()
            logger.warning(f"HEAD request failed for [cyan]{url}[/cyan]: {e}")
            return None


    def fetch_author_metadata(self, author_url: str) -> dict[str, str]:
        """
        Navigates to an author's page and extracts their metadata.
        Includes protection against "False Positive" 200 OK pages with empty data.
        """
        self._enforce_politeness()
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(
                    author_url, headers=self.headers, timeout=10.0)
                response.raise_for_status()

                # CRITICAL: Record the exact time the request finished
                self.last_request_time = time.time()

                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    logger.warning(
                        f"Skipping [cyan]{author_url}[/cyan]: Expected HTML, "
                        f"got [yellow]{content_type}[/yellow]")  # pragma: no cover
                    return {} # pragma: no cover

                # Memory Saver: Only parse the author-details div
                strainer = SoupStrainer(class_="author-details")
                soup = BeautifulSoup(
                    response.text, "lxml", parse_only=strainer)

                title_node = soup.select_one(".author-title")
                name = " ".join(
                    title_node.stripped_strings) if title_node else ""

                # EDGE CASE DEFENSE: The "False Positive" Trap
                if not name:
                    logger.warning(
                        f"False Positive at [cyan]{author_url}[/cyan]: "
                        f"Empty author data.")
                    return {}

                born_date_node = soup.select_one(".author-born-date")
                born_location_node = soup.select_one(".author-born-location")
                description_node = soup.select_one(".author-description")

                return {
                    "name": name,
                    "born_date": " ".join(born_date_node.stripped_strings)
                        if born_date_node else "",
                    "born_location": " ".join(born_location_node.stripped_strings)
                        if born_location_node else "",
                    "description": " ".join(description_node.stripped_strings)
                        if description_node else ""
                }

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Timeout fetching [cyan]{author_url}[/cyan] "
                    f"(Attempt {attempt}/{max_retries}). Waiting 10s...")
                if attempt == max_retries:
                    logger.error(
                        f"Failed to fetch [cyan]{author_url}[/cyan]: "
                        f"Max retries exhausted.")
                    return {}
                time.sleep(10.0)

            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"Connection error on attempt {attempt}/{max_retries} "
                    f"for author {author_url}: {e}")
                if attempt == max_retries:
                    logger.error(
                        f"Failed to fetch [cyan]{author_url}[/cyan]: "
                        f"Max retries exhausted.")
                    return {}
                time.sleep(2.0)

            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP Error for [cyan]{author_url}[/cyan]: {e}")
                return {}

        return {}  # pragma: no cover

    def _parse_html(self, html_content: str) -> dict[str, Any]:
        """
        Parses HTML using lxml and CSS selectors.
        Returns a Dictionary containing the extracted quotes and the 'next' page URL.
        """
        # EDGE CASE DEFENSE: Out-of-Bounds Pagination
        if "No quotes found!" in html_content:
            logger.info(
                "Pagination boundary reached: [green]No quotes found![/green]")
            return {"quotes": [], "next_page": None}

        strainer = SoupStrainer(class_=["quote", "pager"])
        soup = BeautifulSoup(html_content, "lxml", parse_only=strainer)

        parsed_quotes = []

        for quote_block in soup.select(".quote"):
            text_node = quote_block.select_one(".text")
            text = " ".join(text_node.stripped_strings) if text_node else ""

            author_node = quote_block.select_one(".author")
            author_name = " ".join(
                author_node.stripped_strings) if author_node else ""

            # Relational Data Extraction
            author_link_node = quote_block.select_one("a[href^='/author/']")
            author_url = author_link_node["href"] if author_link_node else ""

            tags = [tag.get_text(strip=True)
                    for tag in quote_block.select(".tag")]

            if text and author_name:
                parsed_quotes.append({
                    "text": text,
                    "author": author_name,
                    "author_url": author_url,
                    "tags": tags
                })

            quote_block.decompose()

        # Extract the Next Page link to safely drive the while loop
        next_btn = soup.select_one(".next > a")
        next_page = next_btn["href"] if next_btn else None

        return {"quotes": parsed_quotes, "next_page": next_page}

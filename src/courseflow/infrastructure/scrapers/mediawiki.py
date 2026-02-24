"""MediaWiki API adapter implementation.

This module implements the ScrapingPort interface for fetching Wikipedia
article content via the MediaWiki REST API with rate limiting and retries.
"""

import re
from datetime import UTC, datetime
from typing import Any

import httpx

from courseflow.domain.scraping.exceptions import (
    ArticleNotFoundError,
    NetworkError,
    ParsingError,
    RateLimitError,
)
from courseflow.domain.scraping.ports import ScrapingPort
from courseflow.infrastructure.scrapers.rate_limiter import RateLimiter
from courseflow.infrastructure.scrapers.retry_strategy import with_retry


class MediaWikiAdapter(ScrapingPort):
    """MediaWiki API adapter implementing ScrapingPort interface.

    Handles communication with Wikipedia's MediaWiki REST API including
    rate limiting, redirects, and error handling.

    Attributes:
        base_url: Wikipedia API base URL
        rate_limiter: Rate limiter for API requests
        client: Async HTTP client
    """

    def __init__(
        self,
        base_url: str = "https://en.wikipedia.org/w/rest.php/v1",
        rate_limit: float = 1.0,
        timeout_seconds: int = 30,
        user_agent: str | None = None,
    ) -> None:
        """Initialize MediaWiki adapter.

        Args:
            base_url: MediaWiki REST API base URL
            rate_limit: Requests per second (default: 1.0)
            timeout_seconds: HTTP request timeout (default: 30)
            user_agent: User-Agent header (default: auto-generated)
        """
        self.base_url = base_url.rstrip("/")
        self.rate_limiter = RateLimiter(rate=rate_limit)
        self.timeout_seconds = timeout_seconds

        # Default User-Agent following Wikipedia guidelines
        if user_agent is None:
            user_agent = "CourseFlow/0.1.0 (Educational RAG System; contact@example.com)"

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )

    @with_retry(max_attempts=3)
    async def fetch_article(self, title: str) -> dict[str, Any]:
        """Fetch article content from Wikipedia.

        Args:
            title: Wikipedia article title

        Returns:
            Dictionary containing article data

        Raises:
            ArticleNotFoundError: Article does not exist (HTTP 404)
            RateLimitError: Rate limit exceeded (HTTP 429)
            NetworkError: Connection timeout or network failure
            ParsingError: Invalid API response format
        """
        try:
            current_title = title
            data: dict[str, Any] | None = None

            for _ in range(3):
                data = await self._request_page(current_title)
                redirect_target = self._extract_redirect_target(data)
                if not redirect_target or redirect_target == current_title:
                    break
                current_title = redirect_target

            if data is None:
                raise ParsingError(f"Failed to fetch article '{title}'")

            return self._build_article_dict(title, data)

        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timeout for article '{title}'", e) from e
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error fetching article '{title}'", e) from e
        except httpx.HTTPStatusError as e:
            raise NetworkError(f"HTTP error {e.response.status_code}", e) from e
        except ValueError as e:
            raise ParsingError(f"Invalid JSON response for article '{title}'") from e

    @with_retry(max_attempts=3)
    async def validate_article_exists(self, title: str) -> bool:
        """Check if article exists without fetching full content.

        Args:
            title: Wikipedia article title

        Returns:
            True if article exists, False if not found

        Raises:
            NetworkError: Connection timeout or network failure
        """
        async with self.rate_limiter:
            try:
                # Use HEAD request to check existence
                url = f"{self.base_url}/page/{self._encode_title(title)}"
                response = await self.client.head(url)

                if response.status_code == 404:
                    return False
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(retry_after=int(retry_after) if retry_after else None)

                response.raise_for_status()
                return True

            except httpx.TimeoutException as e:
                raise NetworkError(f"Request timeout checking article '{title}'", e) from e
            except httpx.NetworkError as e:
                raise NetworkError(f"Network error checking article '{title}'", e) from e
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return False
                raise NetworkError(f"HTTP error {e.response.status_code}", e) from e

    @with_retry(max_attempts=3)
    async def follow_redirect(self, title: str) -> str:
        """Resolve redirects to get canonical article title.

        Args:
            title: Original article title (may be redirect)

        Returns:
            Canonical title after following redirects

        Raises:
            ArticleNotFoundError: Article does not exist
            NetworkError: Connection timeout or network failure
        """
        async with self.rate_limiter:
            try:
                # Fetch article and check if it's a redirect
                article_data = await self.fetch_article(title)
                return article_data.get("canonical_title", title)

            except ArticleNotFoundError:
                raise
            except Exception as e:
                raise NetworkError(f"Failed to follow redirect for '{title}'", e) from e

    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self.client.aclose()

    def _encode_title(self, title: str) -> str:
        """Encode article title for URL.

        Args:
            title: Article title

        Returns:
            URL-encoded title
        """
        # Replace spaces with underscores (Wikipedia convention)
        encoded = title.replace(" ", "_")
        return encoded

    async def _request_page(self, title: str) -> dict[str, Any]:
        """Request one article page from MediaWiki REST API."""
        async with self.rate_limiter:
            url = f"{self.base_url}/page/{self._encode_title(title)}"
            response = await self.client.get(url)

            if response.status_code == 404:
                raise ArticleNotFoundError(title)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(retry_after=int(retry_after) if retry_after else None)
            if response.status_code >= 500:
                raise NetworkError(f"Wikipedia server error: HTTP {response.status_code}")

            response.raise_for_status()
            return response.json()

    def _extract_redirect_target(self, api_response: dict[str, Any]) -> str | None:
        """Extract redirect target from MediaWiki source content."""
        source = api_response.get("source")
        if not isinstance(source, str):
            return None

        match = re.match(r"^\s*#redirect\s*\[\[([^\]]+)\]\]", source, flags=re.IGNORECASE)
        if not match:
            return None

        target = match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
        return self._encode_title(target) if target else None

    def _build_article_dict(
        self, original_title: str, api_response: dict[str, Any]
    ) -> dict[str, Any]:
        """Build article dictionary from API response.

        Args:
            original_title: Original requested title
            api_response: Raw API response data

        Returns:
            Dictionary with standardized article data

        Raises:
            ParsingError: Missing required fields in response
        """
        try:
            # Extract fields from MediaWiki REST API response
            canonical_title = api_response.get("title", original_title)
            page_id = api_response.get("id")
            revision_id = api_response.get("latest", {}).get("id")

            # Get source content (wikitext or HTML)
            if "source" in api_response:
                content = api_response["source"]
            elif "html" in api_response:
                # For HTML response, would need additional processing
                content = api_response["html"]
            else:
                raise ParsingError("No content found in API response")

            # Calculate word count
            word_count = len(content.split())

            # Build source URL
            source_url = f"https://en.wikipedia.org/wiki/{self._encode_title(canonical_title)}"

            return {
                "title": original_title,
                "canonical_title": canonical_title,
                "source_url": source_url,
                "word_count": word_count,
                "retrieved_at": datetime.now(UTC),
                "raw_api_response": api_response,  # Store raw response for processor
                "api_response_metadata": {
                    "page_id": page_id,
                    "revision_id": revision_id,
                    "api_version": "rest_v1",
                },
            }

        except KeyError as e:
            raise ParsingError(f"Missing required field in API response: {e}") from e

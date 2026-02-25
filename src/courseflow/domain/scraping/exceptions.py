"""Custom exceptions for Wikipedia scraping.

This module defines all domain-specific exceptions used throughout
the scraping feature. Exceptions follow a hierarchy for precise error handling.
"""


class ScrapingError(Exception):
    """Base exception for all scraping-related errors."""

    def __init__(self, message: str, article_title: str | None = None) -> None:
        """Initialize scraping error.

        Args:
            message: Error description
            article_title: Optional article title where error occurred
        """
        self.message = message
        self.article_title = article_title
        super().__init__(message)


class ArticleNotFoundError(ScrapingError):
    """Article does not exist on Wikipedia (HTTP 404)."""

    def __init__(self, article_title: str) -> None:
        """Initialize article not found error.

        Args:
            article_title: Title of the missing article
        """
        super().__init__(f"Article not found: {article_title}", article_title=article_title)


class RateLimitError(ScrapingError):
    """Wikipedia API rate limit exceeded (HTTP 429)."""

    def __init__(self, retry_after: int | None = None) -> None:
        """Initialize rate limit error.

        Args:
            retry_after: Seconds to wait before retry (from Retry-After header)
        """
        message = "Rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        self.retry_after = retry_after
        super().__init__(message)


class NetworkError(ScrapingError):
    """Network connectivity or timeout error."""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        """Initialize network error.

        Args:
            message: Error description
            original_error: Original exception that caused this error
        """
        self.original_error = original_error
        super().__init__(message)


class ParsingError(ScrapingError):
    """Failed to parse MediaWiki API response."""

    def __init__(self, message: str, article_title: str | None = None) -> None:
        """Initialize parsing error.

        Args:
            message: Error description
            article_title: Article being parsed when error occurred
        """
        super().__init__(message, article_title=article_title)


class ChunkingError(ScrapingError):
    """Failed to chunk article content."""

    def __init__(self, message: str, article_title: str) -> None:
        """Initialize chunking error.

        Args:
            message: Error description
            article_title: Article being chunked when error occurred
        """
        super().__init__(message, article_title=article_title)


class StorageError(ScrapingError):
    """Failed to store chunks in ChromaDB."""

    def __init__(self, message: str, article_title: str | None = None) -> None:
        """Initialize storage error.

        Args:
            message: Error description
            article_title: Article being stored when error occurred
        """
        super().__init__(message, article_title=article_title)


class EmbeddingError(ScrapingError):
    """Failed to generate embeddings for chunks."""

    def __init__(self, message: str, article_title: str | None = None) -> None:
        """Initialize embedding error.

        Args:
            message: Error description
            article_title: Article being embedded when error occurred
        """
        super().__init__(message, article_title=article_title)

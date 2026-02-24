"""Port interfaces for Wikipedia scraping.

This module defines the port interfaces that must be implemented by
infrastructure adapters. These interfaces isolate domain logic from
external dependencies (Wikipedia API, ChromaDB, content processing).
"""

from abc import ABC, abstractmethod
from typing import Any

# Type aliases for clarity
ArticleTitle = str
ArticleContent = str
ChunkText = str


class ScrapingPort(ABC):
    """Port interface for fetching Wikipedia article content.

    Adapters implementing this port handle communication with Wikipedia's
    MediaWiki API, including rate limiting, redirects, and error handling.
    """

    @abstractmethod
    async def fetch_article(self, title: ArticleTitle) -> dict[str, Any]:
        """Fetch article content from Wikipedia.

        Args:
            title: Wikipedia article title (e.g., "Python (programming language)")

        Returns:
            Dictionary containing:
                - title: Original requested title
                - canonical_title: Final title after redirect resolution
                - content: Plain text article content
                - source_url: Full Wikipedia URL
                - word_count: Number of words in content
                - retrieved_at: UTC timestamp of fetch
                - api_response_metadata: Raw API metadata (revision_id, etc.)

        Raises:
            ArticleNotFoundError: Article does not exist (HTTP 404)
            RateLimitError: Rate limit exceeded (HTTP 429)
            NetworkError: Connection timeout or network failure
            ParsingError: Invalid or unexpected API response format
        """
        pass

    @abstractmethod
    async def validate_article_exists(self, title: ArticleTitle) -> bool:
        """Check if article exists without fetching full content.

        Args:
            title: Wikipedia article title

        Returns:
            True if article exists, False if not found (404)

        Raises:
            NetworkError: Connection timeout or network failure
        """
        pass

    @abstractmethod
    async def follow_redirect(self, title: ArticleTitle) -> ArticleTitle:
        """Resolve redirects to get canonical article title.

        Args:
            title: Original article title (may be redirect)

        Returns:
            Canonical title after following redirects

        Raises:
            ArticleNotFoundError: Article does not exist
            NetworkError: Connection timeout or network failure
        """
        pass


class StoragePort(ABC):
    """Port interface for storing and retrieving chunked articles.

    Adapters implementing this port handle ChromaDB operations including
    ingestion, deduplication, deletion, and metadata queries.
    """

    @abstractmethod
    async def ingest_chunks(
        self,
        chunks: list[dict[str, Any]],
        article_title: ArticleTitle
    ) -> int:
        """Ingest article chunks into ChromaDB with deduplication.

        Args:
            chunks: List of chunk dictionaries, each containing:
                - id: Unique chunk identifier
                - text: Chunk content
                - chunk_index: Position in article (0-indexed)
                - total_chunks: Total number of chunks for article
                - article_title: Source article title
                - source_url: Wikipedia URL
                - word_count: Words in this chunk
                - overlap_start: Overlap with previous chunk (character offset)
                - overlap_end: Overlap with next chunk (character offset)
                - created_at: UTC timestamp
            article_title: Article title for logging/error reporting

        Returns:
            Number of chunks successfully ingested

        Raises:
            StorageError: ChromaDB connection or ingestion failure
            EmbeddingError: Failed to generate embeddings for chunks
        """
        pass

    @abstractmethod
    async def check_article_exists(self, article_title: ArticleTitle) -> bool:
        """Check if article chunks already exist in ChromaDB.

        Args:
            article_title: Article title to check

        Returns:
            True if any chunks for this article exist, False otherwise
        """
        pass

    @abstractmethod
    async def delete_article(self, article_title: ArticleTitle) -> int:
        """Delete all chunks for an article from ChromaDB.

        Args:
            article_title: Article title to delete

        Returns:
            Number of chunks deleted

        Raises:
            StorageError: ChromaDB connection or deletion failure
        """
        pass

    @abstractmethod
    async def get_article_metadata(
        self,
        article_title: ArticleTitle
    ) -> dict[str, Any] | None:
        """Get metadata for an ingested article.

        Args:
            article_title: Article title to query

        Returns:
            Dictionary containing:
                - article_title: Article title
                - total_chunks: Number of chunks stored
                - source_url: Wikipedia URL
                - created_at: Timestamp of first chunk ingestion
                - last_updated: Timestamp of most recent chunk update
            Returns None if article not found in ChromaDB

        Raises:
            StorageError: ChromaDB query failure
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        article_filter: ArticleTitle | None = None
    ) -> list[dict[str, Any]]:
        """Semantic search across all ingested Wikipedia articles.

        Args:
            query: Natural language search query
            top_k: Number of results to return (default: 5)
            article_filter: Optional article title to filter results

        Returns:
            List of dictionaries containing:
                - text: Chunk content
                - article_title: Source article
                - source_url: Wikipedia URL
                - chunk_index: Position in article
                - relevance_score: Similarity score (0-1)

        Raises:
            StorageError: ChromaDB query failure
            EmbeddingError: Failed to embed query
        """
        pass

    @abstractmethod
    async def list_all_articles(self) -> list[dict[str, Any]]:
        """List all ingested Wikipedia articles with metadata.

        Returns:
            List of dictionaries containing:
                - article_title: Article title
                - total_chunks: Number of chunks
                - source_url: Wikipedia URL
                - created_at: Ingestion timestamp

        Raises:
            StorageError: ChromaDB query failure
        """
        pass


class ProcessingPort(ABC):
    """Port interface for processing article content into chunks.

    Adapters implementing this port handle text extraction, chunking with
    sentence boundaries, UTF-8 validation, and metadata enrichment.
    """

    @abstractmethod
    async def extract_content(self, raw_api_response: dict[str, Any]) -> ArticleContent:
        """Extract clean text content from MediaWiki API response.

        Args:
            raw_api_response: Raw JSON response from MediaWiki REST API

        Returns:
            Clean plain text content with:
                - HTML tags removed
                - Navigation/metadata/infoboxes excluded
                - Paragraph structure preserved
                - UTF-8 encoding validated

        Raises:
            ParsingError: Invalid or unexpected API response structure
        """
        pass

    @abstractmethod
    async def chunk_content(
        self,
        content: ArticleContent,
        article_title: ArticleTitle,
        source_url: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 100
    ) -> list[dict[str, Any]]:
        """Chunk article content with sentence boundaries and overlap.

        Args:
            content: Article plain text content
            article_title: Article title for metadata
            source_url: Wikipedia URL for metadata
            chunk_size: Target chunk size in words (default: 1000)
            chunk_overlap: Overlap between chunks in words (default: 100)

        Returns:
            List of chunk dictionaries (see StoragePort.ingest_chunks for schema)

        Raises:
            ChunkingError: Failed to chunk content (e.g., sentence tokenization error)
        """
        pass

    @abstractmethod
    async def validate_utf8(self, text: str) -> bool:
        """Validate text is valid UTF-8 without partial multibyte sequences.

        Args:
            text: Text to validate

        Returns:
            True if valid UTF-8, False if corrupted or partial sequences
        """
        pass

    @abstractmethod
    async def estimate_chunk_count(
        self,
        content: ArticleContent,
        chunk_size: int = 1000
    ) -> int:
        """Estimate number of chunks for article content.

        Args:
            content: Article plain text content
            chunk_size: Target chunk size in words

        Returns:
            Estimated number of chunks (for dry-run preview)
        """
        pass

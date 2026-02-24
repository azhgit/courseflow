"""Domain models for Wikipedia scraping.

This module defines all Pydantic models used in the Wikipedia scraping feature.
Models include validation rules, state transitions, and serialization methods.
"""

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class JobStatus(StrEnum):
    """Status of a scraping job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


class ScrapingConfig(BaseModel):
    """Configuration for a scraping job.

    Attributes:
        rate_limit: Requests per second (0.1-10.0)
        retry_attempts: Maximum retries for transient failures (0-5)
        timeout_seconds: HTTP request timeout in seconds (5-300)
        dry_run: If True, preview mode without actual scraping
        chunk_size: Target words per chunk (100-5000)
        chunk_overlap: Overlap words between chunks (0 to chunk_size/2)
    """

    rate_limit: float = Field(default=1.0, ge=0.1, le=10.0)
    retry_attempts: int = Field(default=3, ge=0, le=5)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    dry_run: bool = False
    no_ingest: bool = False
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=100, ge=0)

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap_size(cls, v: int, info) -> int:
        """Validate overlap does not exceed half of chunk size."""
        chunk_size = info.data.get("chunk_size", 1000)
        if v > chunk_size / 2:
            raise ValueError(
                f"Overlap ({v}) cannot exceed half of chunk size ({chunk_size})"
            )
        return v


class JobStatistics(BaseModel):
    """Aggregated metrics for a scraping job.

    Attributes:
        total_articles: Total articles attempted
        successful_articles: Articles successfully processed
        failed_articles: Articles that failed
        total_chunks_created: Total chunks ingested to ChromaDB
        total_processing_time_seconds: Total elapsed time
    """

    total_articles: int = Field(ge=0)
    successful_articles: int = Field(ge=0)
    failed_articles: int = Field(ge=0)
    total_chunks_created: int = Field(ge=0)
    total_processing_time_seconds: float = Field(ge=0.0)

    @model_validator(mode="after")
    def validate_article_counts(self):
        """Validate successful + failed equals total articles."""
        if self.successful_articles + self.failed_articles != self.total_articles:
            raise ValueError(
                f"successful ({self.successful_articles}) + failed "
                f"({self.failed_articles}) must equal total articles "
                f"({self.total_articles})"
            )
        return self


class ArticleError(BaseModel):
    """Error encountered while processing an article.

    Attributes:
        article_title: Article that failed
        error_type: Category of error (network, not_found, rate_limit, parsing, storage)
        error_message: Human-readable error description
        retry_count: Number of retries attempted
    """

    article_title: str
    error_type: str = Field(
        pattern=r"^(network|not_found|rate_limit|parsing|storage|chunking|embedding)$"
    )
    error_message: str
    retry_count: int = Field(ge=0)


class WikipediaArticle(BaseModel):
    """Retrieved Wikipedia article content.

    Represents intermediate data after fetching from API, before chunking.

    Attributes:
        title: User-provided article title
        canonical_title: Final title after following redirects
        source_url: Wikipedia article URL (canonical)
        content: Extracted main article text
        retrieved_at: Retrieval timestamp (UTC)
        word_count: Total words in article
        api_response_metadata: Raw metadata from API
    """

    title: str
    canonical_title: str
    source_url: HttpUrl
    content: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    word_count: int = Field(gt=0)
    api_response_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Warn if article content is very short (stub article)."""
        if len(v.strip()) < 100:
            import logging

            logging.warning(f"Article content is very short: {len(v)} characters")
        return v

    @field_validator("source_url")
    @classmethod
    def validate_wikipedia_domain(cls, v: HttpUrl) -> HttpUrl:
        """Validate URL is from wikipedia.org domain."""
        if "wikipedia.org" not in str(v):
            raise ValueError("URL must be from wikipedia.org domain")
        return v

    @property
    def requires_chunking(self) -> bool:
        """Whether article needs to be split into multiple chunks."""
        return self.word_count > 1000


class ContentChunk(BaseModel):
    """Processed text segment ready for embedding and ChromaDB storage.

    Attributes:
        id: Unique chunk identifier
        text: Chunk content (≤1200 words, complete sentences)
        chunk_index: Position in article (0-based)
        total_chunks: Total chunks from parent article
        article_title: Parent article canonical title
        source_url: Parent article URL
        word_count: Words in this chunk
        overlap_start: Character offset where overlap with previous chunk starts
        overlap_end: Character offset where overlap with next chunk starts
        created_at: Chunk creation timestamp (UTC)
    """

    id: UUID = Field(default_factory=uuid4)
    text: str
    chunk_index: int = Field(ge=0)
    total_chunks: int = Field(gt=0)
    article_title: str
    source_url: HttpUrl
    word_count: int = Field(gt=0)
    overlap_start: int = Field(ge=0)
    overlap_end: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("text")
    @classmethod
    def validate_chunk_size(cls, v: str) -> str:
        """Validate chunk size is within acceptable bounds."""
        words = len(v.split())
        if words > 1200:  # 1000 + 100 overlap + 100 buffer
            raise ValueError(f"Chunk too large: {words} words (max 1200)")
        if words == 0:
            raise ValueError("Chunk cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_chunk_index_bounds(self):
        """Validate chunk index is less than total chunks."""
        if self.chunk_index >= self.total_chunks:
            raise ValueError(
                f"chunk_index ({self.chunk_index}) must be < total_chunks ({self.total_chunks})"
            )
        return self

    @field_validator("overlap_end")
    @classmethod
    def validate_overlap_end(cls, v: int, info) -> int:
        """Validate overlap_end does not exceed text length."""
        text = info.data.get("text", "")
        if v > len(text):
            raise ValueError(
                f"overlap_end ({v}) cannot exceed text length ({len(text)})"
            )
        return v

    def to_chroma_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata dictionary.

        Returns:
            Dictionary with article metadata for ChromaDB storage
        """
        return {
            "article_title": self.article_title,
            "source_url": str(self.source_url),
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "scrape_timestamp": self.created_at.isoformat(),
            "word_count": self.word_count,
        }

    def to_chroma_id(self) -> str:
        """Generate deterministic ChromaDB document ID.

        Uses MD5 hash of source URL + chunk index for deduplication.

        Returns:
            Deterministic ID string (e.g., "a3f8e92c_0")
        """
        url_hash = hashlib.md5(str(self.source_url).encode()).hexdigest()[:8]
        return f"{url_hash}_{self.chunk_index}"


class ScrapingJob(BaseModel):
    """Scraping operation triggered via CLI.

    Tracks job lifecycle, configuration, and results.

    Attributes:
        id: Unique job identifier
        topics: Wikipedia article titles to scrape
        config: Job configuration (rate limit, dry-run, etc.)
        status: Current job state
        start_time: Job start timestamp (UTC)
        end_time: Job completion timestamp (UTC), None while running
        statistics: Success/fail counts, timing metrics
        errors: Errors encountered during scraping
    """

    id: UUID = Field(default_factory=uuid4)
    topics: list[str] = Field(min_length=1, max_length=100)
    config: ScrapingConfig
    status: JobStatus = JobStatus.PENDING
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    statistics: JobStatistics
    errors: list[ArticleError] = Field(default_factory=list)

    @field_validator("topics")
    @classmethod
    def validate_unique_topics(cls, v: list[str]) -> list[str]:
        """Validate topics are unique (no duplicates)."""
        if len(v) != len(set(v)):
            raise ValueError("Topics must be unique (no duplicates)")
        return v

    @field_validator("topics")
    @classmethod
    def validate_non_empty_titles(cls, v: list[str]) -> list[str]:
        """Validate article titles are not empty."""
        for topic in v:
            if not topic.strip():
                raise ValueError("Article titles cannot be empty")
        return v

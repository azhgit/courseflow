"""Unit tests for domain models.

Tests all Pydantic model validation rules, field validators,
cross-field validation, state transitions, and serialization.
"""

import pytest
from datetime import datetime, UTC
from uuid import UUID

from courseflow.domain.scraping.models import (
    ArticleError,
    ContentChunk,
    JobStatistics,
    JobStatus,
    ScrapingConfig,
    ScrapingJob,
    WikipediaArticle,
)


class TestScrapingConfig:
    """Test ScrapingConfig model validation."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ScrapingConfig()
        assert config.rate_limit == 1.0
        assert config.retry_attempts == 3
        assert config.timeout_seconds == 30
        assert config.dry_run is False
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 100

    def test_rate_limit_validation(self):
        """Test rate limit bounds validation."""
        # Valid rate limits
        ScrapingConfig(rate_limit=0.1)
        ScrapingConfig(rate_limit=10.0)

        # Invalid rate limits
        with pytest.raises(ValueError):
            ScrapingConfig(rate_limit=0.05)  # Too low

        with pytest.raises(ValueError):
            ScrapingConfig(rate_limit=15.0)  # Too high

    def test_chunk_overlap_validation(self):
        """Test chunk overlap cannot exceed half of chunk size."""
        # Valid overlap
        ScrapingConfig(chunk_size=1000, chunk_overlap=500)

        # Invalid overlap (exceeds half)
        with pytest.raises(ValueError, match="cannot exceed half"):
            ScrapingConfig(chunk_size=1000, chunk_overlap=600)


class TestJobStatistics:
    """Test JobStatistics model validation."""

    def test_article_counts_validation(self):
        """Test successful + failed must equal total."""
        # Valid statistics
        JobStatistics(
            total_articles=10,
            successful_articles=7,
            failed_articles=3,
            total_chunks_created=100,
            total_processing_time_seconds=45.5,
        )

        # Invalid: sum doesn't match total
        with pytest.raises(ValueError, match="must equal total articles"):
            JobStatistics(
                total_articles=10,
                successful_articles=6,
                failed_articles=3,  # 6 + 3 = 9, not 10
                total_chunks_created=100,
                total_processing_time_seconds=45.5,
            )


class TestArticleError:
    """Test ArticleError model validation."""

    def test_valid_error_types(self):
        """Test valid error type patterns."""
        valid_types = ["network", "not_found", "rate_limit", "parsing", "storage"]
        for error_type in valid_types:
            error = ArticleError(
                article_title="Test Article",
                error_type=error_type,
                error_message="Test error",
                retry_count=3,
            )
            assert error.error_type == error_type

    def test_invalid_error_type(self):
        """Test invalid error type is rejected."""
        with pytest.raises(ValueError):
            ArticleError(
                article_title="Test Article",
                error_type="invalid_type",
                error_message="Test error",
                retry_count=3,
            )


class TestWikipediaArticle:
    """Test WikipediaArticle model validation."""

    def test_wikipedia_url_validation(self):
        """Test URL must be from wikipedia.org domain."""
        # Valid URL
        article = WikipediaArticle(
            title="Python",
            canonical_title="Python (programming language)",
            source_url="https://en.wikipedia.org/wiki/Python_(programming_language)",
            content="Python is a programming language",
            word_count=5,
        )
        assert article.source_url

        # Invalid URL (not wikipedia.org)
        with pytest.raises(ValueError, match="wikipedia.org"):
            WikipediaArticle(
                title="Python",
                canonical_title="Python",
                source_url="https://example.com/python",
                content="Python content",
                word_count=5,
            )

    def test_requires_chunking(self):
        """Test requires_chunking property."""
        # Small article doesn't need chunking
        small_article = WikipediaArticle(
            title="Short",
            canonical_title="Short",
            source_url="https://en.wikipedia.org/wiki/Short",
            content="Short content",
            word_count=500,
        )
        assert not small_article.requires_chunking

        # Large article needs chunking
        large_article = WikipediaArticle(
            title="Long",
            canonical_title="Long",
            source_url="https://en.wikipedia.org/wiki/Long",
            content="Long content " * 1000,
            word_count=5000,
        )
        assert large_article.requires_chunking


class TestContentChunk:
    """Test ContentChunk model validation."""

    def test_chunk_size_validation(self):
        """Test chunk cannot exceed maximum size."""
        # Valid chunk
        chunk = ContentChunk(
            text=" ".join(["word"] * 1000),  # 1000 words
            chunk_index=0,
            total_chunks=1,
            article_title="Test",
            source_url="https://en.wikipedia.org/wiki/Test",
            word_count=1000,
            overlap_start=0,
            overlap_end=4999,
        )
        assert chunk.word_count == 1000

        # Invalid: too large
        large_text = " ".join(["word"] * 1300)  # Exceeds 1200 limit
        with pytest.raises(ValueError, match="too large"):
            ContentChunk(
                text=large_text,
                chunk_index=0,
                total_chunks=1,
                article_title="Test",
                source_url="https://en.wikipedia.org/wiki/Test",
                word_count=1300,
                overlap_start=0,
                overlap_end=len(large_text),
            )

    def test_chunk_index_bounds(self):
        """Test chunk_index must be less than total_chunks."""
        # Valid index
        ContentChunk(
            text="test content",
            chunk_index=0,
            total_chunks=5,
            article_title="Test",
            source_url="https://en.wikipedia.org/wiki/Test",
            word_count=2,
            overlap_start=0,
            overlap_end=12,
        )

        # Valid: last index
        ContentChunk(
            text="test content",
            chunk_index=4,
            total_chunks=5,
            article_title="Test",
            source_url="https://en.wikipedia.org/wiki/Test",
            word_count=2,
            overlap_start=0,
            overlap_end=12,
        )

        # Invalid: index >= total (should be 6 >= 5)
        with pytest.raises(ValueError, match="must be <"):
            ContentChunk(
                text="test content",
                chunk_index=6,
                total_chunks=5,
                article_title="Test",
                source_url="https://en.wikipedia.org/wiki/Test",
                word_count=2,
                overlap_start=0,
                overlap_end=12,
            )

    def test_to_chroma_metadata(self):
        """Test conversion to ChromaDB metadata format."""
        chunk = ContentChunk(
            text="test content",
            chunk_index=3,
            total_chunks=10,
            article_title="Python",
            source_url="https://en.wikipedia.org/wiki/Python",
            word_count=2,
            overlap_start=0,
            overlap_end=12,
        )

        metadata = chunk.to_chroma_metadata()
        assert metadata["article_title"] == "Python"
        assert metadata["chunk_index"] == 3
        assert metadata["total_chunks"] == 10
        assert metadata["word_count"] == 2
        assert "scrape_timestamp" in metadata

    def test_to_chroma_id(self):
        """Test deterministic ID generation."""
        chunk = ContentChunk(
            text="test content",
            chunk_index=5,
            total_chunks=10,
            article_title="Test",
            source_url="https://en.wikipedia.org/wiki/Test",
            word_count=2,
            overlap_start=0,
            overlap_end=12,
        )

        chunk_id = chunk.to_chroma_id()
        assert "_" in chunk_id
        assert chunk_id.endswith("_5")  # chunk_index in ID

        # Same URL and index should produce same ID
        chunk2 = ContentChunk(
            text="different content",
            chunk_index=5,
            total_chunks=10,
            article_title="Test",
            source_url="https://en.wikipedia.org/wiki/Test",
            word_count=2,
            overlap_start=0,
            overlap_end=17,
        )
        assert chunk.to_chroma_id() == chunk2.to_chroma_id()


class TestScrapingJob:
    """Test ScrapingJob model validation."""

    def test_unique_topics_validation(self):
        """Test topics must be unique (no duplicates)."""
        # Valid unique topics
        job = ScrapingJob(
            topics=["Python", "Machine Learning", "AI"],
            config=ScrapingConfig(),
            statistics=JobStatistics(
                total_articles=0,
                successful_articles=0,
                failed_articles=0,
                total_chunks_created=0,
                total_processing_time_seconds=0.0,
            ),
        )
        assert len(job.topics) == 3

        # Invalid: duplicate topics
        with pytest.raises(ValueError, match="unique"):
            ScrapingJob(
                topics=["Python", "Python", "AI"],
                config=ScrapingConfig(),
                statistics=JobStatistics(
                    total_articles=0,
                    successful_articles=0,
                    failed_articles=0,
                    total_chunks_created=0,
                    total_processing_time_seconds=0.0,
                ),
            )

    def test_non_empty_titles_validation(self):
        """Test article titles cannot be empty."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ScrapingJob(
                topics=["Python", "  ", "AI"],  # Empty title
                config=ScrapingConfig(),
                statistics=JobStatistics(
                    total_articles=0,
                    successful_articles=0,
                    failed_articles=0,
                    total_chunks_created=0,
                    total_processing_time_seconds=0.0,
                ),
            )

    def test_default_values(self):
        """Test default job values."""
        job = ScrapingJob(
            topics=["Test"],
            config=ScrapingConfig(),
            statistics=JobStatistics(
                total_articles=1,
                successful_articles=0,
                failed_articles=1,
                total_chunks_created=0,
                total_processing_time_seconds=0.0,
            ),
        )

        assert job.status == JobStatus.PENDING
        assert isinstance(job.id, UUID)
        assert isinstance(job.start_time, datetime)
        assert job.end_time is None
        assert job.errors == []

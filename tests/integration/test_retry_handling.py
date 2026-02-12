"""Integration tests for automatic retry and graceful failure handling.

Tests User Story 4: Automatic Retry with Graceful Failure Handling
- Rate limit retry with eventual success
- Retry exhaustion with rollback
- Transient error recovery
- Queue depth limit enforcement
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from courseflow.application.ingestion_service import IngestionService
from courseflow.domain.exceptions import (
    IngestionFailedError,
    QueueFullError,
)
from courseflow.infrastructure.rate_limiting import RateLimiter


@pytest.fixture
def mock_subject_repo():
    """Mock subject repository."""
    repo = AsyncMock()
    repo.subject_exists = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_document_repo():
    """Mock document repository."""
    repo = AsyncMock()
    repo.find_by_content_hash = AsyncMock(return_value=None)
    repo.save_document = AsyncMock()
    return repo


@pytest.fixture
def mock_chunk_repo():
    """Mock chunk repository."""
    repo = AsyncMock()
    repo.save_chunks = AsyncMock()
    repo.delete_chunks_by_document_id = AsyncMock()
    return repo


@pytest.fixture
def mock_embedding_port():
    """Mock embedding port for testing retry scenarios."""
    port = AsyncMock()
    port.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    return port


@pytest.fixture
def mock_pdf_extractor():
    """Mock PDF extractor."""
    extractor = AsyncMock()
    extractor.extract_text = AsyncMock(return_value="Sample text content")
    return extractor


@pytest.fixture
def mock_token_counter():
    """Mock token counter."""
    counter = Mock()
    counter.count_tokens = Mock(return_value=100)
    return counter


@pytest.fixture
def mock_sentence_tokenizer():
    """Mock sentence tokenizer."""
    tokenizer = Mock()
    tokenizer.tokenize = Mock(return_value=["Sample text content."])
    return tokenizer


@pytest.fixture
def mock_chunker():
    """Mock chunker that returns simple chunks."""
    from courseflow.domain.models import Chunk

    chunker = Mock()
    chunker.create_chunks = Mock(
        return_value=[
            Chunk(
                text="Sample text content.",
                document_id="test-doc-id",
                chunk_index=0,
                token_count=100,
                subject="general",
                source_filename="test.txt",
            )
        ]
    )
    return chunker


@pytest.fixture
def ingestion_service_with_rate_limiter(
    mock_pdf_extractor,
    mock_token_counter,
    mock_sentence_tokenizer,
    mock_chunker,
    mock_embedding_port,
    mock_subject_repo,
    mock_document_repo,
    mock_chunk_repo,
):
    """IngestionService with custom rate limiter for testing."""
    rate_limiter = RateLimiter(requests_per_minute=15, max_queue_depth=10)
    return IngestionService(
        pdf_extractor=mock_pdf_extractor,
        token_counter=mock_token_counter,
        sentence_tokenizer=mock_sentence_tokenizer,
        chunker=mock_chunker,
        embedding_port=mock_embedding_port,
        subject_repo=mock_subject_repo,
        document_repo=mock_document_repo,
        chunk_repo=mock_chunk_repo,
        rate_limiter=rate_limiter,
    )


@pytest.mark.asyncio
async def test_retry_with_success_after_transient_failure(
    ingestion_service_with_rate_limiter, mock_embedding_port
):
    """Test T063: Rate limit retry succeeds after transient failure.

    Scenario: First attempt fails, retry succeeds
    Expected: Document ingested successfully, no IngestionFailedError
    """
    # Simulate transient failure then success
    mock_embedding_port.generate_embedding = AsyncMock(
        side_effect=[
            Exception("Transient API error"),  # First attempt fails
            [0.1] * 768,  # Second attempt succeeds
        ]
    )

    file_bytes = b"Test content for retry scenario"
    result = await ingestion_service_with_rate_limiter.ingest_document(
        file_bytes=file_bytes, filename="retry_test.txt", subject="general"
    )

    assert result.success is True
    assert result.chunks_created == 1
    assert result.skipped is False

    # Verify retry happened (called twice)
    assert mock_embedding_port.generate_embedding.call_count == 2


@pytest.mark.asyncio
async def test_retry_exhaustion_raises_ingestion_failed(
    ingestion_service_with_rate_limiter, mock_embedding_port
):
    """Test T064: Retry exhaustion with proper error after max attempts.

    Scenario: All retry attempts fail
    Expected: IngestionFailedError with retry_count=5, chunks rolled back
    """
    # Simulate persistent failure
    mock_embedding_port.generate_embedding = AsyncMock(
        side_effect=Exception("Persistent API error")
    )

    file_bytes = b"Test content that will fail"

    with pytest.raises(IngestionFailedError) as exc_info:
        await ingestion_service_with_rate_limiter.ingest_document(
            file_bytes=file_bytes, filename="fail_test.txt", subject="general"
        )

    error = exc_info.value
    assert "retries" in str(error).lower()
    assert error.retry_count == 5  # Max retries reached

    # Verify all retry attempts were made (1 initial + 5 retries = 6 total)
    assert mock_embedding_port.generate_embedding.call_count == 6


@pytest.mark.asyncio
async def test_transient_error_recovery(ingestion_service_with_rate_limiter, mock_embedding_port):
    """Test T065: Transient error recovery without administrator intervention.

    Scenario: Multiple transient failures followed by success
    Expected: Document ingested successfully after automatic retries
    """
    # Simulate 3 transient failures then success
    mock_embedding_port.generate_embedding = AsyncMock(
        side_effect=[
            Exception("Network timeout"),
            Exception("Connection reset"),
            Exception("Temporary unavailable"),
            [0.1] * 768,  # Finally succeeds
        ]
    )

    file_bytes = b"Test content with multiple retries"
    result = await ingestion_service_with_rate_limiter.ingest_document(
        file_bytes=file_bytes, filename="transient_test.txt", subject="general"
    )

    assert result.success is True
    assert result.chunks_created == 1

    # Verify retry happened 4 times total (3 failures + 1 success)
    assert mock_embedding_port.generate_embedding.call_count == 4


@pytest.mark.asyncio
async def test_queue_full_error_enforcement():
    """Test T066: Queue depth limit enforcement.

    Scenario: Exceed max_queue_depth directly via rate limiter
    Expected: QueueFullError raised for requests beyond queue limit
    """
    rate_limiter = RateLimiter(requests_per_minute=5, max_queue_depth=3)

    results = []

    async def make_slow_request(idx):
        try:
            async with rate_limiter.acquire(request_id=f"req_{idx}"):
                await asyncio.sleep(2.0)  # Hold the token
                return f"success_{idx}"
        except QueueFullError as e:
            return e

    # Start 10 concurrent requests with queue limit of 3
    tasks = [asyncio.create_task(make_slow_request(i)) for i in range(10)]

    # Small delay to let tasks pile up in queue
    await asyncio.sleep(0.1)

    results = await asyncio.gather(*tasks)

    # Count QueueFullError exceptions
    queue_full_errors = sum(1 for r in results if isinstance(r, QueueFullError))

    # With 10 requests and queue limit of 3, expect at least 5 rejections
    assert queue_full_errors >= 5, f"Expected at least 5 QueueFullError, got {queue_full_errors}"

    # Some requests should succeed
    successful = sum(1 for r in results if isinstance(r, str) and r.startswith("success"))
    assert successful >= 3, f"Expected at least 3 successful requests, got {successful}"


@pytest.mark.asyncio
async def test_rollback_on_chunk_save_failure(
    ingestion_service_with_rate_limiter, mock_chunk_repo, mock_embedding_port
):
    """Test that chunks are rolled back if save_chunks fails.

    Scenario: Embedding succeeds but chunk persistence fails
    Expected: delete_chunks_by_document_id called for rollback
    """
    # Mock chunk_repo to fail on save
    mock_chunk_repo.save_chunks = AsyncMock(side_effect=Exception("Database write error"))

    mock_embedding_port.generate_embedding = AsyncMock(return_value=[0.1] * 768)

    file_bytes = b"Test content for rollback"

    with pytest.raises(Exception) as exc_info:
        await ingestion_service_with_rate_limiter.ingest_document(
            file_bytes=file_bytes, filename="rollback_test.txt", subject="general"
        )

    assert "Database write error" in str(exc_info.value)

    # Verify rollback was attempted
    assert mock_chunk_repo.delete_chunks_by_document_id.called


@pytest.mark.asyncio
async def test_rate_limiter_enforces_rpm_limit():
    """Test that RateLimiter enforces RPM limit correctly.

    Scenario: Make 16 requests with 15 RPM limit
    Expected: 16th request waits for token refill
    """
    rate_limiter = RateLimiter(requests_per_minute=15, max_queue_depth=20)

    # Track request timestamps
    timestamps = []

    async def make_request(idx):
        async with rate_limiter.acquire(request_id=f"req_{idx}"):
            timestamps.append(asyncio.get_event_loop().time())

    # Make 16 requests rapidly
    tasks = [make_request(i) for i in range(16)]
    await asyncio.gather(*tasks)

    # Verify 16 requests completed
    assert len(timestamps) == 16

    # Check that requests were throttled
    # With 15 RPM, we can process 15 requests immediately,
    # but the 16th must wait for token refill (4 seconds minimum)
    first_batch = timestamps[:15]
    last_request = timestamps[15]

    # All first 15 should complete quickly (within 1 second)
    assert max(first_batch) - min(first_batch) < 1.0

    # 16th request should be delayed by at least token refill time
    # (15 RPM = 1 token per 4 seconds)
    delay = last_request - min(first_batch)
    assert delay >= 3.5  # Allow some slack for timing variance

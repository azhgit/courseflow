"""Unit tests for Document content hash computation.

Tests the SHA-256 hashing algorithm used for duplicate detection.
"""

from courseflow.domain.models import IngestionDocument


def test_compute_content_hash_returns_sha256():
    """Test that compute_content_hash returns valid SHA-256 hex digest."""
    text = "Sample educational content about biology."
    hash_result = IngestionDocument.compute_content_hash(text)

    # SHA-256 produces 64-character hex string
    assert len(hash_result) == 64
    assert all(c in "0123456789abcdef" for c in hash_result)


def test_compute_content_hash_normalizes_whitespace():
    """Test that leading/trailing whitespace is normalized before hashing."""
    text1 = "Sample content"
    text2 = "  Sample content  "
    text3 = "\n\nSample content\n\n"

    hash1 = IngestionDocument.compute_content_hash(text1)
    hash2 = IngestionDocument.compute_content_hash(text2)
    hash3 = IngestionDocument.compute_content_hash(text3)

    # All should produce the same hash after normalization
    assert hash1 == hash2 == hash3


def test_compute_content_hash_normalizes_line_endings():
    """Test that different line endings produce same hash."""
    text_unix = "Line 1\nLine 2\nLine 3"
    text_windows = "Line 1\r\nLine 2\r\nLine 3"
    text_mac = "Line 1\rLine 2\rLine 3"

    hash_unix = IngestionDocument.compute_content_hash(text_unix)
    hash_windows = IngestionDocument.compute_content_hash(text_windows)
    hash_mac = IngestionDocument.compute_content_hash(text_mac)

    # All should normalize to the same hash
    assert hash_unix == hash_windows == hash_mac


def test_compute_content_hash_different_content_different_hash():
    """Test that different content produces different hashes."""
    text1 = "Biology content about cells"
    text2 = "Programming content about Python"

    hash1 = IngestionDocument.compute_content_hash(text1)
    hash2 = IngestionDocument.compute_content_hash(text2)

    assert hash1 != hash2


def test_compute_content_hash_is_deterministic():
    """Test that same content always produces same hash."""
    text = "Deterministic test content"

    hash1 = IngestionDocument.compute_content_hash(text)
    hash2 = IngestionDocument.compute_content_hash(text)
    hash3 = IngestionDocument.compute_content_hash(text)

    assert hash1 == hash2 == hash3


def test_compute_content_hash_empty_string():
    """Test hash computation for empty string."""
    hash_result = IngestionDocument.compute_content_hash("")

    # Should return valid SHA-256 hash even for empty string
    assert len(hash_result) == 64
    # Hash of empty string is consistent
    assert hash_result == IngestionDocument.compute_content_hash("")


def test_compute_content_hash_unicode_content():
    """Test hash computation with unicode characters."""
    text = "Unicode content: café, naïve, 日本語, 🎓"
    hash_result = IngestionDocument.compute_content_hash(text)

    assert len(hash_result) == 64
    # Same unicode content should hash consistently
    assert hash_result == IngestionDocument.compute_content_hash(text)


def test_document_is_duplicate_method():
    """Test Document.is_duplicate() comparison logic."""
    # Valid SHA-256 hash (64 characters)
    hash1 = "a" * 64
    hash2 = "b" * 64

    doc1 = IngestionDocument(
        filename="test1.md",
        subject="biology",
        content_hash=hash1,
        file_format="markdown",
        file_size_bytes=1000,
        chunks_created=5,
        ingestion_time_ms=500,
    )

    # Same hash = duplicate
    assert doc1.is_duplicate(hash1) is True

    # Different hash = not duplicate
    assert doc1.is_duplicate(hash2) is False

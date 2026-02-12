"""Unit tests for Chunk validation logic."""

import pytest
from pydantic import ValidationError

from courseflow.domain.models import Chunk


def test_chunk_creation_with_valid_data():
    """Test that valid chunk data creates a Chunk instance."""
    chunk = Chunk(
        text="Sample chunk text.",
        document_id="doc-123",
        chunk_index=0,
        token_count=50,
        subject="biology",
        source_filename="test.md",
    )

    assert chunk.text == "Sample chunk text."
    assert chunk.document_id == "doc-123"
    assert chunk.chunk_index == 0
    assert chunk.token_count == 50


def test_chunk_requires_non_empty_text():
    """Test that empty text fails validation."""
    with pytest.raises(ValidationError):
        Chunk(
            text="",  # Empty text should fail
            document_id="doc-123",
            chunk_index=0,
            token_count=50,
            subject="biology",
            source_filename="test.md",
        )


def test_chunk_negative_token_count_fails():
    """Test that negative token count fails validation."""
    with pytest.raises(ValidationError):
        Chunk(
            text="Sample text",
            document_id="doc-123",
            chunk_index=0,
            token_count=-10,  # Negative should fail
            subject="biology",
            source_filename="test.md",
        )


def test_chunk_with_embedding():
    """Test chunk creation with embedding vector."""
    embedding = [0.1, 0.2, 0.3] * 256  # 768-dimensional
    chunk = Chunk(
        text="Sample text",
        document_id="doc-123",
        chunk_index=0,
        token_count=50,
        subject="biology",
        source_filename="test.md",
        embedding=embedding,
    )

    assert chunk.embedding == embedding
    assert len(chunk.embedding) == 768

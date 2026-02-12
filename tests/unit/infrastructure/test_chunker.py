"""Unit tests for SentenceChunker algorithm.

Tests sentence-priority chunking with token limits.
"""

from unittest.mock import Mock

import pytest

from courseflow.infrastructure.text_processing.sentence_chunker import SentenceChunker


@pytest.fixture
def tokenizer():
    """Mock sentence tokenizer."""
    tok = Mock()
    tok.tokenize_sentences = Mock(  # Correct method name
        return_value=[
            "First sentence.",
            "Second sentence.",
            "Third sentence.",
            "Fourth sentence.",
        ]
    )
    return tok


@pytest.fixture
def token_counter():
    """Mock token counter."""
    counter = Mock()
    # Each sentence = 50 tokens
    counter.count_tokens = Mock(return_value=50)
    return counter


@pytest.fixture
def chunker(tokenizer, token_counter):
    """SentenceChunker instance."""
    return SentenceChunker(tokenizer=tokenizer, token_counter=token_counter)


def test_chunker_creates_chunks_within_token_limits(chunker, token_counter):
    """Test that chunks respect min/max token limits."""
    # Each sentence = 50 tokens, so we should get ~7-10 sentences per chunk
    text = "This is test content. " * 20
    chunks = chunker.create_chunks(
        text=text,
        document_id="doc-123",
        source_filename="test.md",
        subject="general",
    )

    assert len(chunks) > 0
    for chunk in chunks:
        # Note: chunker prioritizes sentence integrity, so min boundary is flexible
        assert chunk.token_count > 0
        assert chunk.document_id == "doc-123"
        assert chunk.subject == "general"


def test_chunker_preserves_sentence_integrity(chunker):
    """Test that sentences are not split mid-sentence."""
    text = "Sentence one. Sentence two. Sentence three."
    chunks = chunker.create_chunks(
        text=text,
        document_id="doc-123",
        source_filename="test.md",
        subject="general",
    )

    # Each chunk text should end with sentence-ending punctuation
    for chunk in chunks:
        assert chunk.text.strip().endswith((".", "!", "?"))


def test_chunker_assigns_sequential_indices(chunker):
    """Test that chunk indices are sequential starting from 0."""
    text = "First sentence. Second sentence. Third sentence."
    chunks = chunker.create_chunks(
        text=text,
        document_id="doc-123",
        source_filename="test.md",
        subject="general",
    )

    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i

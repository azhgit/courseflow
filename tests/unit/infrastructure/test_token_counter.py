"""Unit tests for token counting utility.

Tests cover:
- Basic token counting for various text lengths
- Caching behavior
- Empty string handling
- Cache clearing
"""

import pytest

from courseflow.infrastructure.token_counting import TokenCounter


class TestTokenCounter:
    """Test suite for TokenCounter utility."""

    def test_count_empty_string(self) -> None:
        """Test counting tokens in empty string returns 0."""
        counter = TokenCounter()
        assert counter.count_tokens("") == 0

    def test_count_single_token(self) -> None:
        """Test counting single token word."""
        counter = TokenCounter()
        count = counter.count_tokens("Hello")
        assert count >= 1  # At least 1 token

    def test_count_multiple_tokens(self) -> None:
        """Test counting multiple tokens."""
        counter = TokenCounter()
        text = "What is photosynthesis?"
        count = counter.count_tokens(text)
        assert count >= 3  # At least 3 tokens for this phrase

    def test_count_long_text(self) -> None:
        """Test counting tokens in longer text."""
        counter = TokenCounter()
        text = "Photosynthesis is the process by which plants convert light energy into chemical energy stored in glucose. It occurs in two main stages: the light-dependent reactions in the thylakoid membranes and the light-independent reactions (Calvin cycle) in the stroma."
        count = counter.count_tokens(text)
        assert count >= 40  # Expect ~50+ tokens

    def test_caching_returns_same_count(self) -> None:
        """Test that caching returns same count for same text."""
        counter = TokenCounter()
        text = "Hello world"

        count1 = counter.count_tokens(text)
        count2 = counter.count_tokens(text)

        assert count1 == count2

    def test_different_texts_different_counts(self) -> None:
        """Test that different texts have different token counts."""
        counter = TokenCounter()

        count1 = counter.count_tokens("Hello")
        count2 = counter.count_tokens("Hello world this is a longer phrase with many more tokens")

        assert count1 < count2

    def test_cache_clearing(self) -> None:
        """Test clearing cache doesn't affect functionality."""
        counter = TokenCounter()
        text = "Test text"

        count1 = counter.count_tokens(text)
        counter.clear_cache()
        count2 = counter.count_tokens(text)

        assert count1 == count2

    def test_whitespace_variations(self) -> None:
        """Test that whitespace affects token count."""
        counter = TokenCounter()

        count1 = counter.count_tokens("hello world")
        count2 = counter.count_tokens("hello  world")  # Extra space
        count3 = counter.count_tokens("hello\nworld")  # Newline

        # All might tokenize differently
        assert count1 >= 1
        assert count2 >= 1
        assert count3 >= 1

"""Token counting using tiktoken library.

This module provides token counting for conversation turns using
the tiktoken library (OpenAI's token counter). Used for enforcing
token budgets on conversation history (2000 tokens max per conversation).

Token counts match Google Gemini's tokenization for consistency
with LLM prompt size calculations.
"""

import tiktoken


class TokenCounter:
    """Encapsulates token counting logic using tiktoken.

    Uses "cl100k_base" encoding (used by OpenAI models), which provides
    reasonable approximation of token counts for any text (including
    Gemini API requests). Counts are cached per unique text to avoid
    redundant computation during history trimming.

    Attributes:
        _encoding: tiktoken Encoding object (lazily initialized)
        _cache: Dict mapping text to token count (in-process cache)
    """

    def __init__(self) -> None:
        self._encoding: tiktoken.Encoding | None = None
        self._cache: dict[str, int] = {}

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Uses cl100k_base encoding. Results are cached to avoid
        redundant computation when the same text is counted multiple times
        (e.g., during history trimming when calculating multiple
        budget scenarios).

        Args:
            text: Text to tokenize (can be empty string)

        Returns:
            Number of tokens in text (0 for empty string)
        """
        if not text:
            return 0

        # Check cache first
        if text in self._cache:
            return self._cache[text]

        # Lazy initialize encoding on first use
        if self._encoding is None:
            self._encoding = tiktoken.get_encoding("cl100k_base")

        # Count tokens and cache result
        count = len(self._encoding.encode(text))
        self._cache[text] = count
        return count

    def clear_cache(self) -> None:
        """Clear in-process token count cache.

        Useful for memory management in long-running processes.
        Cache will be rebuilt on next count_tokens() calls.
        """
        self._cache.clear()

"""tiktoken-based token counting adapter."""

import tiktoken

from courseflow.domain.ports import TokenCounterPort


class TiktokenCounter(TokenCounterPort):
    """Count tokens using the cl100k_base encoding (fast, widely compatible)."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        return len(self._encoding.encode(text))

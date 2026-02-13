"""NLTK-based sentence tokenizer adapter."""

from __future__ import annotations

import re

from nltk.tokenize import sent_tokenize  # type: ignore[import-untyped]

from courseflow.domain.ports import SentenceTokenizerPort


class NLTKSentenceTokenizer(SentenceTokenizerPort):
    """Split text into sentences using NLTK punkt models."""

    def tokenize_sentences(self, text: str) -> list[str]:
        # Fallback keeps ingestion working in minimal CI/runtime environments.
        try:
            return [s for s in sent_tokenize(text) if s.strip()]
        except LookupError:
            return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

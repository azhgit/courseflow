"""NLTK-based sentence tokenizer adapter."""

from __future__ import annotations

from nltk.tokenize import sent_tokenize  # type: ignore[import-untyped]

from courseflow.domain.ports import SentenceTokenizerPort


class NLTKSentenceTokenizer(SentenceTokenizerPort):
    """Split text into sentences using NLTK punkt models."""

    def tokenize_sentences(self, text: str) -> list[str]:
        # NLTK raises LookupError if punkt data is missing.
        return [s for s in sent_tokenize(text) if s.strip()]

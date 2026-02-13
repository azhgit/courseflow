"""Sentence-priority semantic chunker implementation."""

from __future__ import annotations

from courseflow.domain.models import Chunk
from courseflow.domain.ports import ChunkerPort, SentenceTokenizerPort, TokenCounterPort


class SentenceChunker(ChunkerPort):
    """Chunk text by packing whole sentences up to a soft token budget.

    Sentence integrity is strict: we never split mid-sentence.
    Token targets are soft: chunks may exceed target_max_tokens when needed.
    """

    def __init__(self, tokenizer: SentenceTokenizerPort, token_counter: TokenCounterPort):
        self._tokenizer = tokenizer
        self._token_counter = token_counter

    def create_chunks(
        self,
        text: str,
        document_id: str,
        source_filename: str,
        subject: str,
        target_min_tokens: int = 300,
        target_max_tokens: int = 500,
    ) -> list[Chunk]:
        sentences = self._tokenizer.tokenize_sentences(text)
        if not sentences:
            return []

        chunks: list[Chunk] = []
        current_sentences: list[str] = []
        current_tokens = 0

        def flush() -> None:
            nonlocal current_sentences, current_tokens
            if not current_sentences:
                return
            chunk_text = " ".join(s.strip() for s in current_sentences).strip()
            token_count = self._token_counter.count_tokens(chunk_text)
            chunks.append(
                Chunk(
                    document_id=document_id,
                    chunk_index=len(chunks),
                    text=chunk_text,
                    token_count=token_count,
                    source_filename=source_filename,
                    subject=subject,
                )
            )
            current_sentences = []
            current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_tokens = self._token_counter.count_tokens(sentence)

            # Very long single sentence: it becomes its own chunk.
            if sentence_tokens > target_max_tokens:
                flush()
                chunks.append(
                    Chunk(
                        document_id=document_id,
                        chunk_index=len(chunks),
                        text=sentence,
                        token_count=sentence_tokens,
                        source_filename=source_filename,
                        subject=subject,
                    )
                )
                continue

            if not current_sentences:
                current_sentences.append(sentence)
                current_tokens = sentence_tokens
                continue

            proposed = current_tokens + sentence_tokens
            if proposed <= target_max_tokens:
                current_sentences.append(sentence)
                current_tokens = proposed
                continue

            # Would exceed max: if we're still under min, accept overflow to avoid tiny chunks.
            if current_tokens < target_min_tokens:
                current_sentences.append(sentence)
                current_tokens = proposed
                continue

            flush()
            current_sentences.append(sentence)
            current_tokens = sentence_tokens

        flush()
        return chunks

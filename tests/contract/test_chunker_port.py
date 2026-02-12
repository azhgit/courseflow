"""Contract test for ChunkerPort implementations (T073)."""

from __future__ import annotations

from courseflow.domain.ports import ChunkerPort
from courseflow.infrastructure.text_processing.nltk_tokenizer import NLTKSentenceTokenizer
from courseflow.infrastructure.text_processing.sentence_chunker import SentenceChunker
from courseflow.infrastructure.token_counting.tiktoken_counter import TiktokenCounter


def _assert_chunker_contract(chunker: ChunkerPort) -> None:
    assert hasattr(chunker, "create_chunks")
    assert callable(chunker.create_chunks)


def test_sentence_chunker_implements_chunker_port_contract():
    chunker = SentenceChunker(
        tokenizer=NLTKSentenceTokenizer(),
        token_counter=TiktokenCounter(),
    )
    _assert_chunker_contract(chunker)
    chunks = chunker.create_chunks(
        text="Sentence one. Sentence two. Sentence three.",
        document_id="doc-1",
        source_filename="sample.txt",
        subject="general",
    )
    assert chunks
    assert all(c.subject == "general" for c in chunks)


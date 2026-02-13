"""Integration tests for subject organization (US3)."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from courseflow.api.main import create_app
from courseflow.application.ingestion_service import IngestionService
from courseflow.infrastructure.document_processing.pymupdf_extractor import PyMuPDFExtractor
from courseflow.infrastructure.repositories.chunk_repo import SQLiteChromaChunkRepository
from courseflow.infrastructure.repositories.document_repo import SQLiteDocumentRepository
from courseflow.infrastructure.repositories.subject_repo import SQLiteSubjectRepository
from courseflow.infrastructure.text_processing.nltk_tokenizer import NLTKSentenceTokenizer
from courseflow.infrastructure.text_processing.sentence_chunker import SentenceChunker
from courseflow.infrastructure.token_counting.tiktoken_counter import TiktokenCounter


class _StubEmbeddingClient:
    async def generate_embedding(self, text: str, timeout: int = 10) -> list[float]:
        del text, timeout
        return [0.01] * 768


@pytest.fixture(scope="function")
def temp_dirs():
    chroma_dir = tempfile.mkdtemp()
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "test_subjects.db")
    yield chroma_dir, db_path
    shutil.rmtree(chroma_dir, ignore_errors=True)
    shutil.rmtree(db_dir, ignore_errors=True)


@pytest.fixture
def ingestion_context(
    temp_dirs,
) -> tuple[
    IngestionService,
    SQLiteDocumentRepository,
    SQLiteChromaChunkRepository,
]:
    chroma_dir, db_path = temp_dirs
    migration_path = (
        Path(__file__).parent.parent.parent
        / "scripts"
        / "migrations"
        / "002_add_ingestion_tables.sql"
    )
    conn = sqlite3.connect(db_path)
    conn.executescript(migration_path.read_text(encoding="utf-8"))
    conn.close()

    tokenizer = NLTKSentenceTokenizer()
    counter = TiktokenCounter()
    document_repo = SQLiteDocumentRepository(db_path=db_path)
    chunk_repo = SQLiteChromaChunkRepository(db_path=db_path, chroma_persist_dir=chroma_dir)
    service = IngestionService(
        pdf_extractor=PyMuPDFExtractor(),
        token_counter=counter,
        sentence_tokenizer=tokenizer,
        chunker=SentenceChunker(tokenizer=tokenizer, token_counter=counter),
        embedding_port=_StubEmbeddingClient(),
        subject_repo=SQLiteSubjectRepository(db_path=db_path),
        document_repo=document_repo,
        chunk_repo=chunk_repo,
    )
    return service, document_repo, chunk_repo


@pytest.mark.asyncio
async def test_subject_tagging_during_ingestion(
    ingestion_context: tuple[
        IngestionService, SQLiteDocumentRepository, SQLiteChromaChunkRepository
    ],
):
    """T049: chunks and document should keep the ingestion subject tag."""
    content = (
        "Photosynthesis converts light energy into chemical energy. "
        "Chlorophyll absorbs sunlight in chloroplasts."
    )
    ingestion_service, document_repo, chunk_repo = ingestion_context
    result = await ingestion_service.ingest_document(
        file_bytes=content.encode("utf-8"),
        filename="bio.md",
        subject="biology",
    )
    assert result.success is True
    assert result.skipped is False

    # Validate persistence carries the same subject.
    doc = await document_repo.find_by_id(result.document_id)
    assert doc is not None
    assert doc.subject == "biology"
    chunks = await chunk_repo.find_chunks_by_document_id(result.document_id)
    assert chunks
    assert all(c.subject == "biology" for c in chunks)


def test_subject_filtered_query_calls_rag_with_subject():
    """T050: query endpoint should pass subject filter through to RAG service."""
    app = create_app()
    mock_rag = AsyncMock()

    from courseflow.api.dependencies import get_rag_service
    from courseflow.domain.models import (
        Answer,
        Document,
        DocumentMetadata,
        Query,
        SearchResult,
        TokenUsage,
    )

    answer = Answer(
        query_id=Query(text="x").id,
        answer_text="ok",
        sources=[
            SearchResult(
                document=Document(
                    id="d1",
                    content="A" * 120,
                    metadata=DocumentMetadata(source="s.md", subject="biology", chunk_index=0),
                ),
                similarity_score=0.9,
            )
        ],
        latency_ms=1,
        token_usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )
    mock_rag.answer_query.return_value = answer
    app.dependency_overrides[get_rag_service] = lambda: mock_rag
    client = TestClient(app)

    resp = client.post(
        "/api/v1/query", json={"query": "What is photosynthesis?", "subject": "biology"}
    )
    assert resp.status_code == 200
    mock_rag.answer_query.assert_awaited()
    _, kwargs = mock_rag.answer_query.await_args
    assert kwargs.get("subject") == "biology"


def test_default_subject_in_ingest_metadata():
    """T051: missing subject should default to general."""
    from courseflow.api.routes.ingest import IngestMetadata

    meta = IngestMetadata.model_validate_json("{}")
    assert meta.subject == "general"

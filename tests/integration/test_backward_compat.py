"""Backward compatibility tests for non-streaming query endpoint (T033)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from courseflow.api.main import create_app
from courseflow.domain.models import Answer, Document, DocumentMetadata, SearchResult


def test_non_streaming_query_contract_unchanged() -> None:
    """POST /api/v1/query should keep stable response structure."""
    app = create_app()
    mock_rag = AsyncMock()

    from courseflow.api.dependencies import get_rag_service

    app.dependency_overrides[get_rag_service] = lambda: mock_rag
    client = TestClient(app)

    doc = Document(
        id="doc-1",
        content=(
            "Photosynthesis is the process by which plants convert light energy into "
            "chemical energy, storing it as glucose and releasing oxygen as a byproduct."
        ),
        metadata=DocumentMetadata(
            source="photosynthesis.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        ),
    )
    mock_rag.answer_query.return_value = Answer(
        query_id=uuid4(),
        answer_text="Photosynthesis converts light energy into chemical energy.",
        sources=[SearchResult(document=doc, similarity_score=0.84)],
        latency_ms=123,
    )

    response = client.post("/api/v1/query", json={"query": "What is photosynthesis?"})
    assert response.status_code == 200
    body = response.json()
    assert "data" in body and "metadata" in body
    assert {"query_id", "answer", "sources", "conversation_id"} <= set(body["data"].keys())
    assert {"latency_ms", "timestamp"} <= set(body["metadata"].keys())

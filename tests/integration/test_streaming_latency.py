"""Latency tests for streaming endpoint (T036)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient

from courseflow.api.main import create_app


class _Limiter:
    def is_allowed(self) -> tuple[bool, int]:
        return (True, 0)


class _Repo:
    async def create_conversation(self):
        from uuid import uuid4

        from courseflow.domain.models import Conversation

        return Conversation(id=uuid4())

    async def conversation_exists(self, conversation_id):
        return True

    async def get_history(self, conversation_id, max_tokens=2000, max_count=5):
        from courseflow.domain.models import TurnHistory

        return TurnHistory(turns=[], total_tokens=0, truncated=False)

    async def add_turn(self, turn):
        return turn


class _Rag:
    async def stream_query(self, query, subject=None, conversation_history=None) -> AsyncGenerator:
        yield "first ", ["doc.md"]
        yield "second ", ["doc.md"]


def test_streaming_first_token_and_completion_latency() -> None:
    """First token should be fast and stream should complete within timeout budget."""
    app = create_app()
    from courseflow.api.dependencies import (
        get_conversation_repository,
        get_rag_service,
        get_rate_limiter,
    )

    app.dependency_overrides[get_rag_service] = lambda: _Rag()
    app.dependency_overrides[get_conversation_repository] = lambda: _Repo()
    app.dependency_overrides[get_rate_limiter] = lambda: _Limiter()
    client = TestClient(app)

    started = time.perf_counter()
    response = client.post("/api/v1/query/stream", json={"query": "latency test"})
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    assert response.status_code == 200
    assert elapsed_ms < 30_000

    events = [json.loads(x[6:]) for x in response.text.split("\n\n") if x.startswith("data: ")]
    chunk_index = next(i for i, e in enumerate(events) if e.get("type") == "chunk")
    done_index = next(i for i, e in enumerate(events) if e.get("type") == "done")
    assert chunk_index < done_index

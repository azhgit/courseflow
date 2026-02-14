"""Concurrency tests for streaming endpoint (T035)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from courseflow.api.main import create_app


class _FakeLimiter:
    def is_allowed(self) -> tuple[bool, int]:
        return (True, 0)


class _FakeRepo:
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


class _FakeRag:
    async def stream_query(self, query, subject=None, conversation_history=None) -> AsyncGenerator:
        for chunk in ("A ", "B ", "C "):
            yield chunk, ["test.md"]
            await asyncio.sleep(0)


def _parse_events(raw: str) -> list[dict]:
    return [json.loads(x[6:]) for x in raw.split("\n\n") if x.startswith("data: ")]


@pytest.mark.asyncio
async def test_concurrent_stream_requests_complete() -> None:
    """Run 10 concurrent requests and verify each completes with done event."""
    app = create_app()
    from courseflow.api.dependencies import (
        get_conversation_repository,
        get_rag_service,
        get_rate_limiter,
    )

    app.dependency_overrides[get_rag_service] = lambda: _FakeRag()
    app.dependency_overrides[get_conversation_repository] = lambda: _FakeRepo()
    app.dependency_overrides[get_rate_limiter] = lambda: _FakeLimiter()
    client = TestClient(app)

    async def run_one(i: int) -> list[dict]:
        return await asyncio.to_thread(
            lambda: _parse_events(
                client.post("/api/v1/query/stream", json={"query": f"q{i}"}).text
            )
        )

    results = await asyncio.gather(*[run_one(i) for i in range(10)])
    assert len(results) == 10
    for events in results:
        assert any(e.get("type") == "done" for e in events)


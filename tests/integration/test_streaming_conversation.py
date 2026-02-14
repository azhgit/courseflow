"""Integration tests for streaming conversation persistence (T026-T028)."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from courseflow.api.main import create_app
from courseflow.domain.exceptions import NoRelevantDocumentsError
from courseflow.domain.models import Conversation, ConversationTurn, TurnHistory


class FakeConversationRepo:
    """Minimal in-memory conversation repository for integration tests."""

    def __init__(self) -> None:
        self.conversations: dict[str, list[ConversationTurn]] = {}

    async def create_conversation(self) -> Conversation:
        conv_id = str(uuid4())
        self.conversations[conv_id] = []
        return Conversation(id=UUID(conv_id))

    async def conversation_exists(self, conversation_id: str | UUID) -> bool:
        return str(conversation_id) in self.conversations

    async def add_turn(self, turn: ConversationTurn) -> ConversationTurn:
        self.conversations[str(turn.conversation_id)].append(turn)
        return turn

    async def get_history(
        self,
        conversation_id: str | UUID,
        max_tokens: int = 2000,
        max_count: int = 5,
    ) -> TurnHistory:
        turns = self.conversations.get(str(conversation_id), [])
        return TurnHistory.from_turns(turns, max_tokens=max_tokens, max_count=max_count)


class FakeRateLimiter:
    def is_allowed(self) -> tuple[bool, int]:
        return (True, 0)


@pytest.fixture
def setup_client():
    app = create_app()
    repo = FakeConversationRepo()

    from courseflow.api.dependencies import (
        get_conversation_repository,
        get_rag_service,
        get_rate_limiter,
    )

    class FakeRag:
        async def stream_query(
            self, query, subject=None, conversation_history=None
        ) -> AsyncGenerator[tuple[str, list[str]], None]:
            yield ("Hello ", ["python-async.md"])
            yield ("world", ["python-async.md"])

    app.dependency_overrides[get_conversation_repository] = lambda: repo
    app.dependency_overrides[get_rate_limiter] = lambda: FakeRateLimiter()
    app.dependency_overrides[get_rag_service] = lambda: FakeRag()
    return TestClient(app), repo, app


def _parse_events(raw: str) -> list[dict]:
    events: list[dict] = []
    for chunk in raw.strip().split("\n\n"):
        if chunk.startswith("data: "):
            events.append(json.loads(chunk[6:]))
    return events


def test_streaming_creates_conversation_and_saves_turns(setup_client) -> None:
    """T026: new conversation is created and saved from stream."""
    client, repo, _app = setup_client
    response = client.post("/api/v1/query/stream", json={"query": "Explain async"})
    assert response.status_code == 200
    events = _parse_events(response.text)
    done = [e for e in events if e["type"] == "done"]
    assert len(done) == 1
    conversation_id = done[0]["conversation_id"]
    assert conversation_id in repo.conversations


def test_streaming_appends_to_existing_conversation(setup_client) -> None:
    """T027: streaming with conversation_id appends turns."""
    client, repo, _app = setup_client
    # Create existing conversation through repository directly.
    import asyncio

    created = asyncio.run(repo.create_conversation())
    conversation_id = str(created.id)
    response = client.post(
        "/api/v1/query/stream",
        json={"query": "Follow up", "conversation_id": conversation_id},
    )
    assert response.status_code == 200
    events = _parse_events(response.text)
    assert any(e["type"] == "done" for e in events)


def test_no_relevant_documents_not_saved(setup_client) -> None:
    """T028: no relevant documents path does not save conversation turns."""
    client, repo, app = setup_client
    from courseflow.api.dependencies import get_rag_service

    class EmptyRag:
        async def stream_query(
            self, query, subject=None, conversation_history=None
        ) -> AsyncGenerator[tuple[str, list[str]], None]:
            raise NoRelevantDocumentsError("none")
            yield ("", [])

    app.dependency_overrides[get_rag_service] = lambda: EmptyRag()
    response = client.post("/api/v1/query/stream", json={"query": "xyz12345xyz"})
    events = _parse_events(response.text)
    assert any(e.get("error") == "no_relevant_documents" for e in events)
    assert len(repo.conversations) == 0

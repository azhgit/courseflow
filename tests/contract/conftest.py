"""Shared fixtures for contract tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from courseflow.api.main import create_app
from courseflow.domain.exceptions import NoRelevantDocumentsError
from courseflow.domain.models import Conversation, TurnHistory


class _FakeRateLimiter:
    def is_allowed(self) -> tuple[bool, int]:
        return (True, 0)


class _FakeConversationRepo:
    async def create_conversation(self) -> Conversation:
        from uuid import uuid4

        return Conversation(id=uuid4())

    async def conversation_exists(self, conversation_id):
        return True

    async def get_history(self, conversation_id, max_tokens=2000, max_count=5):
        return TurnHistory(turns=[], total_tokens=0, truncated=False)

    async def add_turn(self, turn):
        return turn


class _FakeRag:
    async def stream_query(self, query, subject=None, conversation_history=None):
        if "xyzabc123notarealquery" in query.text:
            raise NoRelevantDocumentsError("none")
        yield ("chunk one ", ["test.md"])
        yield ("chunk two", ["test.md"])


@pytest.fixture
async def client() -> AsyncClient:
    """Async client fixture for contract endpoint tests."""
    app = create_app()
    from courseflow.api.dependencies import (
        get_conversation_repository,
        get_rag_service,
        get_rate_limiter,
    )

    app.dependency_overrides[get_rag_service] = lambda: _FakeRag()
    app.dependency_overrides[get_rate_limiter] = lambda: _FakeRateLimiter()
    app.dependency_overrides[get_conversation_repository] = lambda: _FakeConversationRepo()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

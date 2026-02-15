"""Integration tests for /metrics and /health endpoints."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from courseflow.api.dependencies import get_query_repository, get_rate_limiter, get_vector_store
from courseflow.api.main import create_app
from courseflow.config import settings
from courseflow.domain.models import RateLimitTracker, TokenUsage
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository


class _FakeCollection:
    def count(self) -> int:
        return 42


class _FakeVectorStore:
    def __init__(self) -> None:
        self.collection = _FakeCollection()


def _build_rate_limiter(full: bool = False) -> RateLimitTracker:
    max_rpm = 15
    timestamps = deque(maxlen=max_rpm)
    if full:
        now = datetime.now(UTC)
        for _ in range(max_rpm):
            timestamps.append(now)
    return RateLimitTracker(
        request_timestamps=timestamps,
        max_requests_per_minute=max_rpm,
        max_requests_per_day=1500,
    )


def _seed_queries(repo: SQLiteQueryRepository, count: int = 10) -> None:
    async def _seed() -> None:
        await repo.initialize()
        for idx in range(count):
            await repo.save_query(
                query_id=f"q-{idx}",
                query_text=f"question {idx}",
                answer_text="answer",
                latency_ms=100 + idx,
                token_usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )

    asyncio.run(_seed())


def test_metrics_endpoint_accumulates_queries(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "EVAL_SCHEDULE_ENABLED", False)
    repo = SQLiteQueryRepository(db_path=str(tmp_path / "queries.db"))
    _seed_queries(repo, count=10)

    app = create_app()
    app.dependency_overrides[get_query_repository] = lambda: repo
    app.dependency_overrides[get_rate_limiter] = lambda: _build_rate_limiter(full=False)

    with TestClient(app) as client:
        response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["queries"]["total"] == 10
    assert payload["data"]["latency"]["p95_ms"] >= payload["data"]["latency"]["p50_ms"]
    assert payload["data"]["tokens"]["consumed_total"] == 150


def test_health_endpoint_fast_and_healthy(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "EVAL_SCHEDULE_ENABLED", False)
    repo = SQLiteQueryRepository(db_path=str(tmp_path / "queries.db"))
    _seed_queries(repo, count=1)

    app = create_app()
    app.dependency_overrides[get_query_repository] = lambda: repo
    app.dependency_overrides[get_vector_store] = lambda: _FakeVectorStore()
    app.dependency_overrides[get_rate_limiter] = lambda: _build_rate_limiter(full=False)

    with TestClient(app) as client:
        started = time.perf_counter()
        response = client.get("/api/v1/health")
        elapsed_ms = (time.perf_counter() - started) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 100
    payload = response.json()
    assert payload["data"]["status"] == "healthy"
    assert "gemini_api" in payload["data"]["components"]
    assert "chromadb" in payload["data"]["components"]
    assert "sqlite" in payload["data"]["components"]


def test_health_endpoint_returns_503_when_quota_exceeded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "EVAL_SCHEDULE_ENABLED", False)
    repo = SQLiteQueryRepository(db_path=str(tmp_path / "queries.db"))
    _seed_queries(repo, count=1)

    app = create_app()
    app.dependency_overrides[get_query_repository] = lambda: repo
    app.dependency_overrides[get_vector_store] = lambda: _FakeVectorStore()
    app.dependency_overrides[get_rate_limiter] = lambda: _build_rate_limiter(full=True)

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["success"] is False
    assert payload["data"]["status"] == "degraded"
    assert payload["data"]["components"]["gemini_api"]["status"] == "error"

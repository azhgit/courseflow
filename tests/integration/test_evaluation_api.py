"""Integration tests for evaluation API endpoints."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from statistics import quantiles
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from courseflow.api.dependencies import get_evaluation_service
from courseflow.api.main import create_app
from courseflow.application.evaluation_service import EvaluationService
from courseflow.config import settings
from courseflow.domain.eval_models import EvaluationRun, EvaluationStatus, Metrics
from courseflow.domain.models import Answer, Document, DocumentMetadata, Query, SearchResult
from courseflow.infrastructure.repositories.evaluation_repo import EvaluationRepository


class _FakeRagService:
    def __init__(self, dataset_path: Path, delay_seconds: float = 0.0):
        with dataset_path.open(encoding="utf-8") as file:
            pairs = json.load(file)["pairs"]
        self._pairs = {pair["question"]: pair for pair in pairs}
        self._delay_seconds = delay_seconds

    async def answer_query(self, query: Query, subject: str | None = None):  # noqa: ARG002
        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)

        pair = self._pairs[query.text]
        sources: list[SearchResult] = []
        for idx, chunk_id in enumerate(pair["expected_chunks"]):
            document = Document(
                id=chunk_id,
                content=("context " * 20).strip(),
                metadata=DocumentMetadata(
                    source="golden_dataset.md",
                    subject=pair.get("subject", "general"),
                    chunk_index=idx,
                    total_chunks=len(pair["expected_chunks"]),
                ),
            )
            sources.append(SearchResult(document=document, similarity_score=0.95))

        answer_text = f"{pair['expected_answer']} {' '.join(pair['keywords'])}"
        return Answer(query_id=query.id, answer_text=answer_text, sources=sources, latency_ms=5)


@pytest.fixture
def evaluation_context(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EVAL_SCHEDULE_ENABLED", False)

    db_path = tmp_path / "evaluations.db"
    repo = EvaluationRepository(db_path=db_path)
    asyncio.run(repo.initialize())

    service = EvaluationService(
        repository=repo,
        rag_service=_FakeRagService(Path(settings.eval_golden_dataset_path)),
        golden_dataset_path=settings.eval_golden_dataset_path,
    )

    app = create_app()
    app.dependency_overrides[get_evaluation_service] = lambda: service

    with TestClient(app) as client:
        yield client, repo


def _wait_for_completion(client: TestClient, run_id: str, timeout_seconds: float = 5.0) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get(f"/api/v1/eval/run/{run_id}")
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for evaluation completion")


def _seed_run(repo: EvaluationRepository, timestamp: datetime, status: EvaluationStatus, passed: bool) -> str:
    run = EvaluationRun(
        run_id=uuid4(),
        timestamp=timestamp,
        status=status,
        duration_ms=100,
        passed=passed,
        metrics=Metrics(
            retrieval_precision_avg=0.8,
            retrieval_precision_min=0.7,
            retrieval_precision_max=0.9,
            keyword_match_avg=0.85,
            keyword_match_min=0.75,
            keyword_match_max=0.95,
            latency_p50_ms=200,
            latency_p95_ms=400,
            latency_min_ms=120,
            latency_max_ms=500,
            pass_rate=0.8,
            tests_passed=12,
            tests_failed=3,
        ),
    )
    asyncio.run(repo.save_run(run, []))
    return str(run.run_id)


def test_post_eval_run_triggers_and_persists(evaluation_context) -> None:
    client, repo = evaluation_context

    response = client.post("/api/v1/eval/run")
    assert response.status_code == 202

    payload = response.json()
    run_id = payload["run_id"]
    assert payload["status"] == "running"

    completed = _wait_for_completion(client, run_id)
    assert completed["status"] == "completed"
    assert completed["metrics"] is not None

    persisted = asyncio.run(repo.get_run_by_id(UUID(run_id)))
    assert persisted is not None
    assert persisted.status == EvaluationStatus.COMPLETED


def test_post_eval_run_rejects_concurrent_with_429(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "EVAL_SCHEDULE_ENABLED", False)
    repo = EvaluationRepository(db_path=tmp_path / "evaluations.db")
    asyncio.run(repo.initialize())
    service = EvaluationService(
        repository=repo,
        rag_service=_FakeRagService(Path(settings.eval_golden_dataset_path), delay_seconds=0.05),
        golden_dataset_path=settings.eval_golden_dataset_path,
    )

    app = create_app()
    app.dependency_overrides[get_evaluation_service] = lambda: service

    with TestClient(app) as client:
        first = client.post("/api/v1/eval/run")
        assert first.status_code == 202

        second = client.post("/api/v1/eval/run")
        assert second.status_code == 429
        assert second.headers["retry-after"] == "300"


def test_get_eval_run_returns_completed_running_and_404(evaluation_context) -> None:
    client, _ = evaluation_context

    create_response = client.post("/api/v1/eval/run")
    run_id = create_response.json()["run_id"]

    running_response = client.get(f"/api/v1/eval/run/{run_id}")
    assert running_response.status_code == 200
    assert running_response.json()["status"] in {"running", "completed"}

    completed = _wait_for_completion(client, run_id)
    assert completed["metrics"] is not None

    missing = client.get(f"/api/v1/eval/run/{uuid4()}")
    assert missing.status_code == 404


def test_list_runs_supports_pagination_status_and_date_filters(evaluation_context) -> None:
    client, repo = evaluation_context
    now = datetime.utcnow()

    for idx in range(25):
        status = EvaluationStatus.COMPLETED if idx % 2 == 0 else EvaluationStatus.FAILED
        passed = idx % 3 == 0
        _seed_run(repo, now - timedelta(minutes=idx), status=status, passed=passed)

    paged = client.get("/api/v1/eval/run?page=1&page_size=20")
    assert paged.status_code == 200
    payload = paged.json()
    assert len(payload["runs"]) == 20
    assert payload["pagination"]["total"] >= 25
    assert payload["pagination"]["has_next"] is True

    filtered = client.get("/api/v1/eval/run?status=completed")
    assert filtered.status_code == 200
    assert all(run["status"] == "completed" for run in filtered.json()["runs"])

    since = (now - timedelta(minutes=10)).isoformat()
    until = now.isoformat()
    ranged = client.get(f"/api/v1/eval/run?since={since}&until={until}")
    assert ranged.status_code == 200
    assert len(ranged.json()["runs"]) > 0


def test_list_runs_performance_targets(evaluation_context) -> None:
    client, repo = evaluation_context
    now = datetime.utcnow()

    for idx in range(100):
        _seed_run(
            repo,
            timestamp=now - timedelta(seconds=idx),
            status=EvaluationStatus.COMPLETED,
            passed=True,
        )

    latencies = []
    for _ in range(20):
        start = time.perf_counter()
        response = client.get("/api/v1/eval/run?page=1&page_size=1")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        latencies.append(elapsed_ms)

    p95 = quantiles(latencies, n=100, method="inclusive")[94]
    assert p95 < 500

    start = time.perf_counter()
    all_runs = client.get("/api/v1/eval/run?page=1&page_size=100")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert all_runs.status_code == 200
    assert elapsed_ms < 2000


def test_get_baseline_uses_most_recent_passed_run(evaluation_context) -> None:
    client, repo = evaluation_context
    now = datetime.utcnow()

    none_response = client.get("/api/v1/eval/baseline")
    assert none_response.status_code == 200
    assert none_response.json() is None

    _seed_run(repo, now - timedelta(days=2), EvaluationStatus.COMPLETED, passed=True)
    _seed_run(repo, now - timedelta(days=1), EvaluationStatus.FAILED, passed=False)
    latest_passed_id = _seed_run(repo, now, EvaluationStatus.COMPLETED, passed=True)

    baseline = client.get("/api/v1/eval/baseline")
    assert baseline.status_code == 200
    assert baseline.json()["run_id"] == latest_passed_id

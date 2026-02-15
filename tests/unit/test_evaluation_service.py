"""Unit tests for evaluation service baseline comparison."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from courseflow.application.evaluation_service import EvaluationService
from courseflow.domain.eval_models import EvaluationRun, EvaluationStatus, Metrics


class _FakeRepo:
    def __init__(self, run: EvaluationRun | None, baseline: EvaluationRun | None):
        self._run = run
        self._baseline = baseline

    async def get_run_by_id(self, run_id, include_results: bool = False):  # noqa: ARG002
        return self._run

    async def get_baseline_run(self):
        return self._baseline


class _UnusedRag:
    pass


def _metrics(precision: float, keyword: float, latency_p95: float) -> Metrics:
    return Metrics(
        retrieval_precision_avg=precision,
        retrieval_precision_min=precision,
        retrieval_precision_max=precision,
        keyword_match_avg=keyword,
        keyword_match_min=keyword,
        keyword_match_max=keyword,
        latency_p50_ms=latency_p95 / 2,
        latency_p95_ms=latency_p95,
        latency_min_ms=int(latency_p95 / 3),
        latency_max_ms=int(latency_p95),
        pass_rate=0.8,
        tests_passed=12,
        tests_failed=3,
    )


@pytest.mark.asyncio
async def test_compare_to_baseline_returns_no_baseline_when_missing(tmp_path) -> None:
    run = EvaluationRun(metrics=_metrics(0.8, 0.85, 1200), status=EvaluationStatus.COMPLETED)
    service = EvaluationService(_FakeRepo(run, None), _UnusedRag(), tmp_path / "dataset.json")

    result = await service.compare_to_baseline(run.run_id)

    assert result["baseline_exists"] is False


@pytest.mark.asyncio
async def test_compare_to_baseline_detects_precision_regression(tmp_path) -> None:
    baseline = EvaluationRun(
        run_id=uuid4(),
        timestamp=datetime.utcnow() - timedelta(days=1),
        metrics=_metrics(0.9, 0.9, 1000),
        status=EvaluationStatus.COMPLETED,
        passed=True,
    )
    current = EvaluationRun(
        run_id=uuid4(),
        timestamp=datetime.utcnow(),
        metrics=_metrics(0.7, 0.9, 1000),
        status=EvaluationStatus.COMPLETED,
        passed=False,
    )

    service = EvaluationService(
        _FakeRepo(current, baseline), _UnusedRag(), tmp_path / "dataset.json"
    )
    result = await service.compare_to_baseline(current.run_id)

    assert result["baseline_exists"] is True
    assert result["comparisons"]["retrieval_precision"]["regressed"] is True
    assert result["overall_regression"] is True


@pytest.mark.asyncio
async def test_compare_to_baseline_detects_latency_regression(tmp_path) -> None:
    baseline = EvaluationRun(
        run_id=uuid4(),
        timestamp=datetime.utcnow() - timedelta(days=1),
        metrics=_metrics(0.8, 0.85, 1000),
        status=EvaluationStatus.COMPLETED,
        passed=True,
    )
    current = EvaluationRun(
        run_id=uuid4(),
        timestamp=datetime.utcnow(),
        metrics=_metrics(0.8, 0.85, 1300),
        status=EvaluationStatus.COMPLETED,
        passed=False,
    )

    service = EvaluationService(
        _FakeRepo(current, baseline), _UnusedRag(), tmp_path / "dataset.json"
    )
    result = await service.compare_to_baseline(current.run_id)

    assert result["comparisons"]["latency_p95"]["regressed"] is True
    assert result["overall_regression"] is True

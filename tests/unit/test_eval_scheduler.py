"""Unit tests for evaluation scheduler."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from courseflow.domain.exceptions import EvaluationInProgressException
from courseflow.infrastructure.scheduler.eval_scheduler import EvaluationScheduler


class _FakeEvalService:
    def __init__(self):
        self.trigger_evaluation = AsyncMock()


def test_scheduler_start_registers_daily_job(monkeypatch) -> None:
    service = _FakeEvalService()
    scheduler = EvaluationScheduler(service, enabled=True, hour=2, minute=0)

    calls = {"start": 0}

    original_add_job = scheduler.scheduler.add_job

    def _wrapped_add_job(*args, **kwargs):
        return original_add_job(*args, **kwargs)

    def _wrapped_start():
        calls["start"] += 1

    monkeypatch.setattr(scheduler.scheduler, "add_job", _wrapped_add_job)
    monkeypatch.setattr(scheduler.scheduler, "start", _wrapped_start)

    scheduler.start()

    jobs = scheduler.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "daily_evaluation"
    assert calls["start"] == 1


@pytest.mark.asyncio
async def test_scheduled_execution_calls_service() -> None:
    service = _FakeEvalService()
    scheduler = EvaluationScheduler(service, enabled=True, hour=2, minute=0)

    await scheduler._run_daily_evaluation()

    service.trigger_evaluation.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduled_execution_ignores_in_progress_error() -> None:
    service = _FakeEvalService()
    service.trigger_evaluation.side_effect = EvaluationInProgressException()
    scheduler = EvaluationScheduler(service, enabled=True, hour=2, minute=0)

    await scheduler._run_daily_evaluation()

    service.trigger_evaluation.assert_awaited_once()

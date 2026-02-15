"""Integration tests for scheduler startup/shutdown wiring."""

from __future__ import annotations

from fastapi.testclient import TestClient

from courseflow.api import dependencies
from courseflow.api.main import create_app
from courseflow.config import settings


class _FakeEvalService:
    async def trigger_evaluation(self):
        return None


def test_scheduler_initialization_and_shutdown(monkeypatch) -> None:
    monkeypatch.setattr(settings, "EVAL_SCHEDULE_ENABLED", True)
    monkeypatch.setattr(settings, "EVAL_SCHEDULE_HOUR", 2)
    monkeypatch.setattr(settings, "EVAL_SCHEDULE_MINUTE", 0)
    monkeypatch.setattr(dependencies, "_evaluation_service", _FakeEvalService())

    app = create_app()

    with TestClient(app):
        scheduler = app.state.eval_scheduler
        assert scheduler.scheduler.get_job("daily_evaluation") is not None

    assert scheduler.scheduler.running is False

"""Integration tests for SQLite retry behavior in evaluation repository."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import uuid4

import pytest

from courseflow.domain.eval_models import EvaluationRun, EvaluationStatus
from courseflow.domain.exceptions import EvaluationPersistenceError
from courseflow.infrastructure.repositories.evaluation_repo import EvaluationRepository


@pytest.mark.asyncio
async def test_save_run_retries_operational_error(monkeypatch, tmp_path) -> None:
    repo = EvaluationRepository(db_path=tmp_path / "eval.db")
    run = EvaluationRun(
        run_id=uuid4(),
        timestamp=datetime.utcnow(),
        status=EvaluationStatus.RUNNING,
    )

    attempts = {"count": 0}

    def _failing_connect(*args, **kwargs):  # noqa: ARG001
        attempts["count"] += 1
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(
        "courseflow.infrastructure.repositories.evaluation_repo.aiosqlite.connect", _failing_connect
    )

    with pytest.raises(EvaluationPersistenceError, match="after retries"):
        await repo.save_run(run, [])

    assert attempts["count"] == 3

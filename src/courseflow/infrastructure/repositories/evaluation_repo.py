"""
Evaluation repository for persisting evaluation runs and results to SQLite.

Implements:
- SQLite schema creation (evaluation_runs, test_case_results tables)
- CRUD operations for evaluation runs
- Retry logic with exponential backoff for database lock errors
- Baseline run selection (most recent passed=true)
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

import aiosqlite
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from courseflow.domain.eval_models import EvaluationRun, Metrics, TestCaseResult
from courseflow.domain.exceptions import EvaluationPersistenceError


class EvaluationRepository:
    """
    Repository for evaluation run persistence.

    Uses SQLite with async operations (aiosqlite).
    Implements retry logic for database lock errors.
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize repository with database path.

        Args:
            db_path: Path to SQLite database file (creates if not exists)
        """
        self.db_path = Path(db_path)
        self._initialized = False

    async def initialize(self) -> None:
        """Create database schema if not exists."""
        if self._initialized:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        await self._create_tables()
        self._initialized = True

    @retry(
        retry=retry_if_exception_type(sqlite3.OperationalError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def _create_tables(self) -> None:
        """Create evaluation tables with indexes (idempotent)."""
        async with aiosqlite.connect(self.db_path) as db:
            # evaluation_runs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
                    duration_ms INTEGER,
                    passed INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    golden_dataset_version TEXT NOT NULL DEFAULT '1.0',
                    test_case_count INTEGER NOT NULL DEFAULT 15,
                    metrics_json TEXT,
                    created_at_utc DATETIME DEFAULT (datetime('now'))
                )
            """)

            # test_case_results table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS test_case_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    expected_answer TEXT NOT NULL,
                    expected_chunks_json TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    actual_answer TEXT NOT NULL,
                    retrieved_chunks_json TEXT NOT NULL,
                    retrieval_precision REAL NOT NULL CHECK(retrieval_precision >= 0.0 AND retrieval_precision <= 1.0),
                    keyword_match_rate REAL NOT NULL CHECK(keyword_match_rate >= 0.0 AND keyword_match_rate <= 1.0),
                    latency_ms INTEGER NOT NULL CHECK(latency_ms >= 0),
                    passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
                    FOREIGN KEY (run_id) REFERENCES evaluation_runs(run_id) ON DELETE CASCADE
                )
            """)

            # Indexes for performance
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON evaluation_runs(timestamp DESC)"
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_status ON evaluation_runs(status)")
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_passed_timestamp ON evaluation_runs(passed DESC, timestamp DESC)"
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON test_case_results(run_id)")

            await db.commit()

    @retry(
        retry=retry_if_exception_type(sqlite3.OperationalError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def _save_run_with_retry(self, run: EvaluationRun, results: list[TestCaseResult]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            # Serialize metrics to JSON
            metrics_json = None
            if run.metrics:
                metrics_json = json.dumps(
                    {
                        "retrieval_precision_avg": run.metrics.retrieval_precision_avg,
                        "retrieval_precision_min": run.metrics.retrieval_precision_min,
                        "retrieval_precision_max": run.metrics.retrieval_precision_max,
                        "keyword_match_avg": run.metrics.keyword_match_avg,
                        "keyword_match_min": run.metrics.keyword_match_min,
                        "keyword_match_max": run.metrics.keyword_match_max,
                        "latency_p50_ms": run.metrics.latency_p50_ms,
                        "latency_p95_ms": run.metrics.latency_p95_ms,
                        "latency_min_ms": run.metrics.latency_min_ms,
                        "latency_max_ms": run.metrics.latency_max_ms,
                        "pass_rate": run.metrics.pass_rate,
                        "tests_passed": run.metrics.tests_passed,
                        "tests_failed": run.metrics.tests_failed,
                    }
                )

            await db.execute(
                """
                INSERT OR REPLACE INTO evaluation_runs
                (run_id, timestamp, status, duration_ms, passed, error_message,
                 golden_dataset_version, test_case_count, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(run.run_id),
                    run.timestamp.isoformat(),
                    run.status.value,
                    run.duration_ms,
                    1 if run.passed else 0,
                    run.error_message,
                    run.golden_dataset_version,
                    run.test_case_count,
                    metrics_json,
                ),
            )

            await db.execute("DELETE FROM test_case_results WHERE run_id = ?", (str(run.run_id),))

            for result in results:
                await db.execute(
                    """
                    INSERT INTO test_case_results
                    (run_id, question, expected_answer, expected_chunks_json, keywords_json,
                     actual_answer, retrieved_chunks_json, retrieval_precision,
                     keyword_match_rate, latency_ms, passed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(run.run_id),
                        result.question,
                        result.expected_answer,
                        json.dumps(result.expected_chunks),
                        json.dumps(result.keywords),
                        result.actual_answer,
                        json.dumps(result.retrieved_chunks),
                        result.retrieval_precision,
                        result.keyword_match_rate,
                        result.latency_ms,
                        1 if result.passed else 0,
                    ),
                )

            await db.commit()

    async def save_run(self, run: EvaluationRun, results: list[TestCaseResult]) -> None:
        """
        Save evaluation run and results atomically.

        Args:
            run: EvaluationRun entity
            results: List of test case results

        Raises:
            EvaluationPersistenceError: If save fails after retries
        """
        try:
            await self._save_run_with_retry(run, results)
        except sqlite3.OperationalError as e:
            raise EvaluationPersistenceError(
                f"Failed to save evaluation run after retries: {e}"
            ) from e

    async def get_run_by_id(
        self, run_id: UUID, include_results: bool = False
    ) -> EvaluationRun | None:
        """
        Retrieve evaluation run by ID.

        Args:
            run_id: UUID of the run
            include_results: If True, load test case results (not implemented yet)

        Returns:
            EvaluationRun if found, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM evaluation_runs WHERE run_id = ?", (str(run_id),)
            )
            row = await cursor.fetchone()

            if row is None:
                return None

            return self._row_to_run(row)

    async def list_runs(
        self,
        status: str | None = None,
        passed: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[EvaluationRun], dict[str, int | bool]]:
        """
        List evaluation runs with filtering and pagination.

        Args:
            status: Filter by status (running/completed/failed)
            passed: Filter by passed flag (True/False)
            since: Filter runs after this timestamp
            until: Filter runs before this timestamp
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            Tuple of (runs, pagination_info)
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Build WHERE clause
            where_clauses = []
            params = []

            if status:
                where_clauses.append("status = ?")
                params.append(status)
            if passed is not None:
                where_clauses.append("passed = ?")
                params.append(1 if passed else 0)
            if since:
                where_clauses.append("timestamp >= ?")
                params.append(since.isoformat())
            if until:
                where_clauses.append("timestamp <= ?")
                params.append(until.isoformat())

            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Count total
            count_cursor = await db.execute(
                f"SELECT COUNT(*) FROM evaluation_runs {where_clause}", params
            )
            total = (await count_cursor.fetchone())[0]

            # Fetch page
            offset = (page - 1) * page_size
            cursor = await db.execute(
                f"SELECT * FROM evaluation_runs {where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [page_size, offset],
            )
            rows = await cursor.fetchall()

            runs = [self._row_to_run(row) for row in rows]

            # Pagination info
            total_pages = (total + page_size - 1) // page_size
            pagination = {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }

            return runs, pagination

    async def get_baseline_run(self) -> EvaluationRun | None:
        """
        Get most recent evaluation run where passed=true.

        Returns:
            EvaluationRun if baseline exists, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM evaluation_runs
                WHERE passed = 1
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = await cursor.fetchone()

            if row is None:
                return None

            return self._row_to_run(row)

    def _row_to_run(self, row: aiosqlite.Row) -> EvaluationRun:
        """Convert database row to EvaluationRun entity."""
        from courseflow.domain.eval_models import EvaluationStatus

        # Parse metrics JSON
        metrics = None
        if row["metrics_json"]:
            metrics_data = json.loads(row["metrics_json"])
            metrics = Metrics(
                retrieval_precision_avg=metrics_data["retrieval_precision_avg"],
                retrieval_precision_min=metrics_data["retrieval_precision_min"],
                retrieval_precision_max=metrics_data["retrieval_precision_max"],
                keyword_match_avg=metrics_data["keyword_match_avg"],
                keyword_match_min=metrics_data["keyword_match_min"],
                keyword_match_max=metrics_data["keyword_match_max"],
                latency_p50_ms=metrics_data["latency_p50_ms"],
                latency_p95_ms=metrics_data["latency_p95_ms"],
                latency_min_ms=metrics_data["latency_min_ms"],
                latency_max_ms=metrics_data["latency_max_ms"],
                pass_rate=metrics_data["pass_rate"],
                tests_passed=metrics_data["tests_passed"],
                tests_failed=metrics_data["tests_failed"],
            )

        return EvaluationRun(
            run_id=UUID(row["run_id"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            status=EvaluationStatus(row["status"]),
            duration_ms=row["duration_ms"],
            metrics=metrics,
            passed=bool(row["passed"]),
            error_message=row["error_message"],
            golden_dataset_version=row["golden_dataset_version"],
            test_case_count=row["test_case_count"],
        )

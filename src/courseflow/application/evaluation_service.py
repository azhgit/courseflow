"""Evaluation service for automated RAG quality validation."""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from courseflow.config import settings
from courseflow.domain.eval_models import EvaluationRun, GoldenPair, TestCaseResult, compute_metrics
from courseflow.domain.exceptions import EvaluationInProgressException, QuotaExceededError
from courseflow.domain.models import Query
from courseflow.infrastructure.repositories.evaluation_repo import EvaluationRepository

logger = logging.getLogger(__name__)


def calculate_retrieval_precision(
    expected_chunk_ids: list[str], retrieved_chunk_ids: list[str]
) -> float:
    """Calculate precision with exact chunk ID matching."""
    if not retrieved_chunk_ids:
        return 0.0

    expected_set = set(expected_chunk_ids)
    retrieved_set = set(retrieved_chunk_ids)
    return len(expected_set & retrieved_set) / len(retrieved_set)


def calculate_keyword_match_rate(expected_keywords: list[str], generated_answer: str) -> float:
    """Calculate keyword hit ratio with case-insensitive substring matching."""
    if not expected_keywords:
        return 1.0

    answer_lower = generated_answer.lower()
    matched = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return matched / len(expected_keywords)


def compute_percentiles(latencies: list[float]) -> tuple[float, float]:
    """Compute p50 and p95 percentiles."""
    import statistics

    if not latencies:
        raise ValueError("Cannot compute percentiles for empty latency list")

    if len(latencies) == 1:
        return (latencies[0], latencies[0])

    quantiles = statistics.quantiles(latencies, n=100, method="inclusive")
    return (quantiles[49], quantiles[94])


class EvaluationService:
    """Application service orchestrating golden-dataset evaluations."""

    def __init__(
        self,
        repository: EvaluationRepository,
        rag_service: Any,
        golden_dataset_path: str | Path,
        inter_test_delay_seconds: float = 0.0,
    ) -> None:
        self.repository = repository
        self.rag_service = rag_service
        self.golden_dataset_path = Path(golden_dataset_path)
        self.inter_test_delay_seconds = inter_test_delay_seconds
        self._eval_lock = asyncio.Lock()
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

    async def trigger_evaluation(self) -> EvaluationRun:
        """Start evaluation in background and return a running EvaluationRun."""
        if self._eval_lock.locked():
            raise EvaluationInProgressException(
                "Evaluation already in progress. Retry after completion.",
                retry_after=300,
            )

        await self._eval_lock.acquire()
        run = EvaluationRun()
        await self.repository.save_run(run, [])

        task = asyncio.create_task(self._run_background(run))
        run_key = str(run.run_id)
        self._active_tasks[run_key] = task
        task.add_done_callback(lambda _: self._active_tasks.pop(run_key, None))
        return run

    async def run_evaluation(self) -> EvaluationRun:
        """Run evaluation synchronously and return completed EvaluationRun."""
        if self._eval_lock.locked():
            raise EvaluationInProgressException(
                "Evaluation already in progress. Retry after completion.",
                retry_after=300,
            )

        await self._eval_lock.acquire()
        run = EvaluationRun()
        await self.repository.save_run(run, [])
        try:
            await self._execute_evaluation(run)
            return run
        finally:
            self._eval_lock.release()

    async def _run_background(self, run: EvaluationRun) -> None:
        """Execute and persist evaluation in background, always releasing lock."""
        try:
            await self._execute_evaluation(run)
        finally:
            if self._eval_lock.locked():
                self._eval_lock.release()

    async def _execute_evaluation(self, run: EvaluationRun) -> None:
        """Execute all test cases and persist final run state."""
        start_time = time.perf_counter()
        logger.info("Starting evaluation run %s", run.run_id)
        results: list[TestCaseResult] = []

        try:
            golden_pairs = self._load_golden_dataset()

            for index, pair in enumerate(golden_pairs, start=1):
                if index > 1 and self.inter_test_delay_seconds > 0:
                    await asyncio.sleep(self.inter_test_delay_seconds)

                logger.info("Executing evaluation test %s/%s", index, len(golden_pairs))
                result = await self._execute_test_case_with_retry(pair, index)
                results.append(result)
                # Persist incremental progress for long-running evaluations.
                await self.repository.save_run(run, results)

            metrics = compute_metrics(results)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            run.mark_completed(metrics, duration_ms)
            await self.repository.save_run(run, results)
            logger.info("Evaluation run %s completed (passed=%s)", run.run_id, run.passed)

        except QuotaExceededError as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            run.duration_ms = duration_ms
            run.mark_failed(str(exc))
            logger.warning("Evaluation run %s aborted due to quota exhaustion: %s", run.run_id, exc)
            await self.repository.save_run(run, results)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            run.duration_ms = duration_ms
            run.mark_failed(str(exc))
            logger.exception("Evaluation run %s failed", run.run_id)
            await self.repository.save_run(run, results)

    def _load_golden_dataset(self) -> list[GoldenPair]:
        """Load and validate golden dataset file."""
        if not self.golden_dataset_path.exists():
            raise FileNotFoundError(f"Golden dataset not found: {self.golden_dataset_path}")

        with self.golden_dataset_path.open(encoding="utf-8") as file:
            data = json.load(file)

        if "pairs" not in data:
            raise ValueError("Golden dataset must have 'pairs' key")

        pairs = [GoldenPair(**pair_data) for pair_data in data["pairs"]]
        if len(pairs) != 15:
            raise ValueError(f"Expected exactly 15 golden pairs, got {len(pairs)}")
        return pairs

    async def _execute_test_case_with_retry(
        self, pair: GoldenPair, index: int, max_retries: int = 3
    ) -> TestCaseResult:
        """Execute a test case with automatic retry on quota errors."""
        backoff_delays = [15, 30, 60]  # exponential-ish backoff
        last_exc: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await self._execute_test_case(pair)
            except QuotaExceededError as exc:
                last_exc = exc
                if attempt < max_retries:
                    backoff_delay = backoff_delays[min(attempt, len(backoff_delays) - 1)]
                    delay = max(backoff_delay, exc.retry_after)
                    logger.warning(
                        "Test %s/%s quota exceeded (attempt %s/%s), waiting %ss...",
                        index,
                        15,
                        attempt + 1,
                        max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    # Abort entire evaluation after sustained quota exhaustion.
                    raise QuotaExceededError(
                        message=(
                            f"Evaluation aborted at test {index}/15 after quota retries exhausted: "
                            f"{exc.message}"
                        ),
                        retry_after=exc.retry_after,
                    ) from exc
            except Exception as exc:
                last_exc = exc
                break  # non-quota errors are not retried

        logger.exception("Evaluation test %s failed after retries", index)
        return TestCaseResult(
            question=pair.question,
            expected_answer=pair.expected_answer,
            expected_chunks=pair.expected_chunks,
            keywords=pair.keywords,
            actual_answer=f"ERROR: {last_exc}",
            retrieved_chunks=[],
            retrieval_precision=0.0,
            keyword_match_rate=0.0,
            latency_ms=0,
            passed=False,
        )

    async def _execute_test_case(self, pair: GoldenPair) -> TestCaseResult:
        """Execute one golden pair against the RAG pipeline."""
        start_time = time.perf_counter()
        answer = await self.rag_service.answer_query(
            query=Query(text=pair.question),
            subject=pair.subject,
        )

        retrieved_chunks = [Path(source.document.metadata.source).name for source in answer.sources]
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        retrieval_precision = calculate_retrieval_precision(pair.expected_chunks, retrieved_chunks)
        keyword_match_rate = calculate_keyword_match_rate(pair.keywords, answer.answer_text)

        passed = (
            retrieval_precision >= settings.EVAL_PRECISION_THRESHOLD
            and keyword_match_rate >= settings.EVAL_KEYWORD_MATCH_THRESHOLD
            and latency_ms < settings.EVAL_LATENCY_P95_THRESHOLD_MS
        )

        return TestCaseResult(
            question=pair.question,
            expected_answer=pair.expected_answer,
            expected_chunks=pair.expected_chunks,
            keywords=pair.keywords,
            actual_answer=answer.answer_text,
            retrieved_chunks=retrieved_chunks,
            retrieval_precision=retrieval_precision,
            keyword_match_rate=keyword_match_rate,
            latency_ms=latency_ms,
            passed=passed,
        )

    @staticmethod
    def _percent_change(current: float, baseline: float) -> float:
        if baseline == 0:
            return 0.0 if current == 0 else 100.0
        return ((current - baseline) / baseline) * 100

    async def run_local_evaluation(self) -> EvaluationRun:
        """Run a local-only evaluation that avoids external LLM/embedding calls.

        This mode computes retrieval and keyword metrics using local document files
        only. It is useful for debugging evaluation logic without consuming Gemini quota.
        """
        if self._eval_lock.locked():
            raise EvaluationInProgressException(
                "Evaluation already in progress. Retry after completion.",
                retry_after=300,
            )

        await self._eval_lock.acquire()
        run = EvaluationRun()
        await self.repository.save_run(run, [])

        try:
            start_time = time.perf_counter()
            golden_pairs = self._load_golden_dataset()
            results: list[TestCaseResult] = []

            for _index, pair in enumerate(golden_pairs, start=1):
                # No external calls; compute metrics from local docs
                retrieved_chunks = []
                concatenated_answer = []
                for chunk in pair.expected_chunks:
                    # Search docs/ recursively for the chunk filename first, then fallback to root
                    found = False
                    docs_dir = Path("docs")
                    if docs_dir.exists():
                        matches = list(docs_dir.rglob(chunk))
                        if matches:
                            p = matches[0]
                            retrieved_chunks.append(p.name)
                            concatenated_answer.append(p.read_text(encoding="utf-8").strip())
                            found = True
                    if not found:
                        p = Path(chunk)
                        if p.exists():
                            retrieved_chunks.append(p.name)
                            concatenated_answer.append(p.read_text(encoding="utf-8").strip())
                            found = True
                    if not found:
                        # missing chunk: skip adding
                        continue

                actual_answer = "\n\n".join(concatenated_answer)[:2000]
                latency_ms = 0
                retrieval_precision = calculate_retrieval_precision(
                    pair.expected_chunks, retrieved_chunks
                )
                keyword_match_rate = calculate_keyword_match_rate(pair.keywords, actual_answer)

                passed = (
                    retrieval_precision >= settings.EVAL_PRECISION_THRESHOLD
                    and keyword_match_rate >= settings.EVAL_KEYWORD_MATCH_THRESHOLD
                    and latency_ms < settings.EVAL_LATENCY_P95_THRESHOLD_MS
                )

                result = TestCaseResult(
                    question=pair.question,
                    expected_answer=pair.expected_answer,
                    expected_chunks=pair.expected_chunks,
                    keywords=pair.keywords,
                    actual_answer=actual_answer if actual_answer else "",
                    retrieved_chunks=retrieved_chunks,
                    retrieval_precision=retrieval_precision,
                    keyword_match_rate=keyword_match_rate,
                    latency_ms=latency_ms,
                    passed=passed,
                )

                results.append(result)

            metrics = compute_metrics(results)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            run.mark_completed(metrics, duration_ms)
            await self.repository.save_run(run, results)
            return run

        finally:
            if self._eval_lock.locked():
                self._eval_lock.release()

    async def compare_to_baseline(self, run_id: UUID) -> dict[str, Any]:
        """Compare current run to most recent passed=true baseline."""
        run = await self.repository.get_run_by_id(run_id)
        if run is None or run.metrics is None:
            return {"error": "Run not found or has no metrics"}

        baseline = await self.repository.get_baseline_run()
        if baseline is None or baseline.metrics is None:
            return {"baseline_exists": False, "message": "No baseline available for comparison"}

        precision_diff = self._percent_change(
            run.metrics.retrieval_precision_avg, baseline.metrics.retrieval_precision_avg
        )
        keyword_diff = self._percent_change(
            run.metrics.keyword_match_avg, baseline.metrics.keyword_match_avg
        )
        latency_diff = self._percent_change(
            run.metrics.latency_p95_ms, baseline.metrics.latency_p95_ms
        )

        return {
            "baseline_exists": True,
            "baseline_run_id": str(baseline.run_id),
            "baseline_timestamp": baseline.timestamp.isoformat(),
            "comparisons": {
                "retrieval_precision": {
                    "current": run.metrics.retrieval_precision_avg,
                    "baseline": baseline.metrics.retrieval_precision_avg,
                    "change_percent": round(precision_diff, 2),
                    "regressed": precision_diff < -10.0,
                },
                "keyword_match": {
                    "current": run.metrics.keyword_match_avg,
                    "baseline": baseline.metrics.keyword_match_avg,
                    "change_percent": round(keyword_diff, 2),
                    "regressed": keyword_diff < -10.0,
                },
                "latency_p95": {
                    "current": run.metrics.latency_p95_ms,
                    "baseline": baseline.metrics.latency_p95_ms,
                    "change_percent": round(latency_diff, 2),
                    "regressed": latency_diff > 10.0,
                },
            },
            "overall_regression": precision_diff < -10.0
            or keyword_diff < -10.0
            or latency_diff > 10.0,
        }

"""
Domain models for the evaluation system.

Entities:
- EvaluationRun: Aggregate root for evaluation execution
- TestCaseResult: Individual test case result (value object)
- GoldenPair: Test case definition (Pydantic model)
- Metrics: Aggregated statistics (value object)
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# =============================================================================
# Status Enums
# =============================================================================


class EvaluationStatus(StrEnum):
    """Status of an evaluation run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class TestCaseResult:
    """
    Immutable result for a single golden Q&A pair evaluation.

    Value object - has no identity, identified by combination of fields.
    """

    question: str
    expected_answer: str
    expected_chunks: list[str]  # Expected chunk IDs for retrieval
    keywords: list[str]  # Keywords to check in generated answer

    # Results (computed during evaluation)
    actual_answer: str
    retrieved_chunks: list[str]  # Actual chunk IDs retrieved
    retrieval_precision: float  # 0.0-1.0 (relevant/total retrieved)
    keyword_match_rate: float  # 0.0-1.0 (matched/total keywords)
    latency_ms: int  # Query latency in milliseconds

    # Derived
    passed: bool  # True if individual thresholds met

    def __post_init__(self) -> None:
        """Validate field constraints."""
        assert 0.0 <= self.retrieval_precision <= 1.0, "Precision must be 0-1"
        assert 0.0 <= self.keyword_match_rate <= 1.0, "Match rate must be 0-1"
        assert self.latency_ms >= 0, "Latency must be non-negative"
        assert len(self.question) > 0, "Question cannot be empty"
        assert len(self.expected_chunks) > 0, "Must have expected chunks"
        assert len(self.keywords) > 0, "Must have keywords"


@dataclass(frozen=True)
class Metrics:
    """
    Aggregated metrics computed from all test case results.

    Embedded value object within EvaluationRun.
    Immutable - computed once and never modified.
    """

    # Precision metrics
    retrieval_precision_avg: float  # Mean precision across all tests (0.0-1.0)
    retrieval_precision_min: float  # Worst-case precision (0.0-1.0)
    retrieval_precision_max: float  # Best-case precision (0.0-1.0)

    # Keyword match metrics
    keyword_match_avg: float  # Mean keyword match rate (0.0-1.0)
    keyword_match_min: float  # Worst-case match rate (0.0-1.0)
    keyword_match_max: float  # Best-case match rate (0.0-1.0)

    # Latency metrics
    latency_p50_ms: float  # Median latency (milliseconds)
    latency_p95_ms: float  # 95th percentile latency (milliseconds)
    latency_min_ms: int  # Fastest query (milliseconds)
    latency_max_ms: int  # Slowest query (milliseconds)

    # Pass/fail summary
    pass_rate: float  # Percentage of tests that passed (0.0-1.0)
    tests_passed: int  # Count of passed tests
    tests_failed: int  # Count of failed tests

    def __post_init__(self) -> None:
        """Validate metric ranges."""
        assert 0.0 <= self.retrieval_precision_avg <= 1.0
        assert 0.0 <= self.keyword_match_avg <= 1.0
        assert 0.0 <= self.pass_rate <= 1.0
        assert self.latency_p50_ms >= 0
        assert self.latency_p95_ms >= self.latency_p50_ms  # p95 ≥ p50
        assert self.tests_passed + self.tests_failed == 15  # Total = 15


# =============================================================================
# Pydantic Models (Reference Data)
# =============================================================================


class GoldenPair(BaseModel):
    """
    Golden test case definition.

    Loaded from JSON file, immutable during runtime.
    Pydantic model provides validation on load.
    """

    model_config = {"frozen": True}  # Immutable

    question: str = Field(..., min_length=1, description="Question to test")
    expected_answer: str = Field(..., min_length=1, description="Expected answer content")
    expected_chunks: list[str] = Field(
        ..., min_length=1, description="Chunk IDs that should be retrieved"
    )
    keywords: list[str] = Field(..., min_length=1, description="Keywords to check in answer")

    # Metadata (optional)
    subject: str | None = Field(None, description="Subject area (biology, programming, etc.)")
    difficulty: str | None = Field(
        None, description="Difficulty level (beginner, intermediate, advanced)"
    )


# =============================================================================
# Aggregate Root
# =============================================================================


@dataclass
class EvaluationRun:
    """
    Aggregate root for evaluation execution.

    Represents a single run of the automated evaluation suite.
    Contains aggregated metrics and references to individual test results.
    """

    run_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: EvaluationStatus = EvaluationStatus.RUNNING
    duration_ms: int | None = None  # Total execution time
    metrics: Metrics | None = None  # Computed after completion
    passed: bool = False  # True if all quality thresholds met
    error_message: str | None = None  # Set if status=FAILED

    # Metadata
    golden_dataset_version: str = "1.0"  # Track dataset changes
    test_case_count: int = 15  # Expected: 15 golden pairs

    def mark_completed(self, metrics: Metrics, duration_ms: int) -> None:
        """Transition to completed state with results."""
        self.status = EvaluationStatus.COMPLETED
        self.metrics = metrics
        self.duration_ms = duration_ms
        self.passed = self._check_quality_thresholds(metrics)

    def mark_failed(self, error: str) -> None:
        """Transition to failed state with error."""
        self.status = EvaluationStatus.FAILED
        self.error_message = error
        self.passed = False

    def _check_quality_thresholds(self, metrics: Metrics) -> bool:
        """Check if metrics meet minimum quality thresholds."""
        return (
            metrics.retrieval_precision_avg >= 0.70  # ≥70% precision
            and metrics.keyword_match_avg >= 0.80  # ≥80% keyword match
            and metrics.latency_p95_ms < 10000  # <10s p95 latency
        )


# =============================================================================
# Metrics Computation Helpers
# =============================================================================


def compute_metrics(results: list[TestCaseResult]) -> Metrics:
    """
    Compute aggregated metrics from test results.

    Args:
        results: List of test case results (must have exactly 15 items)

    Returns:
        Metrics value object with aggregated statistics
    """
    if len(results) != 15:
        raise ValueError(f"Expected 15 test results, got {len(results)}")

    precisions = [r.retrieval_precision for r in results]
    matches = [r.keyword_match_rate for r in results]
    latencies = [r.latency_ms for r in results]
    passed_count = sum(1 for r in results if r.passed)

    # Compute percentiles using stdlib statistics
    quantiles = statistics.quantiles(latencies, n=100, method="inclusive")
    p50 = quantiles[49]  # Median
    p95 = quantiles[94]  # 95th percentile

    return Metrics(
        retrieval_precision_avg=statistics.mean(precisions),
        retrieval_precision_min=min(precisions),
        retrieval_precision_max=max(precisions),
        keyword_match_avg=statistics.mean(matches),
        keyword_match_min=min(matches),
        keyword_match_max=max(matches),
        latency_p50_ms=p50,
        latency_p95_ms=p95,
        latency_min_ms=min(latencies),
        latency_max_ms=max(latencies),
        pass_rate=passed_count / len(results),
        tests_passed=passed_count,
        tests_failed=len(results) - passed_count,
    )

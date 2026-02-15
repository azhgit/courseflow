"""
Evaluation API routes.

Endpoints:
- POST /api/v1/eval/run - Trigger evaluation
- GET /api/v1/eval/run - List evaluations
- GET /api/v1/eval/run/{run_id} - Get evaluation details
- GET /api/v1/eval/baseline - Get baseline evaluation
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from courseflow.api.dependencies import get_evaluation_service
from courseflow.application.evaluation_service import EvaluationService
from courseflow.domain.exceptions import EvaluationInProgressException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eval", tags=["evaluation"])


# =============================================================================
# Response Models
# =============================================================================


class MetricsResponse(BaseModel):
    """Metrics response model."""

    retrieval_precision_avg: float
    retrieval_precision_min: float
    retrieval_precision_max: float
    keyword_match_avg: float
    keyword_match_min: float
    keyword_match_max: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_min_ms: int
    latency_max_ms: int
    pass_rate: float
    tests_passed: int
    tests_failed: int


class EvaluationRunResponse(BaseModel):
    """Evaluation run response model."""

    run_id: str
    timestamp: str
    status: str
    duration_ms: int | None = None
    metrics: MetricsResponse | None = None
    passed: bool
    error_message: str | None = None
    golden_dataset_version: str
    test_case_count: int


class PaginationInfo(BaseModel):
    """Pagination metadata."""

    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class EvaluationListResponse(BaseModel):
    """List of evaluations with pagination."""

    runs: list[EvaluationRunResponse]
    pagination: PaginationInfo


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    status_code=202,
    summary="Trigger evaluation run",
    description="""
    Trigger automated evaluation against golden dataset (15 Q&A pairs).

    Returns 202 Accepted with run_id immediately. Evaluation executes asynchronously.

    Returns 429 if evaluation already in progress (use Retry-After header).
    """,
)
async def trigger_evaluation(
    eval_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRunResponse:
    """
    POST /api/v1/eval/run

    Trigger evaluation run (async execution).
    """
    try:
        run = await eval_service.trigger_evaluation()

        # Convert to response model
        metrics_response = None
        if run.metrics:
            metrics_response = MetricsResponse(
                retrieval_precision_avg=run.metrics.retrieval_precision_avg,
                retrieval_precision_min=run.metrics.retrieval_precision_min,
                retrieval_precision_max=run.metrics.retrieval_precision_max,
                keyword_match_avg=run.metrics.keyword_match_avg,
                keyword_match_min=run.metrics.keyword_match_min,
                keyword_match_max=run.metrics.keyword_match_max,
                latency_p50_ms=run.metrics.latency_p50_ms,
                latency_p95_ms=run.metrics.latency_p95_ms,
                latency_min_ms=run.metrics.latency_min_ms,
                latency_max_ms=run.metrics.latency_max_ms,
                pass_rate=run.metrics.pass_rate,
                tests_passed=run.metrics.tests_passed,
                tests_failed=run.metrics.tests_failed,
            )

        return EvaluationRunResponse(
            run_id=str(run.run_id),
            timestamp=run.timestamp.isoformat(),
            status=run.status.value,
            duration_ms=run.duration_ms,
            metrics=metrics_response,
            passed=run.passed,
            error_message=run.error_message,
            golden_dataset_version=run.golden_dataset_version,
            test_case_count=run.test_case_count,
        )

    except EvaluationInProgressException as e:
        # HTTP 429 with Retry-After header
        raise HTTPException(
            status_code=429,
            detail={
                "error": "evaluation_in_progress",
                "message": str(e),
                "retry_after": e.retry_after,
            },
            headers={"Retry-After": str(e.retry_after)},
        ) from e


@router.post(
    "/run/local",
    response_model=EvaluationRunResponse,
    status_code=200,
    summary="Run local-only evaluation (no external API calls)",
    description="Run evaluation using local documents only. Useful for debugging without consuming Gemini quota.",
)
async def trigger_local_evaluation(
    eval_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRunResponse:
    """
    POST /api/v1/eval/run/local

    Execute evaluation using local document files only (no embeddings or LLM calls).
    This is synchronous and returns the completed run result.
    """
    try:
        run = await eval_service.run_local_evaluation()

        metrics_response = None
        if run.metrics:
            metrics_response = MetricsResponse(
                retrieval_precision_avg=run.metrics.retrieval_precision_avg,
                retrieval_precision_min=run.metrics.retrieval_precision_min,
                retrieval_precision_max=run.metrics.retrieval_precision_max,
                keyword_match_avg=run.metrics.keyword_match_avg,
                keyword_match_min=run.metrics.keyword_match_min,
                keyword_match_max=run.metrics.keyword_match_max,
                latency_p50_ms=run.metrics.latency_p50_ms,
                latency_p95_ms=run.metrics.latency_p95_ms,
                latency_min_ms=run.metrics.latency_min_ms,
                latency_max_ms=run.metrics.latency_max_ms,
                pass_rate=run.metrics.pass_rate,
                tests_passed=run.metrics.tests_passed,
                tests_failed=run.metrics.tests_failed,
            )

        return EvaluationRunResponse(
            run_id=str(run.run_id),
            timestamp=run.timestamp.isoformat(),
            status=run.status.value,
            duration_ms=run.duration_ms,
            metrics=metrics_response,
            passed=run.passed,
            error_message=run.error_message,
            golden_dataset_version=run.golden_dataset_version,
            test_case_count=run.test_case_count,
        )

    except EvaluationInProgressException as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "evaluation_in_progress",
                "message": str(e),
                "retry_after": e.retry_after,
            },
            headers={"Retry-After": str(e.retry_after)},
        ) from e


@router.get(
    "/run/{run_id}",
    response_model=EvaluationRunResponse,
    summary="Get evaluation run details",
    description="Retrieve evaluation run by ID with optional results.",
)
async def get_evaluation_run(
    run_id: UUID,
    include_results: bool = Query(False, description="Include test case results"),
    eval_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRunResponse:
    """
    GET /api/v1/eval/run/{run_id}

    Retrieve evaluation run details.
    """
    run = await eval_service.repository.get_run_by_id(run_id, include_results=include_results)

    if run is None:
        raise HTTPException(status_code=404, detail=f"Evaluation run {run_id} not found")

    # Convert to response model
    metrics_response = None
    if run.metrics:
        metrics_response = MetricsResponse(
            retrieval_precision_avg=run.metrics.retrieval_precision_avg,
            retrieval_precision_min=run.metrics.retrieval_precision_min,
            retrieval_precision_max=run.metrics.retrieval_precision_max,
            keyword_match_avg=run.metrics.keyword_match_avg,
            keyword_match_min=run.metrics.keyword_match_min,
            keyword_match_max=run.metrics.keyword_match_max,
            latency_p50_ms=run.metrics.latency_p50_ms,
            latency_p95_ms=run.metrics.latency_p95_ms,
            latency_min_ms=run.metrics.latency_min_ms,
            latency_max_ms=run.metrics.latency_max_ms,
            pass_rate=run.metrics.pass_rate,
            tests_passed=run.metrics.tests_passed,
            tests_failed=run.metrics.tests_failed,
        )

    return EvaluationRunResponse(
        run_id=str(run.run_id),
        timestamp=run.timestamp.isoformat(),
        status=run.status.value,
        duration_ms=run.duration_ms,
        metrics=metrics_response,
        passed=run.passed,
        error_message=run.error_message,
        golden_dataset_version=run.golden_dataset_version,
        test_case_count=run.test_case_count,
    )


@router.get(
    "/run",
    response_model=EvaluationListResponse,
    summary="List evaluation runs",
    description="List evaluation runs with filtering and pagination.",
)
async def list_evaluation_runs(
    status: str | None = Query(None, description="Filter by status"),
    passed: bool | None = Query(None, description="Filter by passed flag"),
    since: datetime | None = Query(None, description="Filter runs after this time"),
    until: datetime | None = Query(None, description="Filter runs before this time"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    eval_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationListResponse:
    """
    GET /api/v1/eval/run

    List evaluation runs with filtering and pagination.
    """
    runs, pagination_info = await eval_service.repository.list_runs(
        status=status,
        passed=passed,
        since=since,
        until=until,
        page=page,
        page_size=page_size,
    )

    # Convert to response models
    run_responses = []
    for run in runs:
        metrics_response = None
        if run.metrics:
            metrics_response = MetricsResponse(
                retrieval_precision_avg=run.metrics.retrieval_precision_avg,
                retrieval_precision_min=run.metrics.retrieval_precision_min,
                retrieval_precision_max=run.metrics.retrieval_precision_max,
                keyword_match_avg=run.metrics.keyword_match_avg,
                keyword_match_min=run.metrics.keyword_match_min,
                keyword_match_max=run.metrics.keyword_match_max,
                latency_p50_ms=run.metrics.latency_p50_ms,
                latency_p95_ms=run.metrics.latency_p95_ms,
                latency_min_ms=run.metrics.latency_min_ms,
                latency_max_ms=run.metrics.latency_max_ms,
                pass_rate=run.metrics.pass_rate,
                tests_passed=run.metrics.tests_passed,
                tests_failed=run.metrics.tests_failed,
            )

        run_responses.append(
            EvaluationRunResponse(
                run_id=str(run.run_id),
                timestamp=run.timestamp.isoformat(),
                status=run.status.value,
                duration_ms=run.duration_ms,
                metrics=metrics_response,
                passed=run.passed,
                error_message=run.error_message,
                golden_dataset_version=run.golden_dataset_version,
                test_case_count=run.test_case_count,
            )
        )

    return EvaluationListResponse(
        runs=run_responses,
        pagination=PaginationInfo(**pagination_info),
    )


@router.get(
    "/baseline",
    response_model=EvaluationRunResponse | None,
    summary="Get baseline evaluation",
    description="Get most recent evaluation run where passed=true (baseline for regression detection).",
)
async def get_baseline(
    eval_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRunResponse | None:
    """
    GET /api/v1/eval/baseline

    Get baseline evaluation (most recent passed=true run).
    """
    baseline = await eval_service.repository.get_baseline_run()

    if baseline is None:
        return None

    # Convert to response model
    metrics_response = None
    if baseline.metrics:
        metrics_response = MetricsResponse(
            retrieval_precision_avg=baseline.metrics.retrieval_precision_avg,
            retrieval_precision_min=baseline.metrics.retrieval_precision_min,
            retrieval_precision_max=baseline.metrics.retrieval_precision_max,
            keyword_match_avg=baseline.metrics.keyword_match_avg,
            keyword_match_min=baseline.metrics.keyword_match_min,
            keyword_match_max=baseline.metrics.keyword_match_max,
            latency_p50_ms=baseline.metrics.latency_p50_ms,
            latency_p95_ms=baseline.metrics.latency_p95_ms,
            latency_min_ms=baseline.metrics.latency_min_ms,
            latency_max_ms=baseline.metrics.latency_max_ms,
            pass_rate=baseline.metrics.pass_rate,
            tests_passed=baseline.metrics.tests_passed,
            tests_failed=baseline.metrics.tests_failed,
        )

    return EvaluationRunResponse(
        run_id=str(baseline.run_id),
        timestamp=baseline.timestamp.isoformat(),
        status=baseline.status.value,
        duration_ms=baseline.duration_ms,
        metrics=metrics_response,
        passed=baseline.passed,
        error_message=baseline.error_message,
        golden_dataset_version=baseline.golden_dataset_version,
        test_case_count=baseline.test_case_count,
    )

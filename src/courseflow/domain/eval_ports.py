"""
Port interfaces for the evaluation system.

Defines abstract contracts for:
- EvaluationServicePort: Business logic for evaluation orchestration
- EvaluationRepositoryPort: Persistence for evaluation runs and results
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from courseflow.domain.eval_models import EvaluationRun, TestCaseResult


class EvaluationServicePort(ABC):
    """
    Port for evaluation service business logic.

    Defines operations for:
    - Running automated evaluations
    - Computing metrics
    - Comparing against baseline
    """

    @abstractmethod
    async def run_evaluation(self) -> EvaluationRun:
        """
        Execute automated evaluation against golden dataset.

        Returns:
            EvaluationRun with computed metrics

        Raises:
            EvaluationInProgressException: If evaluation already running
            EvaluationPersistenceError: If results cannot be saved
        """
        pass

    @abstractmethod
    async def compare_to_baseline(self, run_id: UUID) -> dict[str, object]:
        """
        Compare evaluation run to baseline metrics.

        Args:
            run_id: ID of run to compare

        Returns:
            Comparison results with % differences and regression flags
        """
        pass


class EvaluationRepositoryPort(ABC):
    """
    Port for evaluation persistence.

    Defines CRUD operations for evaluation runs and results.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Create database schema if not exists."""
        pass

    @abstractmethod
    async def save_run(self, run: EvaluationRun, results: list[TestCaseResult]) -> None:
        """
        Save evaluation run and results atomically.

        Args:
            run: EvaluationRun entity
            results: List of test case results

        Raises:
            EvaluationPersistenceError: If save fails after retries
        """
        pass

    @abstractmethod
    async def get_run_by_id(
        self, run_id: UUID, include_results: bool = False
    ) -> EvaluationRun | None:
        """
        Retrieve evaluation run by ID.

        Args:
            run_id: UUID of the run
            include_results: If True, load test case results

        Returns:
            EvaluationRun if found, None otherwise
        """
        pass

    @abstractmethod
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
            passed: Filter by passed flag
            since: Filter runs after this timestamp
            until: Filter runs before this timestamp
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            Tuple of (runs, pagination_info)
        """
        pass

    @abstractmethod
    async def get_baseline_run(self) -> EvaluationRun | None:
        """
        Get most recent evaluation run where passed=true.

        Returns:
            EvaluationRun if baseline exists, None otherwise
        """
        pass

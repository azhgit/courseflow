"""APScheduler integration for daily evaluation execution."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

from courseflow.application.evaluation_service import EvaluationService
from courseflow.domain.exceptions import EvaluationInProgressException

logger = logging.getLogger(__name__)


class EvaluationScheduler:
    """Wrapper around APScheduler for daily evaluation jobs."""

    def __init__(
        self,
        eval_service: EvaluationService,
        enabled: bool,
        hour: int,
        minute: int,
    ) -> None:
        self.eval_service = eval_service
        self.enabled = enabled
        self.hour = hour
        self.minute = minute
        self.scheduler = AsyncIOScheduler()

    async def _run_daily_evaluation(self) -> None:
        """Trigger background evaluation job."""
        try:
            run = await self.eval_service.trigger_evaluation()
            logger.info("Scheduled evaluation started: %s", run.run_id)
        except EvaluationInProgressException:
            logger.info("Skipping scheduled evaluation: another run in progress")
        except Exception:
            logger.exception("Scheduled evaluation failed")

    def start(self) -> None:
        """Register daily cron job and start scheduler."""
        if not self.enabled:
            logger.info("Evaluation scheduler disabled")
            return

        self.scheduler.add_job(
            self._run_daily_evaluation,
            trigger=CronTrigger(hour=self.hour, minute=self.minute),
            id="daily_evaluation",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()
        logger.info(
            "Evaluation scheduler started (daily at %02d:%02d UTC)",
            self.hour,
            self.minute,
        )

    def shutdown(self) -> None:
        """Stop scheduler if running."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Evaluation scheduler stopped")

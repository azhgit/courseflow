"""Quota enforcement service (application layer).

Orchestrates quota checking logic: per-IP limits, daily budgets,
and quota status aggregation.
"""

from datetime import UTC, datetime, timedelta

from src.courseflow.domain.exceptions import (
    DailyQuotaExceededError,
    IPLimitExceededError,
    QuotaStorageError,
)
from src.courseflow.domain.models import DailyQuotaLedger, QuotaStatus, QuotaWindow
from src.courseflow.domain.ports import QuotaStorePort


class QuotaService:
    """Service for quota enforcement and monitoring.

    Handles:
    - Per-IP hourly limit checks
    - Daily budget enforcement
    - Quota status aggregation
    """

    def __init__(
        self,
        quota_store: QuotaStorePort,
        hourly_limit: int = 20,
        daily_budget: int = 300,
    ):
        """Initialize quota service.

        Args:
            quota_store: Persistence adapter (QuotaStorePort)
            hourly_limit: Per-IP requests per hour (default 20)
            daily_budget: Global daily budget (default 300)
        """
        self.quota_store = quota_store
        self.hourly_limit = hourly_limit
        self.daily_budget = daily_budget

        # Per-IP windows (ephemeral, reset on restart)
        self.ip_windows: dict[str, QuotaWindow] = {}

    async def check_and_enforce_quota(self, ip: str) -> None:
        """Check IP and daily quota limits. Raises exception if exceeded.

        Args:
            ip: Client IP address

        Raises:
            IPLimitExceededError: If per-IP hourly limit exceeded
            DailyQuotaExceededError: If daily budget exhausted
            QuotaStorageError: If quota storage unavailable
        """
        # Check per-IP hourly limit
        if not self._is_ip_within_limit(ip):
            # Calculate retry-after based on oldest request in window
            window = self.ip_windows[ip]
            if window.request_timestamps:
                oldest = window.request_timestamps[0]
                reset_time = oldest + timedelta(seconds=3600)
                now = datetime.now(UTC)
                retry_after = max(0, int((reset_time - now).total_seconds()))
            else:
                retry_after = 3600

            raise IPLimitExceededError(ip, self.hourly_limit, retry_after)

        # Check daily budget
        try:
            ledger = await self.quota_store.get_daily_ledger()
            if ledger.is_exhausted:
                # Calculate next reset time (midnight UTC tomorrow)
                tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
                reset_at = datetime.combine(
                    tomorrow,
                    datetime.min.time(),
                    tzinfo=UTC,
                ).isoformat()
                raise DailyQuotaExceededError(ledger.used, ledger.limit, reset_at)
        except QuotaStorageError:
            raise
        except DailyQuotaExceededError:
            raise
        except Exception as e:
            raise QuotaStorageError(e)

    async def increment_daily_usage(self) -> None:
        """Increment daily quota counter after request processed.

        Raises:
            QuotaStorageError: If quota storage unavailable
        """
        try:
            await self.quota_store.increment_daily_usage()
        except QuotaStorageError:
            raise
        except Exception as e:
            raise QuotaStorageError(e)

    async def increment_cache_hit(self) -> None:
        """Record cache hit (bypasses quota but counted for metrics).

        Raises:
            QuotaStorageError: If quota storage unavailable
        """
        try:
            await self.quota_store.increment_cache_hit()
        except QuotaStorageError:
            raise
        except Exception as e:
            raise QuotaStorageError(e)

    async def get_quota_status(self, cached_questions_count: int = 10) -> QuotaStatus:
        """Get current quota status for endpoint response.

        Args:
            cached_questions_count: Number of demo questions cached (default 10)

        Returns:
            QuotaStatus value object with current state

        Raises:
            QuotaStorageError: If quota storage unavailable
        """
        try:
            ledger = await self.quota_store.get_daily_ledger()
            cache_hits = await self.quota_store.get_cache_hit_count()

            # Calculate cache hit rate (hits / total queries)
            total_queries = ledger.used + cache_hits
            hit_rate = (cache_hits / total_queries * 100) if total_queries > 0 else 0.0

            # Calculate next reset time (midnight UTC tomorrow)
            tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
            reset_at = datetime.combine(
                tomorrow,
                datetime.min.time(),
                tzinfo=UTC,
            ).isoformat()

            return QuotaStatus(
                daily_used=ledger.used,
                daily_limit=ledger.limit,
                daily_remaining=ledger.remaining,
                daily_percentage_used=ledger.percentage_used,
                daily_reset_at=reset_at,
                quota_warning=ledger.is_warning,
                cached_questions_count=cached_questions_count,
                cache_hit_rate=hit_rate,
                current_time=datetime.now(UTC).isoformat(),
            )
        except QuotaStorageError:
            raise
        except Exception as e:
            raise QuotaStorageError(e)

    # Private methods for per-IP tracking
    def _is_ip_within_limit(self, ip: str) -> bool:
        """Check if IP is within hourly limit.

        Args:
            ip: Client IP address

        Returns:
            True if limit not reached, False if limit exceeded
        """
        now = datetime.now(UTC)

        # Create window if doesn't exist
        if ip not in self.ip_windows:
            self.ip_windows[ip] = QuotaWindow(ip, window_duration_seconds=3600)

        window = self.ip_windows[ip]
        is_allowed = window.is_within_limit(self.hourly_limit, now)

        if is_allowed:
            # Record this request
            window.record_request(now)

        return is_allowed

    def _record_ip_request(self, ip: str) -> None:
        """Record request for IP (internal use).

        Args:
            ip: Client IP address
        """
        if ip not in self.ip_windows:
            self.ip_windows[ip] = QuotaWindow(ip, window_duration_seconds=3600)

        self.ip_windows[ip].record_request()

    def get_ip_request_count(self, ip: str) -> int:
        """Get current request count for IP in rolling window.

        Args:
            ip: Client IP address

        Returns:
            Number of requests in current window
        """
        if ip not in self.ip_windows:
            return 0

        window = self.ip_windows[ip]
        window.prune_old_requests()
        return window.current_count

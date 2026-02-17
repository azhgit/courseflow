"""In-memory quota store adapter for testing and per-IP tracking.

Implements QuotaStorePort using in-memory dictionaries for fast per-IP
rolling window tracking. Daily usage tracking also uses in-memory state.

Note: Per-IP counters reset on process restart (acceptable for demo scope).
Daily usage persistence is handled by SQLiteQuotaStore.
"""

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from src.courseflow.domain.exceptions import QuotaStorageError
from src.courseflow.domain.models import DailyQuotaLedger
from src.courseflow.domain.ports import QuotaStorePort


class InMemoryQuotaStore(QuotaStorePort):
    """In-memory quota storage for per-IP tracking and testing.

    Maintains rolling window timestamps for each IP address.
    Per-IP counters reset on process restart.
    """

    def __init__(self):
        """Initialize empty quota store."""
        # Per-IP rolling windows: { ip: deque[datetime] }
        self.ip_windows: dict[str, deque[datetime]] = defaultdict(deque)

        # Daily ledger (ephemeral, reset on startup)
        self.daily_ledger: DailyQuotaLedger | None = None

        # Cache hit tracking (ephemeral)
        self.cache_hits_today: int = 0

    async def get_daily_ledger(self) -> DailyQuotaLedger:
        """Get or create today's quota ledger.

        Returns:
            DailyQuotaLedger for today (creates if missing)
        """
        try:
            if self.daily_ledger is None:
                today = datetime.now(UTC).date().isoformat()
                self.daily_ledger = DailyQuotaLedger(
                    date=today,
                    used=0,
                    limit=300,  # Default, should be from config
                )
            return self.daily_ledger
        except Exception as e:
            raise QuotaStorageError(e)

    async def increment_daily_usage(self) -> None:
        """Increment daily usage by 1.

        Raises:
            QuotaStorageError: If operation fails
        """
        try:
            ledger = await self.get_daily_ledger()
            ledger.increment()
        except QuotaStorageError:
            raise
        except Exception as e:
            raise QuotaStorageError(e)

    async def reset_daily_usage(self, new_date: str) -> None:
        """Reset daily usage for a new day.

        Args:
            new_date: ISO 8601 date string (YYYY-MM-DD)

        Raises:
            QuotaStorageError: If operation fails
        """
        try:
            self.daily_ledger = DailyQuotaLedger(
                date=new_date,
                used=0,
                limit=300,
            )
            self.cache_hits_today = 0
        except Exception as e:
            raise QuotaStorageError(e)

    async def get_cache_hit_count(self) -> int:
        """Get cache hits for today.

        Returns:
            Number of cache hits recorded today
        """
        try:
            return self.cache_hits_today
        except Exception as e:
            raise QuotaStorageError(e)

    async def increment_cache_hit(self) -> None:
        """Record a cache hit.

        Raises:
            QuotaStorageError: If operation fails
        """
        try:
            self.cache_hits_today += 1
        except Exception as e:
            raise QuotaStorageError(e)

    # Additional methods for per-IP tracking
    def is_ip_within_limit(
        self,
        ip: str,
        limit: int,
        window_seconds: int = 3600,
    ) -> bool:
        """Check if IP is within hourly limit.

        Args:
            ip: Client IP address
            limit: Maximum requests allowed in window
            window_seconds: Rolling window size (default 1 hour)

        Returns:
            True if request count < limit, False if limit reached
        """
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window_seconds)

        # Prune old timestamps for this IP
        while self.ip_windows[ip] and self.ip_windows[ip][0] < cutoff:
            self.ip_windows[ip].popleft()

        # Check limit
        return len(self.ip_windows[ip]) < limit

    def record_ip_request(self, ip: str, timestamp: datetime | None = None) -> None:
        """Record request for IP.

        Args:
            ip: Client IP address
            timestamp: Request timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now(UTC)
        self.ip_windows[ip].append(timestamp)

    def get_ip_request_count(
        self,
        ip: str,
        window_seconds: int = 3600,
    ) -> int:
        """Get current request count for IP in rolling window.

        Args:
            ip: Client IP address
            window_seconds: Rolling window size

        Returns:
            Number of requests in current window
        """
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window_seconds)

        # Prune old timestamps
        while self.ip_windows[ip] and self.ip_windows[ip][0] < cutoff:
            self.ip_windows[ip].popleft()

        return len(self.ip_windows[ip])

"""
Rate Limit Repository Interface and Implementation.

Handles persistence of rate limit counters for IP-based request throttling.
Stores state in SQLite for persistence across container restarts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime

import aiosqlite


@dataclass
class RateLimitEntry:
    """Rate limit entry for a single IP address."""

    id: int | None
    ip_address: str
    request_count: int
    window_start: datetime
    last_request: datetime
    created_at: datetime | None = None


class RateLimitRepository(ABC):
    """Abstract repository for rate limit operations."""

    @abstractmethod
    async def get_by_ip(self, ip_address: str) -> RateLimitEntry | None:
        """
        Retrieve rate limit entry for an IP address.

        Args:
            ip_address: Client IP address

        Returns:
            RateLimitEntry if exists, None otherwise
        """
        pass

    @abstractmethod
    async def create_entry(self, ip_address: str) -> RateLimitEntry:
        """
        Create new rate limit entry for an IP address.

        Args:
            ip_address: Client IP address

        Returns:
            Created RateLimitEntry with id
        """
        pass

    @abstractmethod
    async def increment_counter(self, ip_address: str) -> None:
        """
        Increment request counter and update last_request timestamp.

        Args:
            ip_address: Client IP address
        """
        pass

    @abstractmethod
    async def reset_window(self, ip_address: str) -> None:
        """
        Reset rate limit window for expired entries.
        Sets request_count=1 and window_start=now.

        Args:
            ip_address: Client IP address
        """
        pass

    @abstractmethod
    async def cleanup_old_entries(self, cutoff: datetime) -> int:
        """
        Delete rate limit entries older than cutoff.

        Args:
            cutoff: Delete entries where last_request < cutoff

        Returns:
            Number of deleted entries
        """
        pass


class SQLiteRateLimitRepository(RateLimitRepository):
    """SQLite implementation of rate limit repository."""

    def __init__(self, db_path: str):
        """
        Initialize repository with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    async def get_by_ip(self, ip_address: str) -> RateLimitEntry | None:
        """Retrieve rate limit entry for an IP address."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT id, ip_address, request_count, window_start,
                       last_request, created_at
                FROM rate_limits
                WHERE ip_address = ?
                """,
                (ip_address,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                return RateLimitEntry(
                    id=row[0],
                    ip_address=row[1],
                    request_count=row[2],
                    window_start=datetime.fromisoformat(row[3]),
                    last_request=datetime.fromisoformat(row[4]),
                    created_at=datetime.fromisoformat(row[5]) if row[5] else None,
                )

    async def create_entry(self, ip_address: str) -> RateLimitEntry:
        """Create new rate limit entry for an IP address."""
        now = datetime.now(UTC)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO rate_limits
                (ip_address, request_count, window_start, last_request)
                VALUES (?, 1, ?, ?)
                """,
                (ip_address, now.isoformat(), now.isoformat()),
            )
            await db.commit()
            entry_id = cursor.lastrowid

        return RateLimitEntry(
            id=entry_id,
            ip_address=ip_address,
            request_count=1,
            window_start=now,
            last_request=now,
            created_at=now,
        )

    async def increment_counter(self, ip_address: str) -> None:
        """Increment request counter and update last_request timestamp."""
        now = datetime.now(UTC)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE rate_limits
                SET request_count = request_count + 1,
                    last_request = ?
                WHERE ip_address = ?
                """,
                (now.isoformat(), ip_address),
            )
            await db.commit()

    async def reset_window(self, ip_address: str) -> None:
        """Reset rate limit window for expired entries."""
        now = datetime.now(UTC)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE rate_limits
                SET request_count = 1,
                    window_start = ?,
                    last_request = ?
                WHERE ip_address = ?
                """,
                (now.isoformat(), now.isoformat(), ip_address),
            )
            await db.commit()

    async def cleanup_old_entries(self, cutoff: datetime) -> int:
        """Delete rate limit entries older than cutoff."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM rate_limits
                WHERE last_request < ?
                """,
                (cutoff.isoformat(),),
            )
            await db.commit()
            return cursor.rowcount

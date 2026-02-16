"""Integration tests for quota enforcement.

Tests per-IP limits, daily budget enforcement, and error handling.
"""

import pytest
import pytest_asyncio
from datetime import UTC, datetime, timedelta

from src.courseflow.application.quota_service import QuotaService
from src.courseflow.domain.exceptions import (
    DailyQuotaExceededError,
    IPLimitExceededError,
    QuotaStorageError,
)
from src.courseflow.infrastructure.quota.in_memory_quota import InMemoryQuotaStore


@pytest_asyncio.fixture
async def quota_store():
    """Fixture: In-memory quota store for testing."""
    return InMemoryQuotaStore()


@pytest_asyncio.fixture
async def quota_service(quota_store):
    """Fixture: Quota service with test limits."""
    service = QuotaService(
        quota_store=quota_store,
        hourly_limit=5,  # Low limit for testing
        daily_budget=10,  # Low budget for testing
    )
    # Manually set the daily ledger limit to match daily_budget
    ledger = await service.quota_store.get_daily_ledger()
    ledger.limit = 10
    return service


@pytest.mark.asyncio
async def test_per_ip_limit_allows_20_requests(quota_service):
    """Test that 20th request succeeds, 21st is rejected."""
    ip = "192.168.1.100"
    
    # Set higher limit for this test
    quota_service.hourly_limit = 20
    
    # Record 19 requests
    for _ in range(19):
        quota_service._record_ip_request(ip)
    
    # 20th should be allowed
    await quota_service.check_and_enforce_quota(ip)
    assert quota_service.get_ip_request_count(ip) == 20
    
    # 21st should be rejected
    with pytest.raises(IPLimitExceededError) as exc_info:
        await quota_service.check_and_enforce_quota(ip)
    
    assert exc_info.value.limit == 20
    assert exc_info.value.retry_after_seconds > 0


@pytest.mark.asyncio
async def test_per_ip_limit_different_ips(quota_service):
    """Test that different IPs have independent counters."""
    ip1 = "192.168.1.100"
    ip2 = "192.168.1.101"
    quota_service.hourly_limit = 3
    
    # Fill up IP1
    for _ in range(3):
        quota_service._record_ip_request(ip1)
    
    # IP2 should still have capacity
    await quota_service.check_and_enforce_quota(ip2)
    assert quota_service.get_ip_request_count(ip2) == 1
    
    # IP1 should be rejected
    with pytest.raises(IPLimitExceededError):
        await quota_service.check_and_enforce_quota(ip1)


@pytest.mark.asyncio
async def test_daily_budget_enforcement(quota_service):
    """Test that daily budget limit is enforced."""
    # Set budget to 3
    quota_service.daily_budget = 3
    
    # Use 3 queries
    for _ in range(3):
        await quota_service.check_and_enforce_quota("192.168.1.100")
        await quota_service.increment_daily_usage()
    
    # 4th should be rejected
    with pytest.raises(DailyQuotaExceededError) as exc_info:
        await quota_service.check_and_enforce_quota("192.168.1.200")
    
    assert exc_info.value.used == 3
    assert exc_info.value.limit == 3
    assert "reset_at" in exc_info.value.reset_at


@pytest.mark.asyncio
async def test_quota_status_accuracy(quota_service):
    """Test that status endpoint returns accurate data."""
    # Use 5 queries
    for _ in range(5):
        await quota_service.check_and_enforce_quota("192.168.1.100")
        await quota_service.increment_daily_usage()
    
    # Record 2 cache hits
    for _ in range(2):
        await quota_service.increment_cache_hit()
    
    status = await quota_service.get_quota_status(cached_questions_count=10)
    
    assert status.daily_used == 5
    assert status.daily_remaining == quota_service.daily_budget - 5
    assert status.quota_warning is False  # 5/10 = 50%
    assert status.cached_questions_count == 10
    # Cache hit rate: 2 hits / (5 + 2) total = 28.57%
    assert 28 < status.cache_hit_rate < 29


@pytest.mark.asyncio
async def test_warning_at_80_percent(quota_service):
    """Test that warning triggers at 80% usage."""
    quota_service.daily_budget = 10
    
    # Use 8 queries (80%)
    for _ in range(8):
        await quota_service.check_and_enforce_quota("192.168.1.100")
        await quota_service.increment_daily_usage()
    
    status = await quota_service.get_quota_status()
    assert status.quota_warning is True
    assert status.daily_percentage_used == 80.0


@pytest.mark.asyncio
async def test_rolling_window_pruning():
    """Test that old requests are pruned from rolling window."""
    from src.courseflow.domain.models import QuotaWindow
    
    store = InMemoryQuotaStore()
    service = QuotaService(store, hourly_limit=20)
    
    ip = "192.168.1.100"
    now = datetime.now(UTC)
    
    # Add request 1 hour ago (outside window)
    old_time = now - timedelta(seconds=3601)
    service.ip_windows[ip] = QuotaWindow(ip, [old_time])
    
    # Check should prune old timestamp
    count_before = service.get_ip_request_count(ip)
    assert count_before == 0  # Old request pruned
    
    # New request should be allowed
    await service.check_and_enforce_quota(ip)
    count_after = service.get_ip_request_count(ip)
    assert count_after == 1


@pytest.mark.asyncio
async def test_cache_hit_rate_calculation():
    """Test cache hit rate is calculated correctly."""
    store = InMemoryQuotaStore()
    service = QuotaService(store)
    
    # 10 quota requests
    for _ in range(10):
        await service.check_and_enforce_quota("192.168.1.100")
        await service.increment_daily_usage()
    
    # 5 cache hits
    for _ in range(5):
        await service.increment_cache_hit()
    
    status = await service.get_quota_status()
    # Hit rate: 5 / (10 + 5) = 33.33%
    assert 33 < status.cache_hit_rate < 34

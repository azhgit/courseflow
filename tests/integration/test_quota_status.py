"""Integration tests for quota status endpoint."""

import pytest
import pytest_asyncio

from courseflow.application.quota_service import QuotaService
from courseflow.domain.models import QuotaStatus
from courseflow.infrastructure.quota.in_memory_quota import InMemoryQuotaStore


@pytest_asyncio.fixture
async def quota_service():
    """Fixture: Quota service with in-memory store."""
    store = InMemoryQuotaStore()
    return QuotaService(store, hourly_limit=20, daily_budget=300)


@pytest.mark.asyncio
async def test_quota_status_returns_all_required_fields(quota_service: QuotaService):
    """Test that quota status endpoint returns all required fields."""
    status = await quota_service.get_quota_status(cached_questions_count=10)

    assert isinstance(status, QuotaStatus)
    assert status.daily_used == 0
    assert status.daily_limit == 300
    assert status.daily_remaining == 300
    assert status.daily_percentage_used == 0.0
    assert status.quota_warning is False
    assert status.cached_questions_count == 10
    assert status.cache_hit_rate == 0.0
    assert status.current_time is not None


@pytest.mark.asyncio
async def test_quota_status_percentage_calculation_accuracy(quota_service: QuotaService):
    """Test that percentage is calculated accurately."""
    # Simulate 150 queries (50% of 300)
    store = quota_service.quota_store
    for _ in range(150):
        await store.increment_daily_usage()

    status = await quota_service.get_quota_status()

    assert status.daily_used == 150
    assert status.daily_percentage_used == 50.0
    assert status.daily_remaining == 150


@pytest.mark.asyncio
async def test_quota_warning_at_80_percent(quota_service: QuotaService):
    """Test that warning is set when daily usage >= 80%."""
    store = quota_service.quota_store

    # Simulate 239 queries (79.67% of 300)
    for _ in range(239):
        await store.increment_daily_usage()

    status = await quota_service.get_quota_status()
    assert status.quota_warning is False  # Not yet 80%

    # Add one more to reach 240 (80% exactly)
    await store.increment_daily_usage()

    status = await quota_service.get_quota_status()
    assert status.quota_warning is True
    assert status.daily_percentage_used >= 80.0


@pytest.mark.asyncio
async def test_cache_hit_rate_calculation(quota_service: QuotaService):
    """Test that cache hit rate is calculated correctly."""
    store = quota_service.quota_store

    # Simulate 50 regular queries + 50 cache hits
    for _ in range(50):
        await store.increment_daily_usage()
    for _ in range(50):
        await store.increment_cache_hit()

    status = await quota_service.get_quota_status()

    # Hit rate should be 50 / (50 + 50) * 100 = 50%
    assert status.cache_hit_rate == 50.0
    assert status.daily_used == 50
    # Cache hits don't increment daily_used


@pytest.mark.asyncio
async def test_quota_status_to_dict_format(quota_service: QuotaService):
    """Test that QuotaStatus.to_dict() returns correct JSON format."""
    await quota_service.quota_store.increment_daily_usage()

    status = await quota_service.get_quota_status(cached_questions_count=10)
    payload = status.to_dict()

    # Check nested structure
    assert "daily" in payload
    assert "cache" in payload
    assert "quota_warning" in payload
    assert "timestamp" in payload

    # Verify daily fields
    assert payload["daily"]["used"] == 1
    assert payload["daily"]["limit"] == 300
    assert payload["daily"]["remaining"] == 299
    assert "percentage_used" in payload["daily"]
    assert "reset_at" in payload["daily"]

    # Verify cache fields
    assert payload["cache"]["questions_count"] == 10
    assert "hit_rate" in payload["cache"]

    # Verify types
    assert isinstance(payload["daily"]["used"], int)
    assert isinstance(payload["daily"]["limit"], int)
    assert isinstance(payload["daily"]["percentage_used"], float)
    assert isinstance(payload["quota_warning"], bool)


@pytest.mark.asyncio
async def test_quota_status_reset_time_is_midnight_utc(quota_service: QuotaService):
    """Test that reset time is set to next midnight UTC."""
    status = await quota_service.get_quota_status()

    # Reset at should end with T00:00:00Z (midnight UTC next day)
    reset_at = status.daily_reset_at
    assert reset_at.endswith("T00:00:00+00:00") or reset_at.endswith("Z")


@pytest.mark.asyncio
async def test_quota_status_with_100_percent_usage(quota_service: QuotaService):
    """Test quota status when daily budget is exhausted."""
    store = quota_service.quota_store

    # Max out the daily budget
    for _ in range(300):
        await store.increment_daily_usage()

    status = await quota_service.get_quota_status()

    assert status.daily_used == 300
    assert status.daily_remaining == 0
    assert status.daily_percentage_used == 100.0
    assert status.quota_warning is True

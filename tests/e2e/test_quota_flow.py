"""End-to-end tests for quota protection flow.

Simulates real user scenarios: progressive usage from 0% to 100%,
warning transitions, and accurate cache hit rate reporting.
"""

import pytest
import pytest_asyncio

from courseflow.application.quota_service import QuotaService
from courseflow.infrastructure.quota.in_memory_quota import InMemoryQuotaStore


@pytest_asyncio.fixture
async def fresh_quota_service():
    """Fixture: Fresh quota service with in-memory store for each test."""
    store = InMemoryQuotaStore()
    return QuotaService(store, hourly_limit=20, daily_budget=300)


@pytest.mark.asyncio
async def test_quota_usage_progression_0_to_25_percent(fresh_quota_service: QuotaService):
    """Test quota status as usage progresses from 0% to 25%."""
    store = fresh_quota_service.quota_store

    # Simulate 0 requests (0%)
    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 0.0
    assert status.quota_warning is False

    # Simulate 75 requests (25% of 300)
    for _ in range(75):
        await store.increment_daily_usage()

    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 25.0
    assert status.daily_used == 75
    assert status.quota_warning is False


@pytest.mark.asyncio
async def test_quota_usage_progression_25_to_50_percent(fresh_quota_service: QuotaService):
    """Test quota status as usage progresses from 25% to 50%."""
    store = fresh_quota_service.quota_store

    # Simulate 75 requests (25%)
    for _ in range(75):
        await store.increment_daily_usage()

    # Simulate another 75 requests (now 50%)
    for _ in range(75):
        await store.increment_daily_usage()

    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 50.0
    assert status.daily_used == 150
    assert status.quota_warning is False


@pytest.mark.asyncio
async def test_quota_usage_progression_50_to_80_percent(fresh_quota_service: QuotaService):
    """Test quota status as usage progresses from 50% to 80% (warning threshold)."""
    store = fresh_quota_service.quota_store

    # Simulate 150 requests (50%)
    for _ in range(150):
        await store.increment_daily_usage()

    status = await fresh_quota_service.get_quota_status()
    assert status.quota_warning is False

    # Simulate to 240 requests (80%)
    for _ in range(90):
        await store.increment_daily_usage()

    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 80.0
    assert status.quota_warning is True  # Should trigger at 80%


@pytest.mark.asyncio
async def test_quota_usage_progression_80_to_100_percent(fresh_quota_service: QuotaService):
    """Test quota status as usage progresses from 80% to 100% (exhausted)."""
    store = fresh_quota_service.quota_store

    # Simulate 240 requests (80%)
    for _ in range(240):
        await store.increment_daily_usage()

    status = await fresh_quota_service.get_quota_status()
    assert status.quota_warning is True
    assert status.daily_remaining == 60

    # Simulate to 300 requests (100%)
    for _ in range(60):
        await store.increment_daily_usage()

    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 100.0
    assert status.daily_remaining == 0
    assert status.quota_warning is True


@pytest.mark.asyncio
async def test_quota_warning_state_transitions(fresh_quota_service: QuotaService):
    """Test warning state transitions accurately."""
    store = fresh_quota_service.quota_store

    # Track warning state changes
    warning_states = []

    # Simulate usage progression in 20% increments
    for i in range(0, 6):  # 0%, 20%, 40%, 60%, 80%, 100%
        # Add 60 requests per iteration (60 * 5 = 300)
        if i > 0:
            for _ in range(60):
                await store.increment_daily_usage()

        status = await fresh_quota_service.get_quota_status()
        warning_states.append((status.daily_percentage_used, status.quota_warning))

    # Verify state transitions
    assert warning_states[0] == (0.0, False)  # 0%
    assert warning_states[1] == (20.0, False)  # 20%
    assert warning_states[2] == (40.0, False)  # 40%
    assert warning_states[3] == (60.0, False)  # 60%
    assert warning_states[4] == (80.0, True)  # 80% - warning ON
    assert warning_states[5] == (100.0, True)  # 100% - warning stays ON


@pytest.mark.asyncio
async def test_cache_hit_rate_with_known_values(fresh_quota_service: QuotaService):
    """Test cache hit rate calculation with known request values."""
    store = fresh_quota_service.quota_store

    # Simulate specific usage pattern
    # 100 regular queries + 50 cache hits
    for _ in range(100):
        await store.increment_daily_usage()
    for _ in range(50):
        await store.increment_cache_hit()

    status = await fresh_quota_service.get_quota_status()

    # Hit rate = 50 / (100 + 50) * 100 = 33.33%
    assert abs(status.cache_hit_rate - 33.33) < 0.1
    assert status.daily_used == 100


@pytest.mark.asyncio
async def test_cache_hit_rate_evolution_over_time(fresh_quota_service: QuotaService):
    """Test that cache hit rate updates accurately as more requests arrive."""
    store = fresh_quota_service.quota_store

    # Initial: 0 hits, 0 total (0%)
    status = await fresh_quota_service.get_quota_status()
    assert status.cache_hit_rate == 0.0

    # After 10 regular requests: 0%
    for _ in range(10):
        await store.increment_daily_usage()
    status = await fresh_quota_service.get_quota_status()
    assert status.cache_hit_rate == 0.0

    # After 10 cache hits: 50% (10 cache / 20 total)
    for _ in range(10):
        await store.increment_cache_hit()
    status = await fresh_quota_service.get_quota_status()
    assert status.cache_hit_rate == 50.0

    # After 40 more regular requests: 16.67% (10 cache / 60 total)
    for _ in range(40):
        await store.increment_daily_usage()
    status = await fresh_quota_service.get_quota_status()
    assert abs(status.cache_hit_rate - 16.67) < 0.1


@pytest.mark.asyncio
async def test_full_quota_lifecycle(fresh_quota_service: QuotaService):
    """Test complete quota lifecycle from fresh start to exhaustion."""
    store = fresh_quota_service.quota_store

    # Phase 1: Fresh start
    status = await fresh_quota_service.get_quota_status(cached_questions_count=10)
    assert status.daily_used == 0
    assert status.daily_percentage_used == 0.0
    assert status.quota_warning is False
    assert status.cached_questions_count == 10

    # Phase 2: Early usage (60 requests = 20%)
    for _ in range(60):
        await store.increment_daily_usage()
    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 20.0
    assert status.quota_warning is False

    # Phase 3: Heavy usage with cache hits (120 more = 60% total, 30 cache)
    for _ in range(120):
        await store.increment_daily_usage()
    for _ in range(30):
        await store.increment_cache_hit()
    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 60.0
    assert status.quota_warning is False
    assert status.cache_hit_rate > 0

    # Phase 4: Approaching limit (60 more = 80% total)
    for _ in range(60):
        await store.increment_daily_usage()
    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 80.0
    assert status.quota_warning is True  # Warning engaged

    # Phase 5: Near exhaustion (60 more = 300% = 100%)
    for _ in range(60):
        await store.increment_daily_usage()
    status = await fresh_quota_service.get_quota_status()
    assert status.daily_percentage_used == 100.0
    assert status.daily_remaining == 0
    assert status.quota_warning is True

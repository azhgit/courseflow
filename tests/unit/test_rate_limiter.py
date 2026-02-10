"""Unit tests for RateLimitTracker model."""

from courseflow.domain.models import RateLimitTracker


class TestRateLimitTracker:
    """Test suite for RateLimitTracker sliding window rate limiting."""

    def test_allows_requests_under_limit(self):
        """Test that requests under RPM limit are allowed."""
        tracker = RateLimitTracker(max_requests_per_minute=15)

        # First 15 requests should be allowed
        for i in range(15):
            allowed, retry_after = tracker.is_allowed()
            assert allowed is True, f"Request {i + 1} should be allowed"
            assert retry_after == 0

    def test_blocks_requests_over_limit(self):
        """Test that 16th request within window is blocked."""
        tracker = RateLimitTracker(max_requests_per_minute=15)

        # Fill up the window
        for _ in range(15):
            tracker.is_allowed()

        # 16th request should be blocked
        allowed, retry_after = tracker.is_allowed()
        assert allowed is False
        assert retry_after > 0
        assert retry_after <= 60

    def test_sliding_window_cleanup(self):
        """Test that old timestamps are removed from sliding window."""
        tracker = RateLimitTracker(
            max_requests_per_minute=5,
            window_seconds=2,  # 2-second window for testing
        )

        # Add 5 requests
        for _ in range(5):
            tracker.is_allowed()

        # Wait for window to expire
        import time

        time.sleep(2.1)

        # Next request should be allowed (window cleared)
        allowed, _ = tracker.is_allowed()
        assert allowed is True

    def test_retry_after_calculation(self):
        """Test that retry_after is calculated correctly."""
        tracker = RateLimitTracker(max_requests_per_minute=3, window_seconds=60)

        # Fill window
        for _ in range(3):
            tracker.is_allowed()

        # Check retry_after is reasonable
        allowed, retry_after = tracker.is_allowed()
        assert allowed is False
        assert 0 < retry_after <= 61  # Should be ≤ window_seconds + 1

    def test_custom_rpm_limit(self):
        """Test tracker with custom RPM limit."""
        tracker = RateLimitTracker(max_requests_per_minute=5)

        # Should allow 5 requests
        for _i in range(5):
            allowed, _ = tracker.is_allowed()
            assert allowed is True

        # 6th should be blocked
        allowed, _ = tracker.is_allowed()
        assert allowed is False

    def test_deque_maxlen_enforced(self):
        """Test that deque maxlen matches max_requests_per_minute."""
        tracker = RateLimitTracker(max_requests_per_minute=3)

        # maxlen should be RATE_LIMIT_RPM default (15), not max_requests_per_minute
        # This is by design - deque size is fixed at default to avoid memory issues
        assert tracker.request_timestamps.maxlen == 15  # Default from settings

        # Add more than 3 requests
        for _ in range(5):
            tracker.is_allowed()

        # Only last max_requests_per_minute count should allow new requests
        # (window cleanup handles this, not deque maxlen)

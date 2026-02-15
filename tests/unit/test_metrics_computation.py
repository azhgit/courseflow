"""
Unit tests for evaluation metrics computation.

Tests:
- T015: Exact chunk ID matching
- T016: Keyword match rate
- T017: Percentile computation
- T018: Metrics aggregation
"""

import pytest

from courseflow.application.evaluation_service import (
    calculate_keyword_match_rate,
    calculate_retrieval_precision,
    compute_percentiles,
)
from courseflow.domain.eval_models import TestCaseResult, compute_metrics


class TestRetrievalPrecision:
    """T015: Test exact chunk ID matching."""

    def test_zero_retrieval_returns_zero_precision(self):
        """When no chunks retrieved, precision should be 0.0."""
        expected = ["chunk_1", "chunk_2"]
        retrieved = []

        precision = calculate_retrieval_precision(expected, retrieved)

        assert precision == 0.0

    def test_all_relevant_chunks_retrieved(self):
        """When all retrieved chunks are relevant, precision should be 1.0."""
        expected = ["chunk_1", "chunk_2", "chunk_3"]
        retrieved = ["chunk_1", "chunk_2"]

        precision = calculate_retrieval_precision(expected, retrieved)

        assert precision == 1.0  # 2/2 = 100%

    def test_partial_match(self):
        """When some retrieved chunks are irrelevant, precision reflects ratio."""
        expected = ["chunk_1", "chunk_2"]
        retrieved = ["chunk_1", "chunk_3", "chunk_4"]

        precision = calculate_retrieval_precision(expected, retrieved)

        assert precision == pytest.approx(1 / 3, abs=0.01)  # 1 relevant / 3 retrieved

    def test_no_match(self):
        """When no retrieved chunks are relevant, precision should be 0.0."""
        expected = ["chunk_1", "chunk_2"]
        retrieved = ["chunk_3", "chunk_4"]

        precision = calculate_retrieval_precision(expected, retrieved)

        assert precision == 0.0

    def test_duplicate_handling(self):
        """Duplicates in retrieved list should be deduplicated."""
        expected = ["chunk_1", "chunk_2"]
        retrieved = ["chunk_1", "chunk_1", "chunk_3"]

        precision = calculate_retrieval_precision(expected, retrieved)

        # Set deduplication: retrieved = {chunk_1, chunk_3} (2 unique)
        # Relevant = {chunk_1} (1 match)
        assert precision == pytest.approx(1 / 2, abs=0.01)

    def test_exact_matching_case_sensitive(self):
        """Chunk ID matching should be case-sensitive and exact."""
        expected = ["Chunk_1"]
        retrieved = ["chunk_1"]  # lowercase

        precision = calculate_retrieval_precision(expected, retrieved)

        assert precision == 0.0  # No match due to case difference


class TestKeywordMatchRate:
    """T016: Test keyword match rate computation."""

    def test_zero_keywords_returns_100_percent(self):
        """When no keywords to match, return 100% match by default."""
        keywords = []
        answer = "Any answer text here"

        rate = calculate_keyword_match_rate(keywords, answer)

        assert rate == 1.0

    def test_all_keywords_matched(self):
        """When all keywords present in answer, return 100% match."""
        keywords = ["photosynthesis", "light", "energy"]
        answer = "Photosynthesis converts light energy into chemical energy."

        rate = calculate_keyword_match_rate(keywords, answer)

        assert rate == 1.0  # All 3 keywords matched

    def test_partial_keyword_match(self):
        """When some keywords missing, return correct ratio."""
        keywords = ["DNA", "RNA", "protein"]
        answer = "DNA and RNA are nucleic acids."

        rate = calculate_keyword_match_rate(keywords, answer)

        assert rate == pytest.approx(2 / 3, abs=0.01)  # DNA, RNA matched; protein not

    def test_case_insensitive_matching(self):
        """Keyword matching should be case-insensitive."""
        keywords = ["Python", "JAVA", "c++"]
        answer = "python and java are popular, but C++ is fast"

        rate = calculate_keyword_match_rate(keywords, answer)

        assert rate == 1.0  # All matched despite case differences

    def test_empty_answer(self):
        """When answer is empty, no keywords can match."""
        keywords = ["test", "keyword"]
        answer = ""

        rate = calculate_keyword_match_rate(keywords, answer)

        assert rate == 0.0


class TestPercentileComputation:
    """T017: Test percentile computation using statistics.quantiles."""

    def test_15_latencies_correct_percentiles(self):
        """Test p50 and p95 for typical 15-element list."""
        latencies = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800]

        p50, p95 = compute_percentiles(latencies)

        assert p50 == 450  # Median (8th element in sorted list)
        assert p95 >= 750  # 95th percentile (should be near 15th element)

    def test_single_value_returns_same_for_both(self):
        """When only one value, both p50 and p95 should equal that value."""
        latencies = [500]

        p50, p95 = compute_percentiles(latencies)

        assert p50 == 500
        assert p95 == 500

    def test_empty_list_raises_error(self):
        """Empty latency list should raise ValueError."""
        latencies = []

        with pytest.raises(ValueError, match="empty latency list"):
            compute_percentiles(latencies)

    def test_p95_greater_or_equal_p50(self):
        """p95 should always be >= p50."""
        latencies = [
            100,
            200,
            300,
            400,
            500,
            600,
            700,
            800,
            900,
            1000,
            1100,
            1200,
            1300,
            1400,
            1500,
        ]

        p50, p95 = compute_percentiles(latencies)

        assert p95 >= p50


class TestMetricsAggregation:
    """T018: Test compute_metrics aggregation function."""

    def _create_test_result(
        self, precision: float, keyword_match: float, latency_ms: int, passed: bool
    ) -> TestCaseResult:
        """Helper to create test case result."""
        return TestCaseResult(
            question="Test question",
            expected_answer="Test answer",
            expected_chunks=["chunk_1"],
            keywords=["keyword"],
            actual_answer="Actual answer",
            retrieved_chunks=["chunk_1"],
            retrieval_precision=precision,
            keyword_match_rate=keyword_match,
            latency_ms=latency_ms,
            passed=passed,
        )

    def test_compute_metrics_with_all_passed(self):
        """Test metrics computation when all tests pass."""
        results = [self._create_test_result(1.0, 1.0, 100, True) for _ in range(15)]

        metrics = compute_metrics(results)

        assert metrics.retrieval_precision_avg == 1.0
        assert metrics.keyword_match_avg == 1.0
        assert metrics.pass_rate == 1.0
        assert metrics.tests_passed == 15
        assert metrics.tests_failed == 0

    def test_compute_metrics_with_mixed_results(self):
        """Test metrics computation with mix of passed/failed tests."""
        results = [self._create_test_result(0.8, 0.9, 200, True) for _ in range(10)] + [
            self._create_test_result(0.5, 0.6, 300, False) for _ in range(5)
        ]

        metrics = compute_metrics(results)

        # Average precision: (10 * 0.8 + 5 * 0.5) / 15 = 0.7
        assert metrics.retrieval_precision_avg == pytest.approx(0.7, abs=0.01)
        # Average keyword: (10 * 0.9 + 5 * 0.6) / 15 = 0.8
        assert metrics.keyword_match_avg == pytest.approx(0.8, abs=0.01)
        assert metrics.pass_rate == pytest.approx(10 / 15, abs=0.01)
        assert metrics.tests_passed == 10
        assert metrics.tests_failed == 5

    def test_metrics_min_max_values(self):
        """Test that min/max metrics are computed correctly."""
        results = [
            self._create_test_result(
                0.5, 0.6, 100, True
            ),  # Min precision, min keyword, min latency
            self._create_test_result(
                1.0, 1.0, 1000, True
            ),  # Max precision, max keyword, max latency
        ] + [self._create_test_result(0.75, 0.8, 500, True) for _ in range(13)]

        metrics = compute_metrics(results)

        assert metrics.retrieval_precision_min == 0.5
        assert metrics.retrieval_precision_max == 1.0
        assert metrics.keyword_match_min == 0.6
        assert metrics.keyword_match_max == 1.0
        assert metrics.latency_min_ms == 100
        assert metrics.latency_max_ms == 1000

    def test_total_tests_equals_15(self):
        """Tests passed + tests failed must equal 15."""
        results = [self._create_test_result(0.8, 0.9, 200, True) for _ in range(12)] + [
            self._create_test_result(0.5, 0.6, 300, False) for _ in range(3)
        ]

        metrics = compute_metrics(results)

        assert metrics.tests_passed + metrics.tests_failed == 15

    def test_wrong_number_of_results_raises_error(self):
        """compute_metrics should require exactly 15 results."""
        results = [self._create_test_result(1.0, 1.0, 100, True) for _ in range(10)]

        with pytest.raises(ValueError, match="Expected 15 test results"):
            compute_metrics(results)

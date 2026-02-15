"""Shared streaming helpers for metrics and observability."""


class StreamingMetrics:
    """In-memory metrics for streaming endpoints."""

    def __init__(self) -> None:
        self.query_count = 0
        self.success_count = 0
        self.error_count = 0
        self.timeout_count = 0
        self.first_token_samples: list[int] = []

    def observe_first_token_latency(self, latency_ms: int) -> None:
        """Record first-token latency sample."""
        self.first_token_samples.append(latency_ms)
        if len(self.first_token_samples) > 1000:
            self.first_token_samples = self.first_token_samples[-1000:]

    def first_token_avg_ms(self) -> float:
        """Compute average first-token latency."""
        if not self.first_token_samples:
            return 0.0
        return sum(self.first_token_samples) / len(self.first_token_samples)

    def to_prometheus(self) -> str:
        """Render Prometheus-compatible text output."""
        lines = [
            "# TYPE courseflow_stream_query_total counter",
            f"courseflow_stream_query_total {self.query_count}",
            "# TYPE courseflow_stream_success_total counter",
            f"courseflow_stream_success_total {self.success_count}",
            "# TYPE courseflow_stream_error_total counter",
            f"courseflow_stream_error_total {self.error_count}",
            "# TYPE courseflow_stream_timeout_total counter",
            f"courseflow_stream_timeout_total {self.timeout_count}",
            "# TYPE courseflow_stream_first_token_avg_ms gauge",
            f"courseflow_stream_first_token_avg_ms {self.first_token_avg_ms():.3f}",
        ]
        return "\n".join(lines) + "\n"


streaming_metrics = StreamingMetrics()

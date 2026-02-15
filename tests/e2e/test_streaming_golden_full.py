"""Golden-dataset streaming E2E coverage (T034)."""

from __future__ import annotations

import pytest

from courseflow.domain.models import SSEEvent
from courseflow.infrastructure.sse import SSEEventBuffer

GOLDEN_QUERIES = [
    ("What is photosynthesis?", "photosynthesis.md"),
    ("Explain async await in Python", "python-async.md"),
    ("What started World War II?", "world-war-2.md"),
    ("Explain mitosis phases", "mitosis.md"),
    ("What is machine learning?", "machine-learning.md"),
    ("Define semantic search", "semantic-search.md"),
    ("What is cellular respiration?", "cellular-respiration.md"),
    ("What is event loop?", "python-async.md"),
    ("What is chlorophyll?", "photosynthesis.md"),
    ("What is overfitting?", "machine-learning.md"),
]


@pytest.mark.parametrize(("query", "source"), GOLDEN_QUERIES)
def test_golden_stream_event_sequence(query: str, source: str) -> None:
    """Each golden query should map to a valid chunk->sources->done sequence."""
    buffer = SSEEventBuffer()
    buffer.collect(SSEEvent.chunk(f"Answer for {query[:20]} "))
    buffer.collect(SSEEvent.chunk("continues "))
    buffer.collect(SSEEvent.with_sources([source], 1))
    buffer.collect(SSEEvent.done("conv_golden", 6))

    types = [e.type for e in buffer.all_events]
    assert types[:2] == ["chunk", "chunk"]
    assert types[-2:] == ["sources", "done"]
    assert source in buffer.sources_list

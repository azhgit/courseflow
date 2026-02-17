"""Streaming utilities for cached response delivery.

Simulates streaming output for cached answers by yielding
word-by-word with configurable delay.
"""

import asyncio
from collections.abc import AsyncGenerator

from src.courseflow.domain.models import SSEEvent


async def stream_cached_answer(
    answer: str,
    delay_ms: int = 30,
) -> AsyncGenerator[str, None]:
    """Stream cached answer word-by-word as Server-Sent Events.

    Simulates interactive streaming UX for cached responses.

    Args:
        answer: Pre-computed cached answer text
        delay_ms: Milliseconds to wait between words (default 30)

    Yields:
        SSE-formatted string chunks with word content
    """
    words = answer.split()
    delay_seconds = delay_ms / 1000.0

    for i, word in enumerate(words):
        # Add space between words (except first)
        content = word if i == 0 else f" {word}"

        # Create SSE event for word chunk
        event = SSEEvent.chunk(content)
        yield f"data: {event.model_dump_json()}\n\n"

        # Sleep between words for interactive feel
        await asyncio.sleep(delay_seconds)


async def stream_cached_answer_with_sources(
    answer: str,
    cached_question: str,
    delay_ms: int = 30,
) -> AsyncGenerator[str, None]:
    """Stream cached answer with metadata events.

    Yields initial metadata, then word-by-word content, then done event.

    Args:
        answer: Pre-computed answer text
        cached_question: Original question text
        delay_ms: Milliseconds between words

    Yields:
        SSE-formatted string events (metadata, chunks, done)
    """
    # Initial start event
    yield f"data: {SSEEvent.start().model_dump_json()}\n\n"
    await asyncio.sleep(0.01)

    # Stream answer chunks word-by-word
    async for chunk in stream_cached_answer(answer, delay_ms):
        yield chunk

    # Done event (no real sources for cached, but metadata included)
    yield f"data: {SSEEvent.done('', token_count=len(answer.split())).model_dump_json()}\n\n"

"""Error handlers for streaming responses (T020-T022).

Implements three error handlers for streaming scenarios:
- T020: No relevant documents (empty retrieval)
- T021: Rate limit exceeded mid-stream
- T022: Timeout during streaming
"""

from courseflow.domain.models import SSEEvent


def handle_no_relevant_documents() -> SSEEvent:
    """T020: Handle case where retrieval returns no documents above threshold.
    
    Returns SSE error event without calling LLM (saves quota, prevents hallucination).
    
    Returns:
        SSEEvent with type="error", error="no_relevant_documents"
    """
    return SSEEvent.failure(
        error="no_relevant_documents",
        message="No relevant content found for your query. Try rephrasing or ask about a topic in the knowledge base.",
    )


def handle_rate_limit_exceeded(retry_after: int = 60) -> SSEEvent:
    """T021: Handle rate limit error during streaming.
    
    Returns SSE error event when Gemini API returns 429 status.
    Includes retry_after timing for client backoff.
    
    Args:
        retry_after: Seconds until quota refreshes (default: 60)
    
    Returns:
        SSEEvent with type="error", error="rate_limit_exceeded", retry_after set
    """
    return SSEEvent(
        type="error",
        error="rate_limit_exceeded",
        message=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
        retry_after=retry_after,
    )


def handle_timeout(max_seconds: int = 30) -> SSEEvent:
    """T022: Handle timeout during streaming.
    
    Returns SSE error event when streaming exceeds max duration.
    
    Args:
        max_seconds: Maximum streaming duration (default: 30)
    
    Returns:
        SSEEvent with type="error", error="stream_timeout"
    """
    return SSEEvent.failure(
        error="stream_timeout",
        message=f"Response generation timeout. Maximum streaming duration is {max_seconds} seconds.",
    )

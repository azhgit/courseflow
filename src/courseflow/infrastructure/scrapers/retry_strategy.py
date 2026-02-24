"""Retry strategy with exponential backoff.

This module provides a decorator for retrying async operations with exponential
backoff (1s, 2s, 4s delays, max 3 retries) for transient failures.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from courseflow.domain.scraping.exceptions import (
    NetworkError,
    RateLimitError,
)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


def with_retry(
    max_attempts: int = 3, retriable_exceptions: tuple = (NetworkError, RateLimitError)
) -> Callable[[F], F]:
    """Decorator for retrying async operations with exponential backoff.

    Retries on network errors and rate limit errors with exponential backoff:
    - 1st retry: wait 1 second
    - 2nd retry: wait 2 seconds
    - 3rd retry: wait 4 seconds

    Args:
        max_attempts: Maximum retry attempts (default: 3)
        retriable_exceptions: Tuple of exception types to retry (default: NetworkError, RateLimitError)

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(max_attempts=3)
        async def fetch_data():
            # This will retry up to 3 times on NetworkError or RateLimitError
            return await api_call()
    """

    def decorator(func: F) -> F:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            retry=retry_if_exception_type(retriable_exceptions),
            reraise=True,
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator

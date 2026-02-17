"""Cache service for demo question matching and retrieval.

Provides methods to find cached answers for user questions,
bypassing the RAG pipeline and saving quota.
"""

from courseflow.domain.models import DemoCacheEntry
from courseflow.infrastructure.cache.demo_cache import get_cached_question_by_text


class CacheService:
    """Service for finding and serving cached demo answers.

    Matches user questions to pre-cached responses using normalized text comparison.
    """

    def __init__(self):
        """Initialize cache service."""
        # Cache can be updated dynamically if needed
        pass

    async def find_cached_answer(self, question: str) -> DemoCacheEntry | None:
        """Find a cached answer for the question.

        Performs normalized text matching (lowercase, no punctuation, collapsed whitespace).

        Args:
            question: User's question text

        Returns:
            DemoCacheEntry if match found, None if not cached
        """
        return get_cached_question_by_text(question)

    async def has_cached_answer(self, question: str) -> bool:
        """Check if question has a cached answer.

        Args:
            question: User's question text

        Returns:
            True if cached, False otherwise
        """
        return await self.find_cached_answer(question) is not None

    def get_cache_size(self) -> int:
        """Get number of cached questions.

        Returns:
            Count of demo questions in cache
        """
        from courseflow.infrastructure.cache.demo_cache import DEMO_CACHE

        return len(DEMO_CACHE)

    def get_cached_questions_list(self) -> list[DemoCacheEntry]:
        """Get list of all cached questions.

        Returns:
            List of DemoCacheEntry objects
        """
        from courseflow.infrastructure.cache.demo_cache import get_all_cached_questions

        return get_all_cached_questions()

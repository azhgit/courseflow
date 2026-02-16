"""Integration tests for cache service and streaming."""

import pytest
import pytest_asyncio

from src.courseflow.application.cache_service import CacheService
from src.courseflow.infrastructure.cache.demo_cache import DEMO_CACHE


@pytest_asyncio.fixture
async def cache_service():
    """Fixture: Cache service instance."""
    return CacheService()


@pytest.mark.asyncio
async def test_cache_service_find_exact_match(cache_service):
    """Test finding cached question with exact text match."""
    # Use first cached question
    cached_entry = DEMO_CACHE[0]
    result = await cache_service.find_cached_answer(cached_entry.original_question)
    
    assert result is not None
    assert result.original_question == cached_entry.original_question
    assert result.answer == cached_entry.answer


@pytest.mark.asyncio
async def test_cache_service_find_with_punctuation(cache_service):
    """Test cache matching with added punctuation."""
    # Original: "What is async/await in Python?"
    # Test with extra punctuation
    question_with_extra = "What is async/await in Python!!!???"
    result = await cache_service.find_cached_answer(question_with_extra)
    
    assert result is not None
    assert "async" in result.answer.lower()


@pytest.mark.asyncio
async def test_cache_service_find_with_case_variation(cache_service):
    """Test cache matching with case variation."""
    question_lowercase = "what is async/await in python?"
    result = await cache_service.find_cached_answer(question_lowercase)
    
    assert result is not None
    assert result.subject == "python"


@pytest.mark.asyncio
async def test_cache_service_find_no_match(cache_service):
    """Test that non-cached question returns None."""
    question = "What is the meaning of life, the universe, and everything?"
    result = await cache_service.find_cached_answer(question)
    
    assert result is None


@pytest.mark.asyncio
async def test_cache_service_has_cached_answer(cache_service):
    """Test checking for cached answer."""
    # Cached
    assert await cache_service.has_cached_answer("What is async/await in Python?")
    
    # Not cached
    assert not await cache_service.has_cached_answer("Totally unknown question?")


def test_cache_service_get_cache_size(cache_service):
    """Test getting cache size."""
    size = cache_service.get_cache_size()
    assert size == 10  # Should have 10 demo questions


def test_cache_service_get_cached_questions_list(cache_service):
    """Test retrieving all cached questions."""
    questions = cache_service.get_cached_questions_list()
    
    assert len(questions) == 10
    assert all(q.original_question for q in questions)
    assert all(q.answer for q in questions)
    assert all(q.normalized_question for q in questions)


@pytest.mark.asyncio
async def test_cache_diversity_across_subjects(cache_service):
    """Test that cached questions cover diverse subjects."""
    subjects = set()
    
    for entry in cache_service.get_cached_questions_list():
        if entry.subject:
            subjects.add(entry.subject)
    
    # Should have multiple subjects
    assert len(subjects) >= 4
    assert "python" in subjects
    assert "biology" in subjects
    assert "ai" in subjects


@pytest.mark.asyncio
async def test_normalization_consistency(cache_service):
    """Test that question normalization is consistent."""
    # Test multiple variations of same question
    variations = [
        "What is async/await in Python?",
        "what is async/await in python?",
        "What is async/await in Python!!!",
        "What   is   async/await   in   Python?",
    ]
    
    # All should find the same cached answer
    results = [await cache_service.find_cached_answer(q) for q in variations]
    
    assert all(r is not None for r in results)
    assert len(set(r.original_question for r in results)) == 1  # All same

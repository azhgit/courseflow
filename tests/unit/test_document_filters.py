"""Tests for document filtering functionality."""

import pytest

from courseflow.application.document_filters import filter_development_docs, is_development_doc
from courseflow.domain.models import Document, DocumentMetadata, SearchResult


class TestIsDevDoc:
    """Test document type classification."""

    def test_development_docs_are_identified(self):
        """Ensure development docs are correctly identified."""
        test_cases = [
            # Development docs - should return True
            ("docs/features/001-rag-qa.md", True),
            ("docs/features/002-doc-ingestion.md", True),
            ("docs/deployment/zeabur-setup.md", True),
            ("docs/deployment/environment-variables.md", True),
            ("docs/CHANGELOG.md", True),
            ("docs/changelog.md", True),  # Case insensitive
            ("docs/README.md", True),
            ("docs/readme.md", True),  # Case insensitive
            
            # User-facing docs - should return False
            ("docs/biology/photosynthesis.md", False),
            ("docs/biology/genetics.md", False),
            ("docs/math/derivatives.md", False),
            ("docs/programming/python-async.md", False),
            ("docs/history/world-war-i.md", False),
            ("docs/scraped/Great_Depression.md", False),
            
            # Edge cases
            ("", False),  # Empty string
            (None, False),  # None should be handled gracefully
        ]
        
        for source, expected in test_cases:
            # Handle None case
            if source is None:
                result = is_development_doc(source)
                assert result == expected, f"Failed for {source}"
            else:
                result = is_development_doc(source)
                assert result == expected, f"Failed for {source}: expected {expected}, got {result}"

    def test_case_insensitivity(self):
        """Test that classification is case-insensitive."""
        assert is_development_doc("docs/features/001-rag-qa.md") == True
        assert is_development_doc("docs/FEATURES/001-rag-qa.md") == True
        assert is_development_doc("docs/Features/001-rag-qa.md") == True
        
        assert is_development_doc("docs/CHANGELOG.md") == True
        assert is_development_doc("docs/changelog.md") == True
        assert is_development_doc("docs/Changelog.md") == True


class TestFilterDevelopmentDocs:
    """Test filtering of development documents from search results."""

    def _create_search_result(self, source: str, similarity: float = 0.8) -> SearchResult:
        """Helper to create a SearchResult object."""
        # Create content that meets the minimum length requirement (100 characters)
        long_content = f"Content from {source}. " + ("This is sample test content. " * 5)
        
        doc = Document(
            id=f"doc_{source}",
            content=long_content,
            embedding=[0.1] * 768,
            metadata=DocumentMetadata(
                source=source,
                subject="test",
                chunk_index=0,
                total_chunks=1,
            ),
        )
        return SearchResult(document=doc, similarity_score=similarity)

    def test_filters_out_development_docs(self):
        """Ensure development docs are filtered out."""
        results = [
            self._create_search_result("docs/features/001-rag-qa.md", 0.9),
            self._create_search_result("docs/biology/photosynthesis.md", 0.85),
            self._create_search_result("docs/deployment/zeabur-setup.md", 0.8),
            self._create_search_result("docs/programming/python-async.md", 0.75),
            self._create_search_result("docs/CHANGELOG.md", 0.7),
        ]
        
        filtered = filter_development_docs(results)
        
        # Should only keep biology and programming docs
        assert len(filtered) == 2
        assert filtered[0].document.metadata.source == "docs/biology/photosynthesis.md"
        assert filtered[1].document.metadata.source == "docs/programming/python-async.md"

    def test_preserves_order(self):
        """Ensure filtering preserves result order."""
        results = [
            self._create_search_result("docs/biology/photosynthesis.md", 0.9),
            self._create_search_result("docs/features/001-rag-qa.md", 0.85),
            self._create_search_result("docs/programming/python-async.md", 0.8),
        ]
        
        filtered = filter_development_docs(results)
        
        assert len(filtered) == 2
        # Order should be preserved (biology first, then programming)
        assert filtered[0].document.metadata.source == "docs/biology/photosynthesis.md"
        assert filtered[1].document.metadata.source == "docs/programming/python-async.md"

    def test_returns_empty_list_when_all_filtered(self):
        """Ensure empty list is returned when all docs are filtered out."""
        results = [
            self._create_search_result("docs/features/001-rag-qa.md", 0.9),
            self._create_search_result("docs/deployment/zeabur-setup.md", 0.85),
            self._create_search_result("docs/CHANGELOG.md", 0.8),
        ]
        
        filtered = filter_development_docs(results)
        
        assert filtered == []

    def test_returns_original_when_none_filtered(self):
        """Ensure original results returned when no development docs present."""
        results = [
            self._create_search_result("docs/biology/photosynthesis.md", 0.9),
            self._create_search_result("docs/programming/python-async.md", 0.85),
        ]
        
        filtered = filter_development_docs(results)
        
        assert len(filtered) == 2
        assert filtered[0].document.metadata.source == "docs/biology/photosynthesis.md"
        assert filtered[1].document.metadata.source == "docs/programming/python-async.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

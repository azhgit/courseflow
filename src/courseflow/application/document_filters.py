"""Document filtering to separate development docs from user-facing content.

This module provides utilities to identify and filter out development/internal
documentation that should not be exposed to end users through the RAG system.
"""

import logging

logger = logging.getLogger(__name__)


# Documents that should NOT be returned to users
# These are internal/development documentation
DEVELOPMENT_DOCS = {
    "features/",          # All feature specs (internal)
    "deployment/",        # Deployment guides (admin only)
    "changelog.md",       # Changelog (internal)
    "readme.md",          # README (internal)
}


def is_development_doc(source: str) -> bool:
    """Check if a document is development/internal and should not be exposed to users.
    
    Args:
        source: Document source path (e.g., "docs/features/001-rag-qa.md")
    
    Returns:
        True if document is internal/development, False if it's user-facing content
    """
    if not source:
        return False
    
    source_lower = source.lower()
    
    # Check each pattern in the development docs set
    for pattern in DEVELOPMENT_DOCS:
        if pattern in source_lower:
            return True
    
    return False


def filter_development_docs(search_results: list) -> list:
    """Filter out development documents from search results.
    
    Args:
        search_results: List of SearchResult objects from vector store
    
    Returns:
        Filtered list with development docs removed
    """
    filtered = [
        result
        for result in search_results
        if not is_development_doc(result.document.metadata.source)
    ]
    
    # Log filtering statistics
    removed_count = len(search_results) - len(filtered)
    if removed_count > 0:
        removed_sources = [
            r.document.metadata.source
            for r in search_results
            if is_development_doc(r.document.metadata.source)
        ]
        logger.debug(
            f"Filtered out {removed_count} development document(s): {removed_sources}"
        )
    
    return filtered

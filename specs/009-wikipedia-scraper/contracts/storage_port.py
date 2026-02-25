"""
Port interface for knowledge base storage operations.

This port abstracts ChromaDB (or any vector database), allowing different
implementations for production, testing, or alternative storage backends.

Part of hexagonal architecture: Domain layer depends on this interface,
infrastructure layer provides concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Protocol
from uuid import UUID


class ContentChunk(Protocol):
    """
    Processed content chunk ready for storage.
    
    This is a protocol (structural subtyping) rather than inheritance-based,
    allowing any object with these attributes to satisfy the contract.
    """
    id: UUID
    text: str
    chunk_index: int
    article_title: str
    source_url: str
    
    def to_chroma_metadata(self) -> dict:
        """Convert to ChromaDB metadata dict."""
        ...


class StoragePort(ABC):
    """
    Interface for vector database operations.
    
    Implementations must handle embeddings (generating or using existing),
    similarity search, and CRUD operations for Wikipedia content chunks.
    
    Example implementations:
    - ChromaDBAdapter: Real ChromaDB with Gemini embeddings
    - InMemoryStorageAdapter: Dictionary-based storage for testing
    - PineconeAdapter: Alternative vector DB (future)
    """
    
    @abstractmethod
    async def ingest_chunks(self, chunks: list[ContentChunk]) -> None:
        """
        Store content chunks with embeddings in vector database.
        
        Embeddings are generated automatically by the adapter using
        configured embedding model (e.g., Gemini text-embedding-004).
        
        Uses article source_url as deduplication key:
        - If chunks with same source_url already exist, they are REPLACED
          (not duplicated). This enables idempotent re-scraping.
        - ChromaDB document IDs are deterministic (URL hash + chunk index).
        
        Batch operation: All chunks are ingested in single transaction
        if possible (depends on implementation).
        
        Args:
            chunks: List of ContentChunk objects to store.
                    All chunks from same article should be ingested together
                    to ensure atomic replacement on re-scraping.
        
        Raises:
            StorageError: Failed to store chunks. Possible causes:
                         - ChromaDB connection failure
                         - Embedding generation failure (Gemini API error)
                         - Disk space exhausted (local persistence)
                         
            EmbeddingError: Specifically for embedding generation failures.
                           Subclass of StorageError with more context.
        
        Example:
            ```python
            chunks = [chunk1, chunk2, chunk3]  # All from same article
            await storage_port.ingest_chunks(chunks)
            # Chunks are now searchable in ChromaDB
            ```
        """
        pass
    
    @abstractmethod
    async def check_article_exists(self, source_url: str) -> bool:
        """
        Check if article chunks already exist in database.
        
        Used for deduplication checks and re-scraping decisions.
        
        Args:
            source_url: Wikipedia article URL (canonical).
                        Example: "https://en.wikipedia.org/wiki/Python_(programming_language)"
        
        Returns:
            True if any chunks from this article exist in database.
            False if no chunks found.
        
        Example:
            ```python
            url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
            exists = await storage_port.check_article_exists(url)
            if exists:
                print("Article already in knowledge base, will replace")
            ```
        """
        pass
    
    @abstractmethod
    async def delete_article(self, source_url: str) -> int:
        """
        Remove all chunks associated with an article.
        
        Deletes all chunks where metadata.source_url matches input.
        This is a permanent deletion (no soft delete).
        
        Args:
            source_url: Wikipedia article URL (canonical).
        
        Returns:
            Number of chunks deleted.
            Returns 0 if no chunks found for this article.
        
        Raises:
            StorageError: Failed to delete chunks (connection failure, etc.)
        
        Example:
            ```python
            url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
            deleted_count = await storage_port.delete_article(url)
            print(f"Deleted {deleted_count} chunks")  # "Deleted 16 chunks"
            ```
        """
        pass
    
    @abstractmethod
    async def get_article_metadata(self, source_url: str) -> dict | None:
        """
        Get metadata for article without retrieving full content.
        
        Lightweight operation for listing articles or checking status.
        
        Args:
            source_url: Wikipedia article URL (canonical).
        
        Returns:
            Metadata dict if article found, None if not found.
            
            Metadata dict contains:
            - article_title: str (canonical title)
            - chunk_count: int (total chunks for this article)
            - scrape_timestamp: str (ISO 8601 format)
            - total_word_count: int (sum of all chunk word counts)
        
        Example:
            ```python
            url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
            metadata = await storage_port.get_article_metadata(url)
            if metadata:
                print(f"{metadata['article_title']}: {metadata['chunk_count']} chunks")
            ```
        """
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        limit: int = 5, 
        filters: dict | None = None
    ) -> list[ContentChunk]:
        """
        Perform semantic search across all Wikipedia content.
        
        Searches COURSE-WIDE across all ingested articles (global search).
        This is the primary retrieval mechanism for RAG queries.
        
        Query is embedded using same model as documents (Gemini text-embedding-004),
        then nearest neighbors are retrieved via cosine similarity.
        
        Args:
            query: Natural language search query.
                   Example: "What is photosynthesis?"
            
            limit: Maximum number of chunks to return.
                   Default: 5 (top-5 most relevant).
                   Range: 1-100 (implementation may enforce different limits).
            
            filters: Optional metadata filters to narrow search.
                    Example: {"article_title": "Python (programming language)"}
                    Filters are AND-ed together.
                    
                    Supported filter keys:
                    - article_title: str (exact match)
                    - source_url: str (exact match)
                    - scrape_timestamp: str (ISO 8601, range queries if supported)
        
        Returns:
            List of ContentChunk objects, ordered by relevance (highest first).
            Similarity scores are NOT returned (implementation detail).
            
            Empty list if no relevant chunks found or database is empty.
        
        Raises:
            StorageError: Search failed (connection error, embedding generation failed).
        
        Example:
            ```python
            results = await storage_port.search("What is photosynthesis?", limit=3)
            for chunk in results:
                print(f"{chunk.article_title} [Chunk {chunk.chunk_index}]")
                print(chunk.text[:200])
            ```
        """
        pass
    
    @abstractmethod
    async def list_all_articles(self) -> list[dict]:
        """
        List all Wikipedia articles in the knowledge base.
        
        Returns metadata for all articles, grouped by source_url.
        Useful for CLI 'list' command and statistics.
        
        Returns:
            List of metadata dicts, one per article.
            Each dict contains same fields as get_article_metadata().
            Sorted by scrape_timestamp (most recent first).
        
        Raises:
            StorageError: Failed to list articles.
        
        Example:
            ```python
            articles = await storage_port.list_all_articles()
            print(f"Total articles: {len(articles)}")
            for article in articles:
                print(f"- {article['article_title']}: {article['chunk_count']} chunks")
            ```
        """
        pass

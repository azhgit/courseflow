"""ChromaDB storage adapter implementation.

This module implements the StoragePort interface for storing and retrieving
Wikipedia article chunks in ChromaDB, reusing existing ChromaDB infrastructure.
"""

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from courseflow.config import settings
from courseflow.domain.scraping.exceptions import EmbeddingError, StorageError
from courseflow.domain.scraping.ports import StoragePort
from courseflow.infrastructure.embeddings.gemini import GeminiEmbeddingClient
from courseflow.infrastructure.scrapers.rate_limiter import RateLimiter


class ChromaDBStorageAdapter(StoragePort):
    """ChromaDB storage adapter implementing StoragePort interface.

    Handles ChromaDB operations including ingestion, deduplication,
    deletion, and metadata queries for Wikipedia article chunks.

    Attributes:
        client: ChromaDB persistent client
        collection: ChromaDB collection for Wikipedia content
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str = "wikipedia_articles",
    ) -> None:
        """Initialize ChromaDB storage adapter.

        Args:
            persist_dir: Directory for ChromaDB persistence (default: from settings)
            collection_name: Collection name (default: "wikipedia_articles")

        Raises:
            StorageError: If ChromaDB client cannot be initialized
        """
        try:
            self._persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
            self._collection_name = collection_name

            self.client = chromadb.PersistentClient(
                path=self._persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # Get or create collection with cosine similarity
            self.collection = self.client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._embedding_client = GeminiEmbeddingClient(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_EMBEDDING_MODEL,
            )
            self._embedding_rate_limiter = RateLimiter(rate=settings.SCRAPER_EMBEDDING_RPS)

        except Exception as e:
            raise StorageError(f"Failed to initialize ChromaDB: {e}") from e

    async def ingest_chunks(
        self,
        chunks: list[dict[str, Any]],
        article_title: str,
    ) -> int:
        """Ingest article chunks into ChromaDB with deduplication.

        Args:
            chunks: List of chunk dictionaries
            article_title: Article title for logging/error reporting

        Returns:
            Number of chunks successfully ingested

        Raises:
            StorageError: ChromaDB connection or ingestion failure
            EmbeddingError: Failed to generate embeddings
        """
        try:
            if not chunks:
                return 0

            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []

            for chunk_data in chunks:
                # Generate deterministic ID for deduplication
                chunk_id = self._generate_chunk_id(
                    chunk_data["source_url"],
                    chunk_data["chunk_index"]
                )

                documents.append(chunk_data["text"])
                metadatas.append({
                    "article_title": chunk_data["article_title"],
                    "source": chunk_data.get("source", chunk_data["source_url"]),
                    "file_path": chunk_data.get("file_path", ""),
                    "subject": "scraped",
                    "source_url": chunk_data["source_url"],
                    "chunk_index": chunk_data["chunk_index"],
                    "total_chunks": chunk_data["total_chunks"],
                    "scrape_timestamp": chunk_data["created_at"].isoformat(),
                    "word_count": chunk_data["word_count"],
                })
                ids.append(chunk_id)

            embeddings = []
            for text in documents:
                async with self._embedding_rate_limiter:
                    embedding = await self._embedding_client.generate_embedding(text)
                embeddings.append(embedding)

            # Upsert to ChromaDB (replaces existing chunks with same ID)
            self.collection.upsert(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )

            return len(chunks)

        except Exception as e:
            if "embed" in str(e).lower():
                raise EmbeddingError(
                    f"Failed to generate embeddings: {e}",
                    article_title=article_title
                ) from e
            raise StorageError(
                f"Failed to ingest chunks for '{article_title}': {e}",
                article_title=article_title
            ) from e

    async def check_article_exists(self, article_title: str) -> bool:
        """Check if article chunks already exist in ChromaDB.

        Args:
            article_title: Article title to check

        Returns:
            True if any chunks for this article exist
        """
        try:
            results = self.collection.get(
                where={"article_title": article_title},
                limit=1,
            )
            return len(results.get("ids", [])) > 0

        except Exception as e:
            raise StorageError(f"Failed to check article existence: {e}") from e

    async def delete_article(self, article_title: str) -> int:
        """Delete all chunks for an article from ChromaDB.

        Args:
            article_title: Article title to delete

        Returns:
            Number of chunks deleted

        Raises:
            StorageError: ChromaDB connection or deletion failure
        """
        try:
            # First, get all chunk IDs for this article
            results = self.collection.get(
                where={"article_title": article_title},
            )

            chunk_ids = results.get("ids", [])

            if chunk_ids:
                self.collection.delete(ids=chunk_ids)

            return len(chunk_ids)

        except Exception as e:
            raise StorageError(
                f"Failed to delete article '{article_title}': {e}",
                article_title=article_title
            ) from e

    async def get_article_metadata(
        self,
        article_title: str,
    ) -> dict[str, Any] | None:
        """Get metadata for an ingested article.

        Args:
            article_title: Article title to query

        Returns:
            Dictionary with article metadata or None if not found

        Raises:
            StorageError: ChromaDB query failure
        """
        try:
            results = self.collection.get(
                where={"article_title": article_title},
                include=["metadatas"],
            )

            if not results.get("ids"):
                return None

            metadatas = results["metadatas"]

            # Aggregate metadata from chunks
            total_chunks = len(metadatas)
            source_url = metadatas[0].get("source_url") if metadatas else ""

            # Find earliest and latest timestamps
            timestamps = [
                m.get("scrape_timestamp", "")
                for m in metadatas
                if m.get("scrape_timestamp")
            ]
            timestamps.sort()

            return {
                "article_title": article_title,
                "total_chunks": total_chunks,
                "source_url": source_url,
                "created_at": timestamps[0] if timestamps else None,
                "last_updated": timestamps[-1] if timestamps else None,
            }

        except Exception as e:
            raise StorageError(
                f"Failed to get metadata for '{article_title}': {e}",
                article_title=article_title
            ) from e

    async def search(
        self,
        query: str,
        top_k: int = 5,
        article_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search across all ingested Wikipedia articles.

        Args:
            query: Natural language search query
            top_k: Number of results to return (default: 5)
            article_filter: Optional article title to filter results

        Returns:
            List of search results with chunk content and metadata

        Raises:
            StorageError: ChromaDB query failure
            EmbeddingError: Failed to embed query
        """
        try:
            # Build query parameters
            query_kwargs: dict[str, Any] = {
                "query_embeddings": [await self._embedding_client.generate_embedding(query)],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }

            # Add article filter if specified
            if article_filter:
                query_kwargs["where"] = {"article_title": article_filter}

            # Execute search
            results = self.collection.query(**query_kwargs)

            # Format results
            search_results = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                search_results.append({
                    "text": results["documents"][0][i],
                    "article_title": metadata.get("article_title") or metadata.get("source", "unknown"),
                    "source_url": metadata.get("source_url") or metadata.get("source", ""),
                    "chunk_index": int(metadata.get("chunk_index", 0)),
                    "relevance_score": 1.0 - results["distances"][0][i],  # Convert distance to similarity
                })

            return search_results

        except Exception as e:
            if "embed" in str(e).lower():
                raise EmbeddingError(f"Failed to embed query: {e}") from e
            raise StorageError(f"Failed to execute search: {e}") from e

    async def list_all_articles(self) -> list[dict[str, Any]]:
        """List all ingested Wikipedia articles with metadata.

        Returns:
            List of article metadata dictionaries

        Raises:
            StorageError: ChromaDB query failure
        """
        try:
            # Get all chunks
            results = self.collection.get(
                include=["metadatas"],
            )

            if not results.get("metadatas"):
                return []

            # Group by article title
            articles_map: dict[str, dict[str, Any]] = {}

            for metadata in results["metadatas"]:
                article_title = metadata.get("article_title")
                if not article_title:
                    continue

                if article_title not in articles_map:
                    articles_map[article_title] = {
                        "article_title": article_title,
                        "source_url": metadata.get("source_url", ""),
                        "total_chunks": 0,
                        "created_at": metadata.get("scrape_timestamp"),
                    }

                articles_map[article_title]["total_chunks"] += 1

            return list(articles_map.values())

        except Exception as e:
            raise StorageError(f"Failed to list articles: {e}") from e

    async def close(self) -> None:
        """Close adapter resources."""
        await self._embedding_client.close()

    def _generate_chunk_id(self, source_url: str, chunk_index: int) -> str:
        """Generate deterministic ChromaDB document ID.

        Args:
            source_url: Wikipedia article URL
            chunk_index: Chunk position in article

        Returns:
            Deterministic ID string (e.g., "a3f8e92c_0")
        """
        import hashlib

        url_hash = hashlib.md5(source_url.encode()).hexdigest()[:8]
        return f"{url_hash}_{chunk_index}"

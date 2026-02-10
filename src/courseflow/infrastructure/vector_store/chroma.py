"""ChromaDB adapter implementing VectorStorePort.

This module provides vector similarity search using ChromaDB with persistent local storage.
Uses cosine similarity and HNSW indexing for efficient retrieval.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings

from courseflow.config import settings
from courseflow.domain.exceptions import ServiceUnavailableError
from courseflow.domain.models import Document, DocumentMetadata, SearchResult
from courseflow.domain.ports import VectorStorePort


class ChromaAdapter(VectorStorePort):
    """ChromaDB adapter for vector similarity search.

    Provides persistent local storage of document embeddings and
    efficient similarity search using HNSW indexing.

    Attributes:
        client: ChromaDB persistent client
        collection: ChromaDB collection for documents
    """

    def __init__(
        self,
        persist_dir: str = settings.CHROMA_PERSIST_DIR,
        collection_name: str = settings.CHROMA_COLLECTION_NAME,
        persist_directory: str | None = None,
    ):
        """Initialize ChromaDB adapter.

        Args:
            persist_dir: Directory for ChromaDB persistence
            collection_name: Name of the collection to use

        Raises:
            ServiceUnavailableError: If ChromaDB client cannot be initialized
        """
        try:
            persist_path = persist_directory or persist_dir
            self.client = chromadb.PersistentClient(
                path=persist_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,  # Disable telemetry
                    allow_reset=True,  # Enable reset for testing
                ),
            )

            # Get or create collection with cosine similarity
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},  # Cosine similarity metric
            )

        except Exception as e:
            raise ServiceUnavailableError(f"Failed to initialize ChromaDB: {str(e)}") from e

    async def initialize(self) -> None:
        """Initialize adapter for compatibility with tests.

        The adapter eagerly initializes its client/collection in __init__,
        so this is a no-op.
        """
        return None

    async def search(
        self, query_embedding: list[float], k: int = 3, threshold: float = 0.5
    ) -> list[SearchResult]:
        """Search for similar documents using vector similarity.

        Args:
            query_embedding: Query vector (768-dim)
            k: Number of results to return (top-k)
            threshold: Minimum similarity score (0-1)

        Returns:
            List of SearchResult objects ranked by similarity (filtered by threshold)

        Raises:
            ServiceUnavailableError: If ChromaDB query fails
        """
        try:
            # Query ChromaDB
            results = self.collection.query(query_embeddings=[query_embedding], n_results=k)

            # Extract results
            ids = results["ids"][0]
            documents = results["documents"][0]
            embeddings = results["embeddings"][0] if results["embeddings"] else None
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            # Convert distance to similarity score (ChromaDB returns L2 distance for cosine)
            # For cosine similarity with normalized vectors: similarity = 1 - (distance^2 / 2)
            # However, ChromaDB should return cosine distance directly, so: similarity = 1 - distance
            search_results = []
            for _rank, (doc_id, content, embedding, metadata, distance) in enumerate(
                zip(
                    ids,
                    documents,
                    embeddings or [None] * len(ids),
                    metadatas,
                    distances,
                    strict=False,
                ),
                start=1,
            ):
                # Convert distance to similarity and clamp to [0, 1] for validation.
                similarity = 1.0 - distance
                similarity = max(0.0, min(1.0, float(similarity)))

                # Filter by threshold
                if similarity < threshold:
                    continue

                # Create Document object
                doc_metadata = DocumentMetadata(
                    source=metadata.get("source", ""),
                    subject=metadata.get("subject", ""),
                    topic=metadata.get("topic"),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    total_chunks=int(metadata.get("total_chunks", 1)),
                )

                document = Document(
                    id=doc_id,
                    content=content,
                    embedding=embedding or query_embedding,  # Fallback if not returned
                    metadata=doc_metadata,
                )

                # Create SearchResult
                search_results.append(
                    SearchResult(
                        document=document,
                        similarity_score=similarity,
                    )
                )

            return search_results

        except Exception as e:
            raise ServiceUnavailableError(f"ChromaDB search failed: {str(e)}") from e

    async def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the vector store.

        Args:
            documents: List of Document objects with embeddings

        Raises:
            ServiceUnavailableError: If ChromaDB add operation fails
        """
        try:
            # Prepare data for ChromaDB
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            embeddings = [doc.embedding for doc in documents]
            metadatas = []
            for doc in documents:
                raw = {
                    "source": doc.metadata.source,
                    "subject": doc.metadata.subject,
                    "topic": doc.metadata.topic,
                    "chunk_index": doc.metadata.chunk_index,
                    "total_chunks": doc.metadata.total_chunks,
                }
                # Chroma metadata values must be JSON-serializable primitives; drop None.
                metadatas.append({k: v for k, v in raw.items() if v is not None})

            # Add to collection
            self.collection.add(
                ids=ids, documents=contents, embeddings=embeddings, metadatas=metadatas
            )

        except Exception as e:
            raise ServiceUnavailableError(f"Failed to add documents to ChromaDB: {str(e)}") from e

    def reset(self) -> None:
        """Reset the collection (delete all documents). For testing only."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name, metadata={"hnsw:space": "cosine"}
        )

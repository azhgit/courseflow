"""RAG (Retrieval-Augmented Generation) service implementation."""

import logging
import time

from courseflow.domain.exceptions import NoRelevantDocumentsError
from courseflow.domain.models import Answer, Query, SearchResult
from courseflow.domain.ports import (
    EmbeddingPort,
    LLMPort,
    QueryRepositoryPort,
    VectorStorePort,
)

logger = logging.getLogger(__name__)


class RAGService:
    """Orchestrates RAG query pipeline: embed → search → generate → log.

    This service implements the core RAG workflow:
    1. Generate embedding for user query
    2. Search vector store for similar documents
    3. Filter results by similarity threshold
    4. Generate answer using LLM with retrieved context
    5. Log query and response to repository
    """

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_store: VectorStorePort,
        llm_port: LLMPort,
        query_repo: QueryRepositoryPort,
        similarity_threshold: float = 0.5,
        top_k: int = 3,
    ):
        """Initialize RAG service with dependencies.

        Args:
            embedding_port: Client for generating query embeddings
            vector_store: Vector database for similarity search
            llm_port: LLM client for answer generation
            query_repo: Repository for logging queries
            similarity_threshold: Minimum similarity score (0.5 default)
            top_k: Number of documents to retrieve (3 default)
        """
        self.embedding_port = embedding_port
        self.vector_store = vector_store
        self.llm_port = llm_port
        self.query_repo = query_repo
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k

        logger.info(f"Initialized RAG service with threshold={similarity_threshold}, k={top_k}")

    async def answer_query(self, query: Query) -> Answer:
        """Execute RAG pipeline to answer user query.

        Pipeline stages:
        1. Validate query (done by Pydantic model)
        2. Generate embedding for query text
        3. Search vector store for top-k similar documents
        4. Filter results by similarity threshold
        5. Generate answer using LLM with context
        6. Log query and response
        7. Return Answer with sources and metadata

        Args:
            query: User's question (validated Query model)

        Returns:
            Answer with generated text, sources, and metadata

        Raises:
            NoRelevantDocumentsError: When no documents meet similarity threshold
            QuotaExceededError: When LLM quota is exceeded
            ServiceUnavailableError: When services are unavailable
        """
        start_time = time.time()

        logger.info(f"Processing query: {query.id} - '{query.text}'")

        # Stage 1: Generate embedding
        embedding_start = time.time()
        query_embedding = await self.embedding_port.generate_embedding(query.text)
        embedding_time_ms = int((time.time() - embedding_start) * 1000)
        logger.debug(f"Query embedding generated in {embedding_time_ms}ms")

        # Stage 2: Search vector store
        search_start = time.time()
        search_results = await self.vector_store.search(
            query_embedding=query_embedding,
            k=self.top_k,
        )
        search_time_ms = int((time.time() - search_start) * 1000)
        logger.debug(
            f"Vector search completed in {search_time_ms}ms, found {len(search_results)} results"
        )

        # Stage 3: Filter by threshold
        filtered_results = self._filter_by_threshold(search_results)

        if not filtered_results:
            max_similarity = (
                max([r.similarity_score for r in search_results]) if search_results else 0.0
            )
            logger.warning(
                f"No relevant documents found for query {query.id}. "
                f"Max similarity: {max_similarity:.3f}, threshold: {self.similarity_threshold}"
            )
            raise NoRelevantDocumentsError(
                message=(
                    "No relevant information found in knowledge base "
                    f"(threshold={self.similarity_threshold})"
                ),
                threshold=self.similarity_threshold,
                max_similarity=max_similarity,
            )

        logger.info(
            f"Found {len(filtered_results)} relevant documents "
            f"(threshold: {self.similarity_threshold})"
        )

        # Log similarity scores
        for i, result in enumerate(filtered_results):
            logger.debug(
                f"  [{i + 1}] {result.document.metadata.source}: "
                f"score={result.similarity_score:.3f}"
            )

        # Stage 4: Generate answer using LLM
        llm_start = time.time()

        # IMPORTANT: Only pass plain text context to the LLM.
        # Passing Document objects will stringify the full Pydantic repr (including embeddings),
        # exploding prompt size and latency.
        context_snippets = [
            f"Source: {r.document.metadata.source}\n\n{r.document.content}" for r in filtered_results
        ]

        answer_text, token_usage = await self.llm_port.generate_answer(
            query=query.text,
            context=context_snippets,
        )
        llm_time_ms = int((time.time() - llm_start) * 1000)
        logger.debug(f"LLM generation completed in {llm_time_ms}ms")

        # Calculate total latency
        total_latency_ms = int((time.time() - start_time) * 1000)

        # Log performance breakdown
        logger.info(
            f"Query {query.id} completed in {total_latency_ms}ms "
            f"(embed: {embedding_time_ms}ms, search: {search_time_ms}ms, "
            f"llm: {llm_time_ms}ms)"
        )

        # Stage 5: Log query to repository
        try:
            await self.query_repo.save_query(
                query_id=str(query.id),
                query_text=query.text,
                answer_text=answer_text,
                latency_ms=total_latency_ms,
                token_usage=token_usage,
            )
        except Exception as e:
            logger.error(f"Failed to log query: {e}")
            # Don't fail the request if logging fails

        # Stage 6: Build and return Answer
        answer = Answer(
            query_id=query.id,
            answer_text=answer_text,
            sources=filtered_results,
            latency_ms=total_latency_ms,
            token_usage=token_usage,
        )

        return answer

    def _filter_by_threshold(
        self,
        search_results: list[SearchResult],
    ) -> list[SearchResult]:
        """Filter search results by similarity threshold.

        Args:
            search_results: Raw results from vector search

        Returns:
            List of results with similarity >= threshold
        """
        filtered = [
            result
            for result in search_results
            if result.similarity_score >= self.similarity_threshold
        ]

        return filtered

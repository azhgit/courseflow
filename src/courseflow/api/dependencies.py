"""Dependency injection for FastAPI routes.

Provides injectable dependencies for services, database connections, and configuration.
Uses singleton pattern for expensive clients to avoid creating new instances per request.
"""

from collections import deque
from collections.abc import AsyncGenerator

import aiosqlite

from courseflow.application.rag_service import RAGService
from courseflow.config import settings
from courseflow.domain.models import RateLimitTracker
from courseflow.infrastructure.document_processing.pymupdf_extractor import PyMuPDFExtractor
from courseflow.infrastructure.embeddings.gemini import GeminiEmbeddingClient
from courseflow.infrastructure.llm.gemini import GeminiLLMClient
from courseflow.infrastructure.repositories.chunk_repo import SQLiteChromaChunkRepository
from courseflow.infrastructure.repositories.document_repo import SQLiteDocumentRepository
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
from courseflow.infrastructure.repositories.subject_repo import SQLiteSubjectRepository
from courseflow.infrastructure.text_processing.nltk_tokenizer import NLTKSentenceTokenizer
from courseflow.infrastructure.text_processing.sentence_chunker import SentenceChunker
from courseflow.infrastructure.token_counting.tiktoken_counter import TiktokenCounter
from courseflow.infrastructure.vector_store.chroma import ChromaAdapter

# Singletons to avoid creating new clients per request (which wastes quota)
_embedding_client: GeminiEmbeddingClient | None = None
_llm_client: GeminiLLMClient | None = None
_vector_store: ChromaAdapter | None = None
_pdf_extractor: PyMuPDFExtractor | None = None
_token_counter: TiktokenCounter | None = None
_sentence_tokenizer: NLTKSentenceTokenizer | None = None
_chunker: SentenceChunker | None = None
_subject_repo: SQLiteSubjectRepository | None = None
_document_repo: SQLiteDocumentRepository | None = None
_chunk_repo: SQLiteChromaChunkRepository | None = None

_rate_limiter = RateLimitTracker(
    request_timestamps=deque(maxlen=settings.RATE_LIMIT_RPM),
    max_requests_per_minute=settings.RATE_LIMIT_RPM,
    max_requests_per_day=settings.RATE_LIMIT_DAILY,
)


async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Dependency for SQLite database connection.

    Yields:
        Async SQLite database connection
    """
    db_path = settings.database_path
    async with aiosqlite.connect(db_path) as db:
        yield db


def get_vector_store() -> ChromaAdapter:
    """Dependency for ChromaDB vector store (singleton).

    Returns:
        ChromaDB adapter instance
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaAdapter(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.chroma_collection_name,
        )
    return _vector_store


def get_embedding_client() -> GeminiEmbeddingClient:
    """Dependency for Gemini embedding client (singleton).

    Returns:
        Gemini embedding client instance
    """
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = GeminiEmbeddingClient(
            api_key=settings.gemini_api_key,
        )
    return _embedding_client


def get_llm_client() -> GeminiLLMClient:
    """Dependency for Gemini LLM client (singleton).

    Returns:
        Gemini LLM client instance
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = GeminiLLMClient(
            api_key=settings.gemini_api_key,
            model_name=settings.GEMINI_MODEL,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )
    return _llm_client


def get_query_repository() -> SQLiteQueryRepository:
    """Dependency for query repository.

    Returns:
        SQLite query repository instance
    """
    return SQLiteQueryRepository(db_path=settings.database_path)


def get_rate_limiter() -> RateLimitTracker:
    """Process-local rate limiter to avoid hitting Gemini RPM quota."""
    return _rate_limiter


def get_rag_service() -> RAGService:
    """Dependency for RAG service.

    Creates RAG service with all required dependencies.

    Returns:
        RAG service instance
    """
    embedding_client = get_embedding_client()
    vector_store = get_vector_store()
    llm_client = get_llm_client()
    query_repo = get_query_repository()

    return RAGService(
        embedding_port=embedding_client,
        vector_store=vector_store,
        llm_port=llm_client,
        query_repo=query_repo,
        similarity_threshold=settings.similarity_threshold,
        top_k=settings.top_k_results,
    )


def get_pdf_extractor() -> PyMuPDFExtractor:
    global _pdf_extractor
    if _pdf_extractor is None:
        _pdf_extractor = PyMuPDFExtractor()
    return _pdf_extractor


def get_token_counter() -> TiktokenCounter:
    global _token_counter
    if _token_counter is None:
        _token_counter = TiktokenCounter()
    return _token_counter


def get_sentence_tokenizer() -> NLTKSentenceTokenizer:
    global _sentence_tokenizer
    if _sentence_tokenizer is None:
        _sentence_tokenizer = NLTKSentenceTokenizer()
    return _sentence_tokenizer


def get_chunker() -> SentenceChunker:
    global _chunker
    if _chunker is None:
        _chunker = SentenceChunker(
            tokenizer=get_sentence_tokenizer(),
            token_counter=get_token_counter(),
        )
    return _chunker


def get_subject_repository() -> SQLiteSubjectRepository:
    global _subject_repo
    if _subject_repo is None:
        _subject_repo = SQLiteSubjectRepository(db_path=settings.database_path)
    return _subject_repo


def get_document_repository() -> SQLiteDocumentRepository:
    global _document_repo
    if _document_repo is None:
        _document_repo = SQLiteDocumentRepository(db_path=settings.database_path)
    return _document_repo


def get_chunk_repository() -> SQLiteChromaChunkRepository:
    global _chunk_repo
    if _chunk_repo is None:
        _chunk_repo = SQLiteChromaChunkRepository(
            db_path=settings.database_path,
            chroma_persist_dir=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.chroma_collection_name,
        )
    return _chunk_repo


def get_ingestion_service():
    """Dependency placeholder for ingestion service wiring."""
    try:
        from courseflow.application.ingestion_service import IngestionService
    except Exception as e:
        raise RuntimeError("IngestionService is not implemented yet") from e

    return IngestionService(
        pdf_extractor=get_pdf_extractor(),
        token_counter=get_token_counter(),
        sentence_tokenizer=get_sentence_tokenizer(),
        chunker=get_chunker(),
        embedding_port=get_embedding_client(),
        subject_repo=get_subject_repository(),
        document_repo=get_document_repository(),
        chunk_repo=get_chunk_repository(),
    )


def get_conversation_repository():
    """Dependency: Conversation repository for multi-turn support.

    Returns:
        SQLiteConversationRepository singleton instance

    Raises:
        RuntimeError: If repository cannot be initialized
    """
    try:
        from courseflow.infrastructure.repositories.conversation_repo import (
            SQLiteConversationRepository,
        )
    except Exception as e:
        raise RuntimeError("ConversationRepository is not initialized") from e

    # Use default database path
    return SQLiteConversationRepository(db_path="./data/courseflow.db")

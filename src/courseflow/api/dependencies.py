"""Dependency injection for FastAPI routes.

Provides injectable dependencies for services, database connections, and configuration.
"""

from typing import AsyncGenerator

import aiosqlite

from courseflow.config import settings
from courseflow.infrastructure.embeddings.gemini import GeminiEmbeddingClient
from courseflow.infrastructure.llm.gemini import GeminiLLMClient
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
from courseflow.infrastructure.vector_store.chroma import ChromaAdapter
from courseflow.application.rag_service import RAGService


async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Dependency for SQLite database connection.
    
    Yields:
        Async SQLite database connection
    """
    db_path = settings.database_path
    async with aiosqlite.connect(db_path) as db:
        yield db


def get_vector_store() -> ChromaAdapter:
    """Dependency for ChromaDB vector store.
    
    Returns:
        ChromaDB adapter instance
    """
    return ChromaAdapter(
        persist_directory=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection_name,
    )


def get_embedding_client() -> GeminiEmbeddingClient:
    """Dependency for Gemini embedding client.
    
    Returns:
        Gemini embedding client instance
    """
    return GeminiEmbeddingClient(
        api_key=settings.gemini_api_key,
    )


def get_llm_client() -> GeminiLLMClient:
    """Dependency for Gemini LLM client.
    
    Returns:
        Gemini LLM client instance
    """
    return GeminiLLMClient(
        api_key=settings.gemini_api_key,
    )


def get_query_repository() -> SQLiteQueryRepository:
    """Dependency for query repository.
    
    Returns:
        SQLite query repository instance
    """
    return SQLiteQueryRepository(db_path=settings.database_path)


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

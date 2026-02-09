"""Dependency injection for FastAPI routes.

Provides injectable dependencies for services, database connections, and configuration.
"""

from typing import AsyncGenerator

import aiosqlite

from courseflow.config import settings
from courseflow.infrastructure.embeddings.gemini import GeminiEmbeddingClient
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
from courseflow.infrastructure.vector_store.chroma import ChromaAdapter


async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Dependency for SQLite database connection.
    
    Yields:
        Async SQLite database connection
    """
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    async with aiosqlite.connect(db_path) as db:
        yield db


def get_vector_store() -> ChromaAdapter:
    """Dependency for ChromaDB vector store.
    
    Returns:
        ChromaDB adapter instance
    """
    return ChromaAdapter(
        persist_dir=settings.CHROMA_PERSIST_DIR,
        collection_name=settings.CHROMA_COLLECTION_NAME
    )


def get_embedding_client() -> GeminiEmbeddingClient:
    """Dependency for Gemini embedding client.
    
    Returns:
        Gemini embedding client instance
    """
    return GeminiEmbeddingClient(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_EMBEDDING_MODEL
    )


def get_query_repository() -> SQLiteQueryRepository:
    """Dependency for query repository.
    
    Returns:
        SQLite query repository instance
    """
    return SQLiteQueryRepository(database_url=settings.DATABASE_URL)

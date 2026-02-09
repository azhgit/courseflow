"""FastAPI application initialization.

This module creates and configures the FastAPI application with middleware,
CORS, and lifespan context management for database and ChromaDB initialization.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from courseflow.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown.
    
    Handles initialization and cleanup of resources like database connections
    and ChromaDB clients.
    
    Args:
        app: FastAPI application instance
    
    Yields:
        None (context manager)
    """
    # Startup: Initialize resources
    print("Starting up CourseFlow RAG system...")
    print(f"Using Gemini model: {settings.GEMINI_MODEL}")
    print(f"ChromaDB persist dir: {settings.CHROMA_PERSIST_DIR}")
    print(f"Rate limit: {settings.RATE_LIMIT_RPM} RPM")
    
    # NOTE: Resources are initialized per-request via dependencies
    # This keeps the lifespan simple and allows for easy testing
    
    yield
    
    # Shutdown: Cleanup resources
    print("Shutting down CourseFlow RAG system...")
    # NOTE: Cleanup is handled by individual components (e.g., httpx client close)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="CourseFlow RAG API",
        description="Basic RAG Question Answering System for Educational Content",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register API routes
    from courseflow.api.routes import health
    
    app.include_router(
        health.router,
        prefix=settings.API_V1_PREFIX,
        tags=["health"]
    )
    
    # NOTE: Query endpoint will be added in Phase 3 (User Story 1)
    
    return app


# Create application instance
app = create_app()

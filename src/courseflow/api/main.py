"""FastAPI application initialization.

This module creates and configures the FastAPI application with middleware,
CORS, and lifespan context management for database and ChromaDB initialization.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from courseflow.config import settings
logger = logging.getLogger(__name__)


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
    print(f"ChromaDB persist dir: {settings.chroma_persist_dir}")
    print(f"Rate limit: {settings.rate_limit_rpm} RPM")
    
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
        openapi_url=f"{settings.api_v1_prefix}/openapi.json"
    )
    
    # Add validation exception handler
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors."""
        logger.warning(f"Validation error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "type": "validation_error",
                    "message": "Invalid request data",
                    "details": exc.errors(),
                }
            },
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
    from courseflow.api.routes import health, query
    
    app.include_router(
        health.router,
        prefix=settings.api_v1_prefix,
        tags=["health"]
    )
    
    app.include_router(
        query.router,
        tags=["query"]
    )
    
    return app


# Create application instance
app = create_app()

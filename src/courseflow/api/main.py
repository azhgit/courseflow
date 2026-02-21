"""FastAPI application initialization.

This module creates and configures the FastAPI application with middleware,
CORS, and lifespan context management for database and ChromaDB initialization.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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
    eval_scheduler = None

    # Startup: Initialize resources
    print("Starting up CourseFlow RAG system...")
    print(f"ChromaDB persist dir: {settings.chroma_persist_dir}")
    print(f"ChromaDB persist dir (abs): {settings.CHROMA_PERSIST_DIR}")
    print(f"Rate limit: {settings.rate_limit_rpm} RPM")

    # Initialize all database tables
    try:
        from courseflow.infrastructure.repositories.chunk_repo import SQLiteChromaChunkRepository
        from courseflow.infrastructure.repositories.document_repo import SQLiteDocumentRepository
        from courseflow.infrastructure.repositories.evaluation_repo import EvaluationRepository
        from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
        from courseflow.infrastructure.repositories.subject_repo import SQLiteSubjectRepository

        query_repo = SQLiteQueryRepository()
        await query_repo.initialize()
        logger.info("SQLite queries table initialized")

        subject_repo = SQLiteSubjectRepository()
        await subject_repo.initialize()
        logger.info("SQLite subjects table initialized")

        document_repo = SQLiteDocumentRepository()
        await document_repo.initialize()
        logger.info("SQLite documents table initialized")

        chunk_repo = SQLiteChromaChunkRepository()
        await chunk_repo.initialize()
        logger.info("SQLite chunks table initialized")

        # Initialize evaluation database
        eval_repo = EvaluationRepository(db_path=settings.eval_database_path)
        await eval_repo.initialize()
        logger.info("Evaluation database initialized")

    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    # NOTE: Other resources are initialized per-request via dependencies
    # This keeps the lifespan simple and allows for easy testing
    try:
        import nltk  # type: ignore[import-untyped]

        nltk_data_dir = os.getenv("NLTK_DATA")
        if nltk_data_dir:
            nltk.data.path.append(nltk_data_dir)
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)
        logger.info("NLTK tokenizer data verified")
    except Exception as e:
        logger.warning(f"Failed to initialize NLTK data: {e}")

    # Initialize evaluation scheduler
    if settings.EVAL_SCHEDULE_ENABLED:
        try:
            from courseflow.api.dependencies import get_evaluation_service
            from courseflow.infrastructure.scheduler.eval_scheduler import EvaluationScheduler

            eval_service = await get_evaluation_service()
            eval_scheduler = EvaluationScheduler(
                eval_service=eval_service,
                enabled=settings.EVAL_SCHEDULE_ENABLED,
                hour=settings.EVAL_SCHEDULE_HOUR,
                minute=settings.EVAL_SCHEDULE_MINUTE,
            )
            eval_scheduler.start()
            app.state.eval_scheduler = eval_scheduler
        except Exception as e:
            logger.warning(f"Failed to initialize evaluation scheduler: {e}")

    # Initialize quota protection (006-demo-protection)
    try:
        from courseflow.application.quota_service import QuotaService
        from courseflow.infrastructure.quota.sqlite_quota import SQLiteQuotaStore

        quota_store = SQLiteQuotaStore(settings.database_path)
        quota_service = QuotaService(
            quota_store=quota_store,
            hourly_limit=settings.QUOTA_HOURLY_LIMIT,
            daily_budget=settings.QUOTA_DAILY_BUDGET,
        )
        app.state.quota_service = quota_service
        logger.info(
            f"Quota protection initialized: {settings.QUOTA_HOURLY_LIMIT} req/hr, "
            f"{settings.QUOTA_DAILY_BUDGET} req/day"
        )
    except Exception as e:
        logger.warning(f"Failed to initialize quota protection: {e}")

    yield

    # Shutdown: Cleanup resources
    print("Shutting down CourseFlow RAG system...")
    if eval_scheduler is not None:
        eval_scheduler.shutdown()
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
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )

    # Add validation exception handler
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
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

    # Rate limit middleware (Feature 008: Zeabur deployment)
    # Must be added BEFORE quota middleware for proper ordering
    try:
        from courseflow.api.middleware.rate_limit import RateLimitMiddleware

        # Allow disabling rate limiting for local development by setting
        # LOCAL_UNLIMITED=true (default true for local/dev).
        # Production deployments should set LOCAL_UNLIMITED=false.
        # Also skip registration if QUOTA_HOURLY_LIMIT <= 0 (treat as unlimited).
        local_unlimited = os.getenv("LOCAL_UNLIMITED", "true").lower() == "true"

        if local_unlimited:
            logger.info("Rate limit middleware disabled for local development (LOCAL_UNLIMITED=true).")
        elif settings.QUOTA_HOURLY_LIMIT <= 0:
            logger.info("Rate limit middleware disabled because QUOTA_HOURLY_LIMIT <= 0.")
        else:
            app.add_middleware(
                RateLimitMiddleware,
                db_path=settings.database_path,
                hourly_limit=settings.QUOTA_HOURLY_LIMIT,
            )
            logger.info(f"Rate limit middleware registered: {settings.QUOTA_HOURLY_LIMIT} req/hour")
    except Exception as e:
        logger.warning(f"Failed to initialize rate limit middleware: {e}")

    # Quota middleware (must be added BEFORE CORS for proper ordering)
    if hasattr(app.state, "quota_service"):
        from courseflow.api.middleware.quota_middleware import QuotaMiddleware

        app.add_middleware(QuotaMiddleware, quota_service=app.state.quota_service)
        logger.info("Quota middleware registered")

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    from courseflow.api.routes import documents, evaluation, health, ingest, query, quota, subjects

    app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["health"])

    app.include_router(query.router, tags=["query"])
    app.include_router(ingest.router, tags=["ingestion"])
    app.include_router(documents.router, tags=["documents"])
    app.include_router(subjects.router, tags=["subjects"])
    app.include_router(quota.router, tags=["quota"])
    app.include_router(evaluation.router, prefix=settings.api_v1_prefix, tags=["evaluation"])

    return app


# Create application instance
app = create_app()

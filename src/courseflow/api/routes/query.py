"""Query endpoint for RAG question answering."""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from courseflow.domain.models import Query
from courseflow.domain.exceptions import (
    NoRelevantDocumentsError,
    QuotaExceededError,
    ServiceUnavailableError,
    ValidationError as DomainValidationError,
)
from courseflow.application.rag_service import RAGService
from courseflow.api.dependencies import get_rag_service, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["query"])


# Request/Response schemas
class QueryRequest(BaseModel):
    """Request schema for query endpoint."""
    query: str = Field(..., description="User's question")


class SourceInfo(BaseModel):
    """Source document information in response."""
    content: str
    source: str
    subject: str
    similarity_score: float


class QueryResponse(BaseModel):
    """Response schema for successful query."""
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class ErrorDetail(BaseModel):
    """Error details in error response."""
    type: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: ErrorDetail


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Successful query response with answer and sources"},
        400: {"description": "Validation error (empty query, too long, etc.)"},
        404: {"description": "No relevant documents found"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Service unavailable"},
    },
)
async def query_endpoint(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service),
    rate_limiter=Depends(get_rate_limiter),
) -> QueryResponse:
    """Handle POST /api/v1/query requests.
    
    Accepts a user question, performs RAG retrieval and generation,
    and returns an AI-generated answer with source attribution.
    
    Args:
        request: Query request with user's question
        rag_service: Injected RAG service dependency
        
    Returns:
        JSON response with answer, sources, and metadata
        
    Raises:
        HTTPException: With appropriate status code for errors
    """
    try:
        query_text = request.query.strip() if request.query is not None else ""
        if not query_text:
            raise ValueError("query must not be empty")
        if len(query_text) > 1000:
            raise ValueError("query must be <= 1000 characters")

        # Create Query model (domain validation)
        query = Query(text=query_text)

        allowed, retry_after = rate_limiter.is_allowed()
        if not allowed:
            logger.warning(
                f"Local rate limit exceeded; retry_after={retry_after}s"
            )
            raise QuotaExceededError(
                message="Rate limit exceeded (local guard)",
                retry_after=retry_after,
            )
        
        logger.info(f"Received query: {query.id} - '{query.text[:50]}...'")
        
        # Execute RAG pipeline
        answer = await rag_service.answer_query(query)
        
        # Format sources
        sources = [
            SourceInfo(
                content=source.document.content[:500],  # Truncate to 500 chars
                source=source.document.metadata.source,
                subject=source.document.metadata.subject,
                similarity_score=source.similarity_score,
            )
            for source in answer.sources
        ]
        
        # Build response
        response_data = {
            "data": {
                "query_id": str(answer.query_id),
                "answer": answer.answer_text,
                "sources": [s.model_dump() for s in sources],
            },
            "metadata": {
                "latency_ms": answer.latency_ms,
                "timestamp": answer.timestamp.isoformat(),
            },
        }
        
        # Include token usage if available
        if answer.token_usage:
            response_data["metadata"]["token_usage"] = {
                "prompt_tokens": answer.token_usage.prompt_tokens,
                "completion_tokens": answer.token_usage.completion_tokens,
                "total_tokens": answer.token_usage.total_tokens,
            }
        
        logger.info(
            f"Query {query.id} completed successfully in {answer.latency_ms}ms"
        )
        
        return QueryResponse(**response_data)
        
    except NoRelevantDocumentsError as e:
        # Treat "no relevant documents" as a normal (non-error) outcome.
        message = "No relevant information found in knowledge base. Please try rephrasing your question."
        logger.info(
            f"No relevant documents for query {query.id}: threshold={e.threshold} max_similarity={e.max_similarity}"
        )
        return QueryResponse(
            data={
                "query_id": str(query.id),
                "answer": message,
                "sources": [],
            },
            metadata={
                "latency_ms": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "no_relevant_documents": {
                    "threshold": e.threshold,
                    "max_similarity": e.max_similarity,
                },
            },
        )
        
    except QuotaExceededError as e:
        logger.error(f"Quota exceeded: {e.message}")
        source = "local_guard" if "local guard" in e.message.lower() else "gemini"
        error_response = ErrorResponse(
            error=ErrorDetail(
                type="quota_exceeded",
                message=e.message,
                details={"retry_after": e.retry_after, "source": source},
            )
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error_response.model_dump(),
            headers={"Retry-After": str(e.retry_after)},
        )
        
    except ServiceUnavailableError as e:
        logger.error(f"Service unavailable: {e.message}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                type="service_unavailable",
                message=e.message,
            )
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response.model_dump(),
        )

    except HTTPException:
        # Preserve explicit HTTP errors (e.g., manual 400 validation)
        raise
        
    except ValueError as e:
        # Validation errors from Pydantic
        logger.warning(f"Validation error: {e}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                type="validation_error",
                message=str(e),
            )
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.model_dump(),
        )
        
    except Exception as e:
        logger.exception(f"Unexpected error processing query: {e}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                type="internal_error",
                message="An unexpected error occurred",
            )
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
        )

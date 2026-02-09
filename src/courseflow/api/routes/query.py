"""Query endpoint for RAG question answering."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.courseflow.domain.models import Query
from src.courseflow.domain.exceptions import (
    NoRelevantDocumentsError,
    QuotaExceededError,
    ServiceUnavailableError,
    ValidationError as DomainValidationError,
)
from src.courseflow.application.rag_service import RAGService
from src.courseflow.api.dependencies import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["query"])


# Request/Response schemas
class QueryRequest(BaseModel):
    """Request schema for query endpoint."""
    query: str = Field(..., min_length=1, max_length=1000, description="User's question")


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
        # Create Query model (validates input)
        query = Query(text=request.query)
        
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
        logger.warning(f"No relevant documents: {e.message}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                type="no_relevant_documents",
                message=e.message,
                details={
                    "threshold": e.threshold,
                    "max_similarity": e.max_similarity,
                },
            )
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response.model_dump(),
        )
        
    except QuotaExceededError as e:
        logger.error(f"Quota exceeded: {e.message}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                type="quota_exceeded",
                message=e.message,
                details={"retry_after": e.retry_after},
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

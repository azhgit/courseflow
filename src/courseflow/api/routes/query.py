"""Query endpoint for RAG question answering."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from courseflow.api.dependencies import (
    get_conversation_repository,
    get_rag_service,
    get_rate_limiter,
    get_token_counter,
)
from courseflow.domain.exceptions import (
    ConversationNotFoundError,
    ConversationPersistenceError,
    NoRelevantDocumentsError,
    QuotaExceededError,
    ServiceUnavailableError,
)
from courseflow.domain.models import ConversationTurn, Query, StreamingQuery, SSEEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["query"])


# Request/Response schemas
class QueryRequest(BaseModel):
    """Request schema for query endpoint."""

    query: str = Field(..., description="User's question")
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation ID for multi-turn context (UUID4 format)",
    )
    subject: str | None = Field(
        default=None,
        description="Optional subject filter (e.g., biology, history)",
    )


class SourceInfo(BaseModel):
    """Source document information in response."""

    content: str
    source: str
    subject: str
    similarity_score: float


class QueryResponse(BaseModel):
    """Response schema for successful query."""

    data: dict[str, Any]
    metadata: dict[str, Any]


class ErrorDetail(BaseModel):
    """Error details in error response."""

    type: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


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
    rag_service: Any = Depends(get_rag_service),
    rate_limiter: Any = Depends(get_rate_limiter),
    conversation_repo: Any = Depends(get_conversation_repository),
    token_counter: Any = Depends(get_token_counter),
) -> QueryResponse:
    """Handle POST /api/v1/query requests.

    Accepts a user question, performs RAG retrieval and generation,
    and returns an AI-generated answer with source attribution.
    Supports multi-turn conversations via optional conversation_id.

    Args:
        request: Query request with user's question and optional conversation_id
        rag_service: Injected RAG service dependency
        rate_limiter: Injected rate limiter dependency
        conversation_repo: Injected conversation repository dependency
        token_counter: Injected token counter dependency

    Returns:
        JSON response with answer, sources, metadata, and conversation_id

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
            logger.warning(f"Local rate limit exceeded; retry_after={retry_after}s")
            raise QuotaExceededError(
                message="Rate limit exceeded (local guard)",
                retry_after=retry_after,
            )

        logger.info(f"Received query: {query.id} - '{query.text[:50]}...'")

        # === CONVERSATION MANAGEMENT ===
        conversation_id: str
        conversation_history: str | None = None

        if request.conversation_id is None:
            # Create new conversation (repository generates UUID and timestamp)
            new_conversation = await conversation_repo.create_conversation()
            conversation_id = str(new_conversation.id)
            logger.info(f"Created new conversation: {conversation_id}")
        else:
            # Validate existing conversation
            conversation_id = request.conversation_id
            exists = await conversation_repo.conversation_exists(conversation_id)
            if not exists:
                logger.warning(f"Conversation not found: {conversation_id}")
                raise ConversationNotFoundError(conversation_id=conversation_id)

            # Fetch conversation history
            turn_history = await conversation_repo.get_history(
                conversation_id=conversation_id,
                max_tokens=2000,  # Budget for history
                max_count=5,  # Last 5 turns
            )
            conversation_history = turn_history.to_llm_context() if turn_history.turns else None
            if conversation_history:
                logger.info(
                    f"Loaded {len(turn_history.turns)} turns "
                    f"({turn_history.total_tokens} tokens) for conversation {conversation_id}"
                )

        # Save user turn before RAG (so we have it even if RAG fails)
        user_turn = ConversationTurn(
            conversation_id=conversation_id,
            role="user",
            content=query_text,
            token_count=token_counter.count_tokens(query_text),
        )
        await conversation_repo.add_turn(user_turn)
        logger.debug(f"Saved user turn ({user_turn.token_count} tokens)")

        # === RAG PIPELINE (with conversation history) ===
        # Execute RAG pipeline with optional subject filtering and conversation history.
        answer = await rag_service.answer_query(
            query,
            subject=request.subject,
            conversation_history=conversation_history,
        )

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

        # Save assistant turn after successful RAG
        assistant_turn = ConversationTurn(
            conversation_id=conversation_id,
            role="assistant",
            content=answer.answer_text,
            token_count=token_counter.count_tokens(answer.answer_text),
        )
        await conversation_repo.add_turn(assistant_turn)
        logger.debug(f"Saved assistant turn ({assistant_turn.token_count} tokens)")

        # Build response
        response_data = {
            "data": {
                "query_id": str(answer.query_id),
                "answer": answer.answer_text,
                "sources": [s.model_dump() for s in sources],
                "conversation_id": conversation_id,  # Include conversation_id in response
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

        logger.info(f"Query {query.id} completed successfully in {answer.latency_ms}ms")

        return QueryResponse(**response_data)

    except NoRelevantDocumentsError as e:
        # Treat "no relevant documents" as a normal (non-error) outcome.
        # Still save assistant turn and return conversation_id.
        message = (
            "No relevant information found in knowledge base. Please try rephrasing your question."
        )
        logger.info(
            f"No relevant documents for query {query.id}: threshold={e.threshold} max_similarity={e.max_similarity}"
        )

        # Save assistant turn with "no docs found" message
        assistant_turn = ConversationTurn(
            conversation_id=conversation_id,
            role="assistant",
            content=message,
            token_count=token_counter.count_tokens(message),
        )
        await conversation_repo.add_turn(assistant_turn)

        return QueryResponse(
            data={
                "query_id": str(query.id),
                "answer": message,
                "sources": [],
                "conversation_id": conversation_id,
            },
            metadata={
                "latency_ms": 0,
                "timestamp": datetime.now(UTC).isoformat(),
                "no_relevant_documents": {
                    "threshold": e.threshold,
                    "max_similarity": e.max_similarity,
                },
            },
        )

    except ConversationNotFoundError as e:
        logger.warning(f"Conversation not found: {e.conversation_id}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                type="conversation_not_found",
                message=str(e),  # Use exception's built-in message
                details={"conversation_id": e.conversation_id},
            )
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response.model_dump(),
        )

    except ConversationPersistenceError as e:
        logger.error(f"Conversation persistence error: {e.reason}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                type="conversation_persistence_error",
                message="Failed to save conversation data. Please try again.",
                details={"reason": e.reason},
            )
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response.model_dump(),
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


@router.post(
    "/query/stream",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Server-Sent Events stream with answer chunks"},
        400: {"description": "Validation error (empty query, too long, etc.)"},
        404: {"description": "No relevant documents found"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Service unavailable"},
    },
)
async def stream_query_endpoint(
    request: QueryRequest,
    rag_service: Any = Depends(get_rag_service),
    rate_limiter: Any = Depends(get_rate_limiter),
    conversation_repo: Any = Depends(get_conversation_repository),
) -> StreamingResponse:
    """Handle POST /api/v1/query/stream requests.

    Accepts a user question and streams answer chunks via Server-Sent Events (SSE).
    Events include: chunk, sources, done, error.
    Supports multi-turn conversations via optional conversation_id.

    Args:
        request: Query request with user's question and optional conversation_id
        rag_service: Injected RAG service dependency
        rate_limiter: Injected rate limiter dependency
        conversation_repo: Injected conversation repository dependency

    Returns:
        SSE stream with answer chunks and metadata

    Raises:
        HTTPException: With appropriate status code for errors (as SSE events)
    """

    async def generate_sse_stream():
        """Generator function that yields SSE-formatted events."""
        try:
            # === REQUEST VALIDATION ===
            query_text = request.query.strip() if request.query is not None else ""
            if not query_text:
                error_event = SSEEvent.failure(
                    error="validation_error",
                    message="query must not be empty",
                )
                yield error_event.to_sse()
                return

            if len(query_text) > 1000:
                error_event = SSEEvent.failure(
                    error="validation_error",
                    message="query must be <= 1000 characters",
                )
                yield error_event.to_sse()
                return

            # Create StreamingQuery model
            streaming_query = StreamingQuery(
                query=query_text,
                conversation_id=request.conversation_id,
            )

            # === RATE LIMITING ===
            allowed, retry_after = rate_limiter.is_allowed()
            if not allowed:
                logger.warning(f"Rate limit exceeded; retry_after={retry_after}s")
                error_event = SSEEvent.failure(
                    error="rate_limit_exceeded",
                    message=f"Rate limit exceeded. Retry after {retry_after}s.",
                )
                yield error_event.to_sse()
                return

            logger.info(f"Streaming query: {streaming_query.query[:50]}...")

            # === CONVERSATION MANAGEMENT ===
            conversation_id: str
            conversation_history: str | None = None

            if streaming_query.conversation_id is None:
                # Create new conversation
                new_conversation = await conversation_repo.create_conversation()
                conversation_id = str(new_conversation.id)
                logger.info(f"Created new conversation: {conversation_id}")
            else:
                # Validate existing conversation
                conversation_id = streaming_query.conversation_id
                exists = await conversation_repo.conversation_exists(conversation_id)
                if not exists:
                    logger.warning(f"Conversation not found: {conversation_id}")
                    error_event = SSEEvent.failure(
                        error="conversation_not_found",
                        message=f"Conversation {conversation_id} not found",
                    )
                    yield error_event.to_sse()
                    return

                # Fetch conversation history (for multi-turn context)
                try:
                    turns = await conversation_repo.get_conversation_turns(
                        conversation_id,
                        limit=5,
                    )
                    conversation_history = "\n".join(
                        [f"Turn {i+1}: {turn.user_query}\nResponse: {turn.ai_response}"
                         for i, turn in enumerate(turns)]
                    )
                except Exception as e:
                    logger.warning(f"Failed to fetch conversation history: {e}")

            # === STREAMING GENERATION ===
            try:
                # Track chunks and sources for logging
                all_chunks = []
                all_sources = []

                # Stream from RAG service
                async for chunk_text, source_names in rag_service.stream_query(
                    query=Query(text=streaming_query.query),
                    subject=request.subject,
                    conversation_history=conversation_history,
                ):
                    # Yield chunk event
                    chunk_event = SSEEvent.chunk(chunk_text)
                    yield chunk_event.to_sse()

                    all_chunks.append(chunk_text)
                    if source_names:
                        all_sources = source_names

                # Yield sources event (after generation completes)
                sources_event = SSEEvent.with_sources(
                    sources=all_sources,
                    retrieval_count=len(all_sources),
                )
                yield sources_event.to_sse()

                # Yield done event with conversation_id and token count
                full_response = "".join(all_chunks)
                token_count = len(full_response.split())

                done_event = SSEEvent.done(
                    conversation_id=conversation_id,
                    token_count=token_count,
                )
                yield done_event.to_sse()

                logger.info(f"Streaming completed for query {conversation_id}")

                # === CONVERSATION PERSISTENCE ===
                try:
                    turn = ConversationTurn(
                        conversation_id=conversation_id,
                        user_query=streaming_query.query,
                        ai_response=full_response,
                        token_count=token_count,
                    )
                    await conversation_repo.save_turn(turn)
                    logger.debug(f"Saved conversation turn: {conversation_id}")
                except Exception as e:
                    logger.error(f"Failed to save conversation turn: {e}")

            except NoRelevantDocumentsError as e:
                logger.warning(f"No relevant documents: {e}")
                error_event = SSEEvent.failure(
                    error="no_relevant_documents",
                    message=e.message,
                )
                yield error_event.to_sse()

            except QuotaExceededError as e:
                logger.error(f"Quota exceeded: {e}")
                error_event = SSEEvent.failure(
                    error="rate_limit_exceeded",
                    message=e.message,
                )
                yield error_event.to_sse()

            except ServiceUnavailableError as e:
                logger.error(f"Service unavailable: {e}")
                error_event = SSEEvent.failure(
                    error="service_unavailable",
                    message=e.message,
                )
                yield error_event.to_sse()

            except Exception as e:
                logger.exception(f"Unexpected streaming error: {e}")
                error_event = SSEEvent.failure(
                    error="internal_error",
                    message="An unexpected error occurred during streaming",
                )
                yield error_event.to_sse()

        except Exception as e:
            logger.exception(f"Critical streaming error: {e}")
            error_event = SSEEvent.failure(
                error="internal_error",
                message="Critical streaming error",
            )
            yield error_event.to_sse()

    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

"""Document ingestion endpoint and schemas."""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from courseflow.api.dependencies import get_ingestion_service
from courseflow.application.ingestion_service import IngestionService
from courseflow.domain.exceptions import (
    EmptyContentError,
    FileSizeExceededError,
    IngestionFailedError,
    InvalidFileFormatError,
    QueueFullError,
    QuotaExceededError,
    RateLimitExceededError,
    ServiceUnavailableError,
    SubjectNotFoundError,
)

router = APIRouter(prefix="/api/v1", tags=["ingestion"])
logger = logging.getLogger(__name__)


class IngestMetadata(BaseModel):
    """Optional metadata provided with document uploads."""

    subject: str = Field(default="general", description="Subject slug (e.g., biology, programming). Defaults to 'general' if not provided.")
    difficulty: str | None = Field(default=None, description="Optional difficulty label")


class IngestSuccessData(BaseModel):
    """Success payload for new ingestion."""

    document_id: str
    filename: str
    chunks_created: int
    subject: str
    ingestion_time_ms: int


class IngestSkippedData(BaseModel):
    """Success payload for duplicate ingestion skip."""

    document_id: str
    filename: str
    chunks_created: int = 0
    skipped: bool = True
    reason: str


class ResponseMeta(BaseModel):
    """Common response metadata."""

    request_id: str
    timestamp: str


class IngestSuccessResponse(BaseModel):
    """Generic successful ingestion response envelope."""

    success: bool = True
    data: IngestSuccessData | IngestSkippedData
    metadata: ResponseMeta


class IngestErrorResponse(BaseModel):
    """Validation or system error response envelope."""

    success: bool = False
    error: str
    message: str
    details: dict[str, Any] | None = None


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf"}
ALLOWED_MIME_TYPES = {
    ".md": {"text/markdown", "text/plain"},
    ".markdown": {"text/markdown", "text/plain"},
    ".txt": {"text/plain"},
    ".pdf": {"application/pdf"},
}


def _sanitize_filename(filename: str) -> str:
    cleaned = os.path.basename(filename).strip()
    if not cleaned:
        raise InvalidFileFormatError("Missing filename")
    if re.search(r"[\x00-\x1f]", cleaned):
        raise InvalidFileFormatError("Filename contains invalid characters")
    return cleaned


def _sanitize_subject(subject: str) -> str:
    normalized = subject.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9\-_]{0,49}", normalized):
        raise InvalidFileFormatError("Invalid subject format")
    return normalized


def _validate_file_type(filename: str, content_type: str | None) -> None:
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileFormatError("Unsupported file type. Accepted: .md, .txt, .pdf")
    if content_type:
        allowed = ALLOWED_MIME_TYPES.get(ext, set())
        if content_type not in allowed:
            raise InvalidFileFormatError(f"Unsupported MIME type: {content_type}")


@router.post(
    "/ingest",
    response_model=IngestSuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Document ingestion completed (or skipped as duplicate)"},
        400: {"description": "Validation error"},
        429: {"description": "Embedding quota exceeded"},
        503: {"description": "Service temporarily unavailable"},
    },
)
async def ingest_document(
    file: UploadFile = File(...),
    metadata: str = Form(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    request_id = f"req_{uuid4().hex[:12]}"
    try:
        meta = IngestMetadata.model_validate_json(metadata)
        meta.subject = _sanitize_subject(meta.subject)

        filename = _sanitize_filename(file.filename or "")
        _validate_file_type(filename, file.content_type)
        file_bytes = await file.read()

        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise FileSizeExceededError(
                message=f"File size exceeds {MAX_UPLOAD_BYTES} bytes",
                file_size=len(file_bytes),
                max_size=MAX_UPLOAD_BYTES,
            )

        result = await ingestion_service.ingest_document(
            file_bytes=file_bytes,
            filename=filename,
            subject=meta.subject,
            request_id=request_id,
        )

        response_meta = ResponseMeta(
            request_id=request_id,
            timestamp=datetime.now(UTC).isoformat(),
        )
        if result.skipped:
            logger.info(
                "ingest_skipped request_id=%s filename=%s subject=%s reason=duplicate",
                request_id,
                filename,
                meta.subject,
            )
            return IngestSuccessResponse(
                data=IngestSkippedData(
                    document_id=result.document_id,
                    filename=result.filename,
                    chunks_created=0,
                    skipped=True,
                    reason="Document already indexed",
                ),
                metadata=response_meta,
            )

        logger.info(
            "ingest_success request_id=%s filename=%s subject=%s chunks_created=%s ingestion_time_ms=%s",
            request_id,
            filename,
            meta.subject,
            result.chunks_created,
            result.ingestion_time_ms,
        )
        return IngestSuccessResponse(
            data=IngestSuccessData(
                document_id=result.document_id,
                filename=result.filename,
                chunks_created=result.chunks_created,
                subject=meta.subject,
                ingestion_time_ms=result.ingestion_time_ms,
            ),
            metadata=response_meta,
        )

    except (InvalidFileFormatError, FileSizeExceededError, EmptyContentError, SubjectNotFoundError) as e:
        logger.warning("ingest_validation_error request_id=%s message=%s", request_id, str(e))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=IngestErrorResponse(
                error="validation_error",
                message=str(e),
            ).model_dump(),
        )
    except QueueFullError as e:
        logger.warning("ingest_queue_full request_id=%s message=%s", request_id, e.message)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=IngestErrorResponse(
                error="queue_full",
                message=e.message or "System overloaded. Too many requests in queue.",
                details={"retry_after": e.retry_after or 60},
            ).model_dump(),
            headers={"Retry-After": str(e.retry_after or 60)},
        )
    except (RateLimitExceededError, IngestionFailedError) as e:
        retry_count = getattr(e, "retry_count", 5)
        logger.error(
            "ingest_failed request_id=%s retry_count=%s message=%s",
            request_id,
            retry_count,
            str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=IngestErrorResponse(
                error="ingestion_failed",
                message=str(e),
                details={"retry_count": retry_count, "last_error": getattr(e, "last_error", "")},
            ).model_dump(),
        )
    except QuotaExceededError as e:
        logger.warning("ingest_quota_exceeded request_id=%s retry_after=%s", request_id, e.retry_after)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=IngestErrorResponse(
                error="quota_exceeded",
                message=e.message,
                details={"retry_after": e.retry_after},
            ).model_dump(),
            headers={"Retry-After": str(e.retry_after)},
        )
    except ServiceUnavailableError as e:
        logger.error("ingest_service_unavailable request_id=%s message=%s", request_id, e.message)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=IngestErrorResponse(
                error="service_unavailable",
                message=e.message,
            ).model_dump(),
        )

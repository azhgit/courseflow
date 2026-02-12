"""Documents listing endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from courseflow.api.dependencies import get_document_repository
from courseflow.infrastructure.repositories.document_repo import SQLiteDocumentRepository

router = APIRouter(prefix="/api/v1", tags=["documents"])


class DocumentsResponse(BaseModel):
    success: bool = True
    data: list[dict[str, Any]]


@router.get(
    "/documents",
    response_model=DocumentsResponse,
    status_code=status.HTTP_200_OK,
)
async def list_documents(
    subject: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    document_repo: SQLiteDocumentRepository = Depends(get_document_repository),
) -> DocumentsResponse:
    docs = await document_repo.list_all(subject=subject, limit=limit)
    return DocumentsResponse(
        data=[
            {
                "id": d.id,
                "filename": d.filename,
                "subject": d.subject,
                "file_format": d.file_format,
                "chunks_created": d.chunks_created,
                "ingestion_time_ms": d.ingestion_time_ms,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]
    )


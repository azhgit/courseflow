"""Subjects listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from courseflow.api.dependencies import get_subject_repository
from courseflow.infrastructure.repositories.subject_repo import SQLiteSubjectRepository

router = APIRouter(prefix="/api/v1", tags=["subjects"])


class SubjectItem(BaseModel):
    id: str
    name: str
    display_name: str


class SubjectsResponse(BaseModel):
    success: bool = True
    data: list[SubjectItem]


@router.get(
    "/subjects",
    response_model=SubjectsResponse,
    status_code=status.HTTP_200_OK,
)
async def list_subjects(
    subject_repo: SQLiteSubjectRepository = Depends(get_subject_repository),
) -> SubjectsResponse:
    subjects = await subject_repo.find_all()
    return SubjectsResponse(
        data=[
            SubjectItem(id=s.id, name=s.name, display_name=s.display_name)
            for s in subjects
        ]
    )


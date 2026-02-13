"""SQLite document repository implementing DocumentRepositoryPort."""

import sqlite3

import aiosqlite

from courseflow.config import settings
from courseflow.domain.exceptions import DuplicateDocumentError, ServiceUnavailableError
from courseflow.domain.models import IngestionDocument
from courseflow.domain.ports import DocumentRepositoryPort


class SQLiteDocumentRepository(DocumentRepositoryPort):
    """Async SQLite repository for ingested document metadata."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or settings.database_path

    async def initialize(self) -> None:
        """Ensure documents table exists."""
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        content_hash TEXT UNIQUE NOT NULL,
                        file_format TEXT NOT NULL,
                        file_size_bytes INTEGER NOT NULL,
                        chunks_created INTEGER NOT NULL DEFAULT 0,
                        ingestion_time_ms INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                await db.execute(
                    """CREATE INDEX IF NOT EXISTS idx_documents_subject ON documents(subject)"""
                )
                await db.execute(
                    """CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at)"""
                )
                await db.commit()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to initialize documents table: {str(e)}") from e

    async def save_document(self, document: IngestionDocument) -> None:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    """
                    INSERT INTO documents (
                        id, filename, subject, content_hash, file_format, file_size_bytes,
                        chunks_created, ingestion_time_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.id,
                        document.filename,
                        document.subject,
                        document.content_hash,
                        document.file_format,
                        int(document.file_size_bytes),
                        int(document.chunks_created),
                        int(document.ingestion_time_ms),
                        document.created_at.isoformat(),
                    ),
                )
                await db.commit()
        except sqlite3.IntegrityError as e:
            # Unique constraint violation on content_hash
            raise DuplicateDocumentError(
                message="Document already indexed",
                content_hash=document.content_hash,
                existing_document_id="",
            ) from e
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to save document: {str(e)}") from e

    async def find_by_content_hash(self, content_hash: str) -> IngestionDocument | None:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute(
                    """
                    SELECT id, filename, subject, content_hash, file_format, file_size_bytes,
                           chunks_created, ingestion_time_ms, created_at
                    FROM documents
                    WHERE content_hash = ?
                    """,
                    (content_hash,),
                ) as cur:
                    row = await cur.fetchone()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to find document: {str(e)}") from e

        return _row_to_document(row)

    async def find_by_id(self, document_id: str) -> IngestionDocument | None:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute(
                    """
                    SELECT id, filename, subject, content_hash, file_format, file_size_bytes,
                           chunks_created, ingestion_time_ms, created_at
                    FROM documents
                    WHERE id = ?
                    """,
                    (document_id,),
                ) as cur:
                    row = await cur.fetchone()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to find document by id: {str(e)}") from e

        return _row_to_document(row)

    async def list_all(
        self, subject: str | None = None, limit: int = 100
    ) -> list[IngestionDocument]:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                if subject:
                    query = """
                        SELECT id, filename, subject, content_hash, file_format, file_size_bytes,
                               chunks_created, ingestion_time_ms, created_at
                        FROM documents
                        WHERE subject = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """
                    params = (subject, int(limit))
                else:
                    query = """
                        SELECT id, filename, subject, content_hash, file_format, file_size_bytes,
                               chunks_created, ingestion_time_ms, created_at
                        FROM documents
                        ORDER BY created_at DESC
                        LIMIT ?
                    """
                    params = (int(limit),)

                async with db.execute(query, params) as cur:
                    rows = await cur.fetchall()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to list documents: {str(e)}") from e

        return [doc for row in rows if (doc := _row_to_document(row)) is not None]


def _row_to_document(row: tuple[object, ...] | None) -> IngestionDocument | None:
    if not row:
        return None
    return IngestionDocument(
        id=str(row[0]),
        filename=str(row[1]),
        subject=str(row[2]),
        content_hash=str(row[3]),
        file_format=str(row[4]),
        file_size_bytes=int(row[5]),
        chunks_created=int(row[6]),
        ingestion_time_ms=int(row[7]),
        created_at=str(row[8]),
    )

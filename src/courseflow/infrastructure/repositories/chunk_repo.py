"""SQLite + ChromaDB chunk repository implementing ChunkRepositoryPort."""

from __future__ import annotations

import sqlite3

import aiosqlite
import chromadb
from chromadb.config import Settings as ChromaSettings

from courseflow.config import settings
from courseflow.domain.exceptions import ServiceUnavailableError
from courseflow.domain.models import Chunk, Document, DocumentMetadata
from courseflow.domain.ports import ChunkRepositoryPort


class SQLiteChromaChunkRepository(ChunkRepositoryPort):
    """Persist chunks in SQLite and embeddings in ChromaDB."""

    def __init__(
        self,
        db_path: str | None = None,
        chroma_persist_dir: str = settings.CHROMA_PERSIST_DIR,
        collection_name: str = settings.CHROMA_COLLECTION_NAME,
    ):
        self._db_path = db_path or settings.database_path
        self._chroma = chromadb.PersistentClient(
            path=chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        self._collection = self._chroma.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    async def save_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.executemany(
                    """
                    INSERT INTO chunks (
                        id, document_id, chunk_index, text, token_count, source_filename, subject
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            c.id,
                            c.document_id,
                            int(c.chunk_index),
                            c.text,
                            int(c.token_count),
                            c.source_filename,
                            c.subject,
                        )
                        for c in chunks
                    ],
                )
                await db.commit()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to save chunks to SQLite: {str(e)}") from e

        # Save to vector store
        try:
            documents: list[Document] = []
            total_chunks = len(chunks)
            for c in chunks:
                if c.embedding is None:
                    raise ServiceUnavailableError("Chunk embedding missing; cannot index in vector store")

                documents.append(
                    Document(
                        id=c.id,
                        content=c.text,
                        embedding=c.embedding,
                        metadata=DocumentMetadata(
                            source=c.source_filename,
                            subject=c.subject,
                            chunk_index=int(c.chunk_index),
                            total_chunks=total_chunks,
                        ),
                    )
                )

            self._collection.add(
                ids=[d.id for d in documents],
                documents=[d.content for d in documents],
                embeddings=[d.embedding for d in documents],  # type: ignore[arg-type]
                metadatas=[
                    {
                        "source": d.metadata.source,
                        "subject": d.metadata.subject,
                        "chunk_index": d.metadata.chunk_index,
                        "total_chunks": d.metadata.total_chunks,
                    }
                    for d in documents
                ],
            )
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to save chunks to ChromaDB: {str(e)}") from e

    async def delete_chunks_by_document_id(self, document_id: str) -> None:
        # Read chunk IDs for vector-store cleanup.
        chunk_ids: list[str] = []
        try:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute(
                    "SELECT id FROM chunks WHERE document_id = ?",
                    (document_id,),
                ) as cur:
                    rows = await cur.fetchall()
                    chunk_ids = [str(r[0]) for r in rows]

                await db.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                await db.commit()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to delete chunks: {str(e)}") from e

        if chunk_ids:
            try:
                self._collection.delete(ids=chunk_ids)
            except Exception as e:
                raise ServiceUnavailableError(f"Failed to delete chunks from ChromaDB: {str(e)}") from e

    async def find_chunks_by_document_id(self, document_id: str) -> list[Chunk]:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute(
                    """
                    SELECT id, document_id, chunk_index, text, token_count, source_filename, subject
                    FROM chunks
                    WHERE document_id = ?
                    ORDER BY chunk_index
                    """,
                    (document_id,),
                ) as cur:
                    rows = await cur.fetchall()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to read chunks: {str(e)}") from e

        return [
            Chunk(
                id=str(r[0]),
                document_id=str(r[1]),
                chunk_index=int(r[2]),
                text=str(r[3]),
                token_count=int(r[4]),
                source_filename=str(r[5]),
                subject=str(r[6]),
            )
            for r in rows
        ]

    async def query(self, subject: str | None = None, limit: int = 100) -> list[Chunk]:
        """Query chunks from SQLite with optional subject filtering.

        This helper supports subject-filtered retrieval paths used by ingestion/query integration.
        """
        try:
            async with aiosqlite.connect(self._db_path) as db:
                if subject:
                    sql = """
                        SELECT id, document_id, chunk_index, text, token_count, source_filename, subject
                        FROM chunks
                        WHERE subject = ?
                        ORDER BY rowid DESC
                        LIMIT ?
                    """
                    params = (subject, int(limit))
                else:
                    sql = """
                        SELECT id, document_id, chunk_index, text, token_count, source_filename, subject
                        FROM chunks
                        ORDER BY rowid DESC
                        LIMIT ?
                    """
                    params = (int(limit),)

                async with db.execute(sql, params) as cur:
                    rows = await cur.fetchall()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to query chunks: {str(e)}") from e

        return [
            Chunk(
                id=str(r[0]),
                document_id=str(r[1]),
                chunk_index=int(r[2]),
                text=str(r[3]),
                token_count=int(r[4]),
                source_filename=str(r[5]),
                subject=str(r[6]),
            )
            for r in rows
        ]

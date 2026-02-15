"""Document ingestion orchestration service."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from courseflow.domain.exceptions import (
    EmptyContentError,
    IngestionFailedError,
    InvalidFileFormatError,
    RateLimitExceededError,
    SubjectNotFoundError,
)
from courseflow.domain.models import Chunk, IngestionDocument, IngestionResult
from courseflow.domain.ports import (
    ChunkerPort,
    ChunkRepositoryPort,
    DocumentRepositoryPort,
    EmbeddingPort,
    PDFExtractorPort,
    SentenceTokenizerPort,
    SubjectRepositoryPort,
    TokenCounterPort,
)
from courseflow.infrastructure.rate_limiting import RateLimiter, retry_with_backoff

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates ingestion: extract -> chunk -> embed -> persist."""

    def __init__(
        self,
        pdf_extractor: PDFExtractorPort,
        token_counter: TokenCounterPort,
        sentence_tokenizer: SentenceTokenizerPort,
        chunker: ChunkerPort,
        embedding_port: EmbeddingPort,
        subject_repo: SubjectRepositoryPort,
        document_repo: DocumentRepositoryPort,
        chunk_repo: ChunkRepositoryPort,
        rate_limiter: RateLimiter | None = None,
        embedding_batch_size: int = 5,
    ):
        self._pdf_extractor = pdf_extractor
        self._token_counter = token_counter
        self._sentence_tokenizer = sentence_tokenizer
        self._chunker = chunker
        self._embedding_port = embedding_port
        self._subject_repo = subject_repo
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._rate_limiter = rate_limiter or RateLimiter()
        self._embedding_batch_size = embedding_batch_size

    async def ingest_document(
        self, file_bytes: bytes, filename: str, subject: str, request_id: str | None = None
    ) -> IngestionResult:
        start = time.time()
        request_id = request_id or f"{filename}_{int(time.time())}"

        if not await self._subject_repo.subject_exists(subject):
            raise SubjectNotFoundError(f"Unknown subject: {subject}", subject=subject)

        text = await self._extract_text(file_bytes=file_bytes, filename=filename)
        if not text.strip():
            raise EmptyContentError("Document content is empty after extraction")

        content_hash = IngestionDocument.compute_content_hash(text)
        existing = await self._document_repo.find_by_content_hash(content_hash)
        if existing:
            logger.info(f"Document {filename} already exists (hash={content_hash[:8]}...)")
            return IngestionResult(
                document_id=existing.id,
                filename=filename,
                success=True,
                chunks_created=0,
                ingestion_time_ms=int((time.time() - start) * 1000),
                skipped=True,
            )

        file_format = _detect_file_format(filename)
        document = IngestionDocument(
            filename=filename,
            subject=subject,
            content_hash=content_hash,
            file_format=file_format,
            file_size_bytes=len(file_bytes),
            chunks_created=0,
            ingestion_time_ms=0,
        )

        chunks = self._chunker.create_chunks(
            text=text,
            document_id=document.id,
            source_filename=filename,
            subject=subject,
        )

        logger.info(
            f"Processing {len(chunks)} chunks for document {filename} (request_id={request_id})"
        )

        # Generate embeddings with retry logic and rate limiting
        embedded_chunks: list[Chunk] = []
        try:
            for batch_start in range(0, len(chunks), self._embedding_batch_size):
                batch = chunks[batch_start : batch_start + self._embedding_batch_size]
                tasks = [
                    self._generate_embedding_with_retry(
                        chunk=chunk,
                        request_id=request_id,
                        chunk_idx=batch_start + idx,
                    )
                    for idx, chunk in enumerate(batch)
                ]
                embeddings = await asyncio.gather(*tasks)
                for chunk, embedding in zip(batch, embeddings, strict=False):
                    embedded_chunks.append(chunk.model_copy(update={"embedding": embedding}))
        except RateLimitExceededError as e:
            logger.error(
                f"Rate limit exceeded for document {filename} after retries "
                f"(request_id={request_id}): {e}"
            )
            raise IngestionFailedError(
                message=f"Ingestion failed after {e.retry_count if hasattr(e, 'retry_count') else 5} retries. "
                f"Rate limit exceeded. Try again later.",
                document_id=document.id,
                retry_count=5,
                last_error=str(e),
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error during embedding generation for {filename} "
                f"(request_id={request_id}): {e}"
            )
            raise IngestionFailedError(
                message=f"Ingestion failed: {str(e)}",
                document_id=document.id,
                retry_count=0,
                last_error=str(e),
            ) from e

        document.chunks_created = len(embedded_chunks)
        document.ingestion_time_ms = int((time.time() - start) * 1000)

        # Persist document and chunks with rollback on failure
        await self._document_repo.save_document(document)
        try:
            await self._chunk_repo.save_chunks(embedded_chunks)
            logger.info(
                f"Successfully ingested {filename}: {len(embedded_chunks)} chunks "
                f"in {document.ingestion_time_ms}ms (request_id={request_id})"
            )
        except Exception as e:
            logger.error(
                f"Failed to save chunks for {filename}, rolling back (request_id={request_id}): {e}"
            )
            await self._chunk_repo.delete_chunks_by_document_id(document.id)
            raise

        return IngestionResult(
            document_id=document.id,
            filename=filename,
            success=True,
            chunks_created=len(embedded_chunks),
            ingestion_time_ms=document.ingestion_time_ms,
            skipped=False,
        )

    async def _extract_text(self, file_bytes: bytes, filename: str) -> str:
        file_format = _detect_file_format(filename)
        if file_format == "pdf":
            return await self._pdf_extractor.extract_text(file_bytes=file_bytes, filename=filename)
        return file_bytes.decode("utf-8", errors="ignore")

    async def _generate_embedding_with_retry(
        self, chunk: Chunk, request_id: str, chunk_idx: int
    ) -> list[float]:
        """Generate embedding with rate limiting and retry logic.

        Args:
            chunk: Chunk to generate embedding for
            request_id: Request identifier for logging
            chunk_idx: Chunk index for logging

        Returns:
            Embedding vector

        Raises:
            RateLimitExceededError: If retries exhausted
        """

        async def _generate() -> list[float]:
            async with self._rate_limiter.acquire(request_id=f"{request_id}_chunk_{chunk_idx}"):
                return await self._embedding_port.generate_embedding(chunk.text)

        try:
            return await retry_with_backoff(
                _generate,
                max_retries=5,
                initial_delay=1.0,
                backoff_multiplier=2.0,
                request_id=f"{request_id}_chunk_{chunk_idx}",
            )
        except RateLimitExceededError:
            logger.warning(f"Retry exhausted for chunk {chunk_idx} (request_id={request_id})")
            raise


def _detect_file_format(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".pdf":
        return "pdf"
    if ext == ".txt":
        return "txt"
    if ext in {".md", ".markdown"}:
        return "markdown"
    raise InvalidFileFormatError("Unsupported file type. Accepted: .md, .txt, .pdf")

"""Integration tests for duplicate detection during document ingestion.

Tests verify:
- T041: Duplicate detection when same file uploaded twice
- T042: Same filename but different content treated as new document
- T043: Concurrent upload handling (race condition scenarios)
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from courseflow.application.ingestion_service import IngestionService
from courseflow.domain.exceptions import DuplicateDocumentError
from courseflow.infrastructure.document_processing.pymupdf_extractor import PyMuPDFExtractor
from courseflow.infrastructure.embeddings.gemini import GeminiEmbeddingClient
from courseflow.infrastructure.repositories.chunk_repo import SQLiteChromaChunkRepository
from courseflow.infrastructure.repositories.document_repo import SQLiteDocumentRepository
from courseflow.infrastructure.repositories.subject_repo import SQLiteSubjectRepository
from courseflow.infrastructure.text_processing.nltk_tokenizer import NLTKSentenceTokenizer
from courseflow.infrastructure.text_processing.sentence_chunker import SentenceChunker
from courseflow.infrastructure.token_counting.tiktoken_counter import TiktokenCounter


@pytest.fixture(scope="function")
def temp_dirs():
    """Create temporary directories for ChromaDB and SQLite."""
    chroma_dir = tempfile.mkdtemp()
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "test_duplicate.db")

    yield chroma_dir, db_path

    shutil.rmtree(chroma_dir, ignore_errors=True)
    shutil.rmtree(db_dir, ignore_errors=True)


@pytest.fixture
async def ingestion_service(temp_dirs):
    """Create IngestionService with isolated test database."""
    chroma_dir, db_path = temp_dirs

    # Initialize database with migration
    import sqlite3

    migration_path = (
        Path(__file__).parent.parent.parent
        / "scripts"
        / "migrations"
        / "002_add_ingestion_tables.sql"
    )
    with open(migration_path) as f:
        migration_sql = f.read()

    conn = sqlite3.connect(db_path)
    conn.executescript(migration_sql)
    conn.close()

    # Create service dependencies
    pdf_extractor = PyMuPDFExtractor()
    token_counter = TiktokenCounter()
    sentence_tokenizer = NLTKSentenceTokenizer()
    chunker = SentenceChunker(
        tokenizer=sentence_tokenizer,
        token_counter=token_counter,
    )
    embedding_port = GeminiEmbeddingClient(api_key=os.getenv("GEMINI_API_KEY", "test-key"))
    subject_repo = SQLiteSubjectRepository(db_path=db_path)
    document_repo = SQLiteDocumentRepository(db_path=db_path)
    chunk_repo = SQLiteChromaChunkRepository(db_path=db_path, chroma_persist_dir=chroma_dir)

    service = IngestionService(
        pdf_extractor=pdf_extractor,
        token_counter=token_counter,
        sentence_tokenizer=sentence_tokenizer,
        chunker=chunker,
        embedding_port=embedding_port,
        subject_repo=subject_repo,
        document_repo=document_repo,
        chunk_repo=chunk_repo,
    )

    return service


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="Requires GEMINI_API_KEY")
async def test_duplicate_file_skipped(ingestion_service):
    """
    T041: Test that uploading the same file twice results in duplicate being skipped.

    Scenario:
    1. Upload document with specific content
    2. Upload same document again
    3. Verify second upload returns success with skipped=True and 0 new chunks
    """
    content = "# Photosynthesis\n\nPhotosynthesis is the process by which plants convert light energy into chemical energy."
    file_bytes = content.encode("utf-8")
    filename = "photosynthesis.md"
    subject = "biology"

    # First upload - should succeed
    result1 = await ingestion_service.ingest_document(
        file_bytes=file_bytes,
        filename=filename,
        subject=subject,
    )

    assert result1.success is True
    assert result1.skipped is False
    assert result1.chunks_created > 0
    first_document_id = result1.document_id

    # Second upload - should be skipped
    result2 = await ingestion_service.ingest_document(
        file_bytes=file_bytes,
        filename=filename,
        subject=subject,
    )

    assert result2.success is True
    assert result2.skipped is True, "Second upload should be marked as skipped"
    assert result2.chunks_created == 0, "No new chunks should be created for duplicate"
    assert result2.document_id == first_document_id, "Should return original document ID"


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="Requires GEMINI_API_KEY")
async def test_same_filename_different_content_not_duplicate(ingestion_service):
    """
    T042: Test that same filename with different content is treated as new document.

    Scenario:
    1. Upload document "notes.txt" with content A
    2. Upload document "notes.txt" with content B (different)
    3. Verify second upload creates new document with new chunks
    """
    filename = "notes.txt"
    subject = "general"

    # First upload
    content1 = "Version 1: This is the original content about cells."
    result1 = await ingestion_service.ingest_document(
        file_bytes=content1.encode("utf-8"),
        filename=filename,
        subject=subject,
    )

    assert result1.success is True
    assert result1.skipped is False

    # Second upload with different content but same filename
    content2 = "Version 2: This is completely different content about molecules and atoms."
    result2 = await ingestion_service.ingest_document(
        file_bytes=content2.encode("utf-8"),
        filename=filename,
        subject=subject,
    )

    assert result2.success is True
    assert result2.skipped is False, "Different content should not be skipped"
    assert result2.chunks_created > 0, "New chunks should be created"
    assert result2.document_id != result1.document_id, "Should create new document ID"


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="Requires GEMINI_API_KEY")
async def test_concurrent_upload_handling(ingestion_service):
    """
    T043: Test concurrent uploads of same file are handled correctly.

    Scenario:
    1. Launch two concurrent uploads of identical content
    2. Verify one succeeds with chunks created
    3. Verify the other either:
       a) Returns skipped=True (detected before save), OR
       b) Raises DuplicateDocumentError (race condition at database)

    Both outcomes are acceptable due to timing uncertainty.
    """
    content = "# Concurrent Upload Test\n\nThis content will be uploaded simultaneously."
    file_bytes = content.encode("utf-8")
    filename = "concurrent_test.md"
    subject = "general"

    # Launch two uploads concurrently
    results = await asyncio.gather(
        ingestion_service.ingest_document(file_bytes, filename, subject),
        ingestion_service.ingest_document(file_bytes, filename, subject),
        return_exceptions=True,
    )

    # At least one should succeed
    successful_results = [r for r in results if not isinstance(r, Exception) and r.success]
    assert len(successful_results) >= 1, "At least one upload should succeed"

    # Check outcomes
    created_count = sum(1 for r in successful_results if not r.skipped)
    skipped_count = sum(1 for r in successful_results if r.skipped)
    error_count = sum(1 for r in results if isinstance(r, DuplicateDocumentError))

    # Exactly one should have created chunks
    assert created_count == 1, f"Exactly one upload should create chunks, got {created_count}"

    # The other should be either skipped or raised DuplicateDocumentError
    assert (skipped_count + error_count) == 1, (
        f"Second upload should be skipped or error, got skipped={skipped_count}, errors={error_count}"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="Requires GEMINI_API_KEY")
async def test_content_normalization_for_duplicate_detection(ingestion_service):
    """
    Additional test: Verify content normalization for duplicate detection.

    Different whitespace/line endings should still be detected as duplicates.
    """
    subject = "general"

    # Upload with Unix line endings
    content1 = "Line 1\nLine 2\nLine 3"
    result1 = await ingestion_service.ingest_document(
        file_bytes=content1.encode("utf-8"),
        filename="test1.txt",
        subject=subject,
    )

    assert result1.success is True
    assert result1.skipped is False

    # Upload with Windows line endings (should be detected as duplicate)
    content2 = "Line 1\r\nLine 2\r\nLine 3"
    result2 = await ingestion_service.ingest_document(
        file_bytes=content2.encode("utf-8"),
        filename="test2.txt",  # Different filename
        subject=subject,
    )

    assert result2.success is True
    assert result2.skipped is True, "Windows line endings should normalize to same hash"
    assert result2.chunks_created == 0


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="Requires GEMINI_API_KEY")
async def test_whitespace_normalization_duplicate_detection(ingestion_service):
    """
    Additional test: Multiple spaces should be normalized to single space.
    """
    subject = "general"

    # Upload with single spaces
    content1 = "The quick brown fox jumps over the lazy dog."
    result1 = await ingestion_service.ingest_document(
        file_bytes=content1.encode("utf-8"),
        filename="fox1.txt",
        subject=subject,
    )

    assert result1.success is True
    assert result1.skipped is False

    # Upload with multiple spaces (should be detected as duplicate)
    content2 = "The  quick   brown    fox     jumps      over       the        lazy         dog."
    result2 = await ingestion_service.ingest_document(
        file_bytes=content2.encode("utf-8"),
        filename="fox2.txt",
        subject=subject,
    )

    assert result2.success is True
    assert result2.skipped is True, "Multiple spaces should normalize to same hash"
    assert result2.chunks_created == 0

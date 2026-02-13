"""End-to-end tests for document ingestion API.

Tests the complete ingestion workflow from file upload through queryability:
- Markdown file ingestion
- PDF file ingestion
- Plain text file ingestion
- Query integration to verify ingested content is searchable
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from courseflow.api.main import create_app

pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Requires GEMINI_API_KEY for end-to-end embedding/query validation",
)


@pytest.fixture(scope="function")
def temp_dirs():
    """Create temporary directories for ChromaDB and SQLite."""
    chroma_dir = tempfile.mkdtemp()
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "test_ingestion.db")

    yield chroma_dir, db_path

    shutil.rmtree(chroma_dir, ignore_errors=True)
    shutil.rmtree(db_dir, ignore_errors=True)


@pytest.fixture
def test_app(temp_dirs, monkeypatch):
    """Create test FastAPI application with isolated database."""
    chroma_dir, db_path = temp_dirs

    # Override settings for testing BEFORE any imports
    monkeypatch.setenv("CHROMA_PERSIST_DIR", chroma_dir)
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "test-key"))

    # Initialize database with migration script
    import sqlite3
    from pathlib import Path

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

    # Create app
    app = create_app()

    # Create test client
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_files():
    """Get paths to sample test files."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "documents"
    return {
        "markdown": fixtures_dir / "sample_biology.md",
        "text": fixtures_dir / "sample_math.txt",
        "pdf": fixtures_dir / "sample_physics.pdf",
    }


class TestMarkdownIngestion:
    """Test markdown file ingestion (T031)."""

    def test_ingest_markdown_success(self, test_app, sample_files):
        """Test successful ingestion of a markdown file.

        Validates:
        - 200 status code
        - Response matches API contract
        - Document ID is returned
        - Chunks are created
        - Ingestion time is recorded
        """
        markdown_path = sample_files["markdown"]
        assert markdown_path.exists(), f"Markdown fixture not found: {markdown_path}"

        with open(markdown_path, "rb") as f:
            response = test_app.post(
                "/api/v1/ingest",
                files={"file": ("sample_biology.md", f, "text/markdown")},
                data={"metadata": json.dumps({"subject": "biology"})},
            )

        # Assert successful response
        assert response.status_code == 200, f"Response: {response.json()}"
        data = response.json()

        # Validate response structure (per API contract)
        assert data["success"] is True
        assert "data" in data
        assert "metadata" in data

        # Validate data payload
        result = data["data"]
        assert "document_id" in result
        assert result["document_id"]  # Not empty
        assert result["filename"] == "sample_biology.md"
        assert result["chunks_created"] > 0  # At least one chunk
        assert result["subject"] == "biology"
        assert result["ingestion_time_ms"] > 0

        # Validate metadata
        metadata = data["metadata"]
        assert "request_id" in metadata
        assert "timestamp" in metadata

    def test_ingest_markdown_duplicate_detection(self, test_app, sample_files):
        """Test that uploading the same markdown file twice is detected as duplicate."""
        markdown_path = sample_files["markdown"]

        # First upload
        with open(markdown_path, "rb") as f:
            response1 = test_app.post(
                "/api/v1/ingest",
                files={"file": ("sample_biology.md", f, "text/markdown")},
                data={"metadata": json.dumps({"subject": "biology"})},
            )
        assert response1.status_code == 200
        data1 = response1.json()
        doc_id_1 = data1["data"]["document_id"]

        # Second upload (same content)
        with open(markdown_path, "rb") as f:
            response2 = test_app.post(
                "/api/v1/ingest",
                files={"file": ("biology_copy.md", f, "text/markdown")},
                data={"metadata": json.dumps({"subject": "biology"})},
            )
        assert response2.status_code == 200
        data2 = response2.json()

        # Should be marked as skipped
        assert data2["success"] is True
        assert data2["data"]["skipped"] is True
        assert data2["data"]["document_id"] == doc_id_1  # Same document
        assert data2["data"]["chunks_created"] == 0  # No new chunks


class TestPDFIngestion:
    """Test PDF file ingestion (T032)."""

    def test_ingest_pdf_success(self, test_app, sample_files):
        """Test successful ingestion of a PDF file.

        Validates:
        - PDF text extraction works
        - Chunks are created from extracted text
        - Response matches API contract
        """
        pdf_path = sample_files["pdf"]
        assert pdf_path.exists(), f"PDF fixture not found: {pdf_path}"

        with open(pdf_path, "rb") as f:
            response = test_app.post(
                "/api/v1/ingest",
                files={"file": ("sample_physics.pdf", f, "application/pdf")},
                data={"metadata": json.dumps({"subject": "physics"})},
            )

        # Assert successful response
        assert response.status_code == 200, f"Response: {response.json()}"
        data = response.json()

        # Validate response
        assert data["success"] is True
        result = data["data"]
        assert result["filename"] == "sample_physics.pdf"
        assert result["chunks_created"] > 0
        assert result["subject"] == "physics"
        assert result["document_id"]

    def test_ingest_pdf_text_extraction_quality(self, test_app, sample_files):
        """Test that PDF text extraction preserves content quality."""
        pdf_path = sample_files["pdf"]

        with open(pdf_path, "rb") as f:
            response = test_app.post(
                "/api/v1/ingest",
                files={"file": ("sample_physics.pdf", f, "application/pdf")},
                data={"metadata": json.dumps({"subject": "physics"})},
            )

        assert response.status_code == 200
        data = response.json()

        # Verify chunks were created (indicates successful text extraction)
        assert data["data"]["chunks_created"] > 0

        # Query to verify content is searchable
        query_response = test_app.post(
            "/api/v1/query",
            json={"query": "Newton's laws of motion", "subject": "physics"},
        )
        assert query_response.status_code == 200
        query_data = query_response.json()

        # Should find relevant content
        assert len(query_data["results"]) > 0
        # At least one result should mention Newton or laws
        found_relevant = any(
            "newton" in result["content"].lower() or "law" in result["content"].lower()
            for result in query_data["results"]
        )
        assert found_relevant, "Expected to find content about Newton's laws"


class TestPlainTextIngestion:
    """Test plain text file ingestion (T033)."""

    def test_ingest_plaintext_success(self, test_app, sample_files):
        """Test successful ingestion of a plain text file.

        Validates:
        - Plain text files are processed correctly
        - Response matches API contract
        - Chunks are created
        """
        text_path = sample_files["text"]
        assert text_path.exists(), f"Text fixture not found: {text_path}"

        with open(text_path, "rb") as f:
            response = test_app.post(
                "/api/v1/ingest",
                files={"file": ("sample_math.txt", f, "text/plain")},
                data={"metadata": json.dumps({"subject": "math"})},
            )

        # Assert successful response
        assert response.status_code == 200, f"Response: {response.json()}"
        data = response.json()

        # Validate response
        assert data["success"] is True
        result = data["data"]
        assert result["filename"] == "sample_math.txt"
        assert result["chunks_created"] > 0
        assert result["subject"] == "math"
        assert result["document_id"]


class TestIngestionValidation:
    """Test input validation and error handling."""

    def test_missing_subject(self, test_app, sample_files):
        """Test that missing subject parameter returns validation error."""
        markdown_path = sample_files["markdown"]

        with open(markdown_path, "rb") as f:
            response = test_app.post(
                "/api/v1/ingest",
                files={"file": ("sample_biology.md", f, "text/markdown")},
                # No subject provided
            )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_invalid_subject(self, test_app, sample_files):
        """Test that non-existent subject returns error."""
        markdown_path = sample_files["markdown"]

        with open(markdown_path, "rb") as f:
            response = test_app.post(
                "/api/v1/ingest",
                files={"file": ("sample_biology.md", f, "text/markdown")},
                data={"metadata": json.dumps({"subject": "nonexistent_subject"})},
            )

        # Should return 400 or 404 error
        assert response.status_code in [400, 404]
        data = response.json()
        assert data["success"] is False

    def test_empty_file(self, test_app, temp_dirs):
        """Test that empty file returns error."""
        # Create empty temporary file
        _, db_path = temp_dirs
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_path = f.name
            # Write nothing (empty file)

        try:
            with open(temp_path, "rb") as f:
                response = test_app.post(
                    "/api/v1/ingest",
                    files={"file": ("empty.txt", f, "text/plain")},
                    data={"metadata": json.dumps({"subject": "math"})},
                )

            # Should return error for empty content
            assert response.status_code in [400, 422]
        finally:
            os.unlink(temp_path)

    def test_unsupported_file_format(self, test_app):
        """Test that unsupported file format returns error."""
        # Create a fake image file
        fake_image_content = b"fake image data"

        response = test_app.post(
            "/api/v1/ingest",
            files={"file": ("image.jpg", fake_image_content, "image/jpeg")},
            data={"metadata": json.dumps({"subject": "biology"})},
        )

        # Should return 400 error
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False


class TestQueryIntegration:
    """Test that ingested content is queryable (T034)."""

    def test_ingested_content_is_queryable(self, test_app, sample_files):
        """Test end-to-end: ingest document, then query it.

        This validates the complete pipeline:
        1. Upload document
        2. Extract text
        3. Create chunks
        4. Generate embeddings
        5. Store in vector database
        6. Query returns relevant results
        """
        # Ingest markdown file about photosynthesis
        markdown_path = sample_files["markdown"]
        with open(markdown_path, "rb") as f:
            ingest_response = test_app.post(
                "/api/v1/ingest",
                files={"file": ("sample_biology.md", f, "text/markdown")},
                data={"metadata": json.dumps({"subject": "biology"})},
            )
        assert ingest_response.status_code == 200

        # Query for content we know is in the document
        query_response = test_app.post(
            "/api/v1/query",
            json={"query": "What is photosynthesis?", "subject": "biology"},
        )

        assert query_response.status_code == 200
        data = query_response.json()

        # Should return results
        assert "results" in data
        assert len(data["results"]) > 0

        # At least one result should be relevant (mention photosynthesis)
        found_relevant = any(
            "photosynthesis" in result["content"].lower() for result in data["results"]
        )
        assert found_relevant, "Expected to find content about photosynthesis"

    def test_subject_filtering_works(self, test_app, sample_files):
        """Test that subject filtering returns only relevant documents."""
        # Ingest documents in different subjects
        with open(sample_files["markdown"], "rb") as f:
            test_app.post(
                "/api/v1/ingest",
                files={"file": ("biology.md", f, "text/markdown")},
                data={"metadata": json.dumps({"subject": "biology"})},
            )

        with open(sample_files["pdf"], "rb") as f:
            test_app.post(
                "/api/v1/ingest",
                files={"file": ("physics.pdf", f, "application/pdf")},
                data={"metadata": json.dumps({"subject": "physics"})},
            )

        # Query with subject filter
        query_response = test_app.post(
            "/api/v1/query", json={"query": "scientific concepts", "subject": "biology"}
        )

        assert query_response.status_code == 200
        data = query_response.json()

        # All results should be from biology subject
        if len(data["results"]) > 0:
            for result in data["results"]:
                # Check metadata if available
                if "metadata" in result and "subject" in result["metadata"]:
                    assert result["metadata"]["subject"] == "biology"

    def test_multiple_file_formats_queryable(self, test_app, sample_files):
        """Test that all file formats (MD, TXT, PDF) are queryable after ingestion."""
        # Ingest all three file types
        with open(sample_files["markdown"], "rb") as f:
            test_app.post(
                "/api/v1/ingest",
                files={"file": ("biology.md", f, "text/markdown")},
                data={"metadata": json.dumps({"subject": "biology"})},
            )

        with open(sample_files["text"], "rb") as f:
            test_app.post(
                "/api/v1/ingest",
                files={"file": ("math.txt", f, "text/plain")},
                data={"metadata": json.dumps({"subject": "math"})},
            )

        with open(sample_files["pdf"], "rb") as f:
            test_app.post(
                "/api/v1/ingest",
                files={"file": ("physics.pdf", f, "application/pdf")},
                data={"metadata": json.dumps({"subject": "physics"})},
            )

        # Query each subject
        queries = [
            ("photosynthesis", "biology", "photosynthesis"),
            ("Pythagorean theorem", "math", "pythagorean"),
            ("Newton's laws", "physics", "newton"),
        ]

        for query_text, subject, expected_keyword in queries:
            query_response = test_app.post(
                "/api/v1/query", json={"query": query_text, "subject": subject}
            )

            assert query_response.status_code == 200, f"Query failed for {subject}"
            data = query_response.json()

            # Should return results
            assert len(data["results"]) > 0, f"No results for {subject} query"

            # At least one result should contain expected keyword
            found = any(expected_keyword in result["content"].lower() for result in data["results"])
            assert found, f"Expected to find {expected_keyword} in {subject} results"

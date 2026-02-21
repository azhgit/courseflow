"""Integration tests for source document API."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from courseflow.api.main import create_app


@pytest.fixture
def temp_docs_dir():
    """Create temporary docs directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()

        # Create test structure
        (docs_dir / "biology").mkdir()
        (docs_dir / "biology" / "photosynthesis.md").write_text(
        "# Photosynthesis\n\nPhotosynthesis is the process by which plants convert light energy into chemical energy."
        )
        (docs_dir / "programming").mkdir()
        (docs_dir / "programming" / "python.md").write_text(
            "# Python\n\nPython is a high-level programming language."
        )

        # Temporarily change working directory to temp dir
        orig_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            yield Path("docs")
        finally:
            os.chdir(orig_cwd)


@pytest.fixture
def client(temp_docs_dir):
    """Create test client with temporary docs directory."""
    app = create_app()
    return TestClient(app)


def test_get_existing_source_file(client, temp_docs_dir):
    """Test retrieving an existing source file."""
    response = client.get("/api/v1/source/biology/photosynthesis.md")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "photosynthesis.md"
    assert "Photosynthesis" in data["data"]["content"]
    assert "docs/biology/photosynthesis.md" in data["data"]["path"] or "biology/photosynthesis.md" in data["data"]["path"]


def test_get_existing_source_file_with_docs_prefix(client, temp_docs_dir):
    """Test retrieving a source file with leading docs/ prefix."""
    response = client.get("/api/v1/source/docs/biology/photosynthesis.md")
    assert response.status_code == 200


def test_get_nonexistent_source_file(client):
    """Test 404 for nonexistent file."""
    response = client.get("/api/v1/source/nonexistent/file.md")
    assert response.status_code == 404


def test_directory_traversal_attack_with_parent_refs(client):
    """Test prevention of ../ directory traversal."""
    response = client.get("/api/v1/source/../config.py")
    # Should be blocked (403) or not found (404), definitely not 200
    assert response.status_code in [403, 404]


def test_directory_traversal_attack_absolute_path(client):
    """Test prevention of absolute path access."""
    response = client.get("/api/v1/source//etc/passwd")
    assert response.status_code in [400, 403]


def test_non_markdown_file_rejection(client, temp_docs_dir):
    """Test rejection of non-.md files."""
    # Create a non-markdown file in docs
    (temp_docs_dir.parent / "docs" / "test.txt").write_text("Not markdown")
    response = client.get("/api/v1/source/test.txt")
    assert response.status_code == 403


def test_double_slash_prevention(client):
    """Double slashes should never trigger server errors."""
    response = client.get("/api/v1/source//biology//photosynthesis.md")
    assert response.status_code in [200, 400, 403, 404]


def test_response_structure(client, temp_docs_dir):
    """Test correct response JSON structure."""
    response = client.get("/api/v1/source/biology/photosynthesis.md")
    assert response.status_code == 200

    data = response.json()
    assert "success" in data
    assert "data" in data
    assert "path" in data["data"]
    assert "name" in data["data"]
    assert "content" in data["data"]


def test_file_size_limit(client, temp_docs_dir):
    """Test rejection of files exceeding size limit."""
    large_file = temp_docs_dir.parent / "docs" / "large.md"
    # Create a file larger than 2MB
    large_file.write_text("x" * (3 * 1024 * 1024))

    response = client.get("/api/v1/source/large.md")
    assert response.status_code == 413

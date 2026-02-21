"""Test fixtures for source API."""

import pytest
from pathlib import Path


@pytest.fixture
def test_source_dir(tmp_path):
    """Create temporary test source documents directory."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    # Create test subdirectories
    (docs_dir / "biology").mkdir()
    (docs_dir / "programming").mkdir()

    # Create test markdown files
    (docs_dir / "biology" / "test_photosynthesis.md").write_text(
        "# Photosynthesis\n\nPhotosynthesis is the process..."
    )
    (docs_dir / "programming" / "test_async.md").write_text(
        "# Async Programming\n\nAsync/await enables concurrent execution."
    )

    return docs_dir


@pytest.fixture
def test_source_file(test_source_dir):
    """Get path to test source file."""
    return test_source_dir / "biology" / "test_photosynthesis.md"

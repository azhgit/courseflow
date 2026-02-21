"""Source document retrieval endpoint.

Provides safe access to knowledge base documents (docs/ directory only).
Prevents directory traversal attacks and validates all requests.
"""

import logging
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["source"])

# Whitelist: only allow docs/ directory
ALLOWED_DIRECTORY = Path("docs")
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


def _validate_source_path(requested_path: str) -> Path:
    """Validate and normalize source path.

    Args:
        requested_path: User-provided path (e.g., 'biology/photosynthesis.md')

    Returns:
        Validated absolute Path object

    Raises:
        HTTPException: 403 if path is outside allowed directory
        HTTPException: 400 if path format is invalid
    """
    # Normalize optional "docs/" prefix from frontend/source metadata
    normalized_path = unquote(requested_path).lstrip("/")
    if normalized_path.startswith("docs/"):
        normalized_path = normalized_path[len("docs/") :]

    # Parse the requested path
    try:
        requested = Path(normalized_path)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path format",
        ) from e

    # Reject absolute paths and parent directory references
    if requested.is_absolute() or ".." in requested.parts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: invalid path",
        )

    # Construct full path and resolve to absolute
    full_path = (ALLOWED_DIRECTORY / requested).resolve()

    # Ensure resolved path is still under ALLOWED_DIRECTORY
    allowed_resolved = ALLOWED_DIRECTORY.resolve()
    try:
        full_path.relative_to(allowed_resolved)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: path is outside allowed directory",
        )

    # Only allow .md files
    if full_path.suffix.lower() != ".md":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only .md files are allowed",
        )

    return full_path


@router.get("/source/{path:path}", response_model=dict)
async def get_source_file(path: str) -> dict:
    """Retrieve source document content.

    Args:
        path: Relative path to markdown file (e.g., 'biology/photosynthesis.md')

    Returns:
        JSON response with file path, name, and content

    Raises:
        HTTPException 400: Invalid path format
        HTTPException 403: Path outside allowed directory
        HTTPException 404: File not found
    """
    try:
        file_path = _validate_source_path(path)
    except HTTPException:
        raise

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source file not found",
        )

    # Check if it's actually a file (not directory)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Path is not a file",
        )

    # Check file size
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_FILE_SIZE_BYTES} bytes)",
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        logger.warning(f"Failed to decode file {file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not valid UTF-8 text",
        ) from e
    except OSError as e:
        logger.warning(f"Failed to read file {file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file",
        ) from e

    # Construct relative path for response
    relative_path = str(file_path.relative_to(ALLOWED_DIRECTORY.resolve()))
    file_name = file_path.name

    logger.info(f"Retrieved source file: {relative_path}")

    return {
        "success": True,
        "data": {
            "path": relative_path,
            "name": file_name,
            "content": content,
        },
    }

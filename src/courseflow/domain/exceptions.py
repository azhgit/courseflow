"""Domain exceptions for the RAG system.

Custom exceptions that represent business rule violations and infrastructure failures.
These exceptions are independent of HTTP status codes and infrastructure details.
"""


class CourseFlowError(Exception):
    """Base exception for all CourseFlow errors."""

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message


class ValidationError(CourseFlowError):
    """Raised when input validation fails.

    Examples:
        - Empty query text
        - Query text exceeds maximum length
        - Invalid parameters
    """

    pass


class QuotaExceededError(CourseFlowError):
    """Raised when API quota or rate limit is exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying
    """

    def __init__(self, message: str, retry_after: int = 0):
        super().__init__(message)
        self.retry_after = retry_after


class NoRelevantDocumentsError(CourseFlowError):
    """Raised when no documents meet the similarity threshold.

    Attributes:
        threshold: Minimum similarity threshold that was used
        max_similarity: Highest similarity score found (below threshold)
    """

    def __init__(self, message: str, threshold: float = 0.5, max_similarity: float = 0.0):
        super().__init__(message)
        self.threshold = threshold
        self.max_similarity = max_similarity


class ServiceUnavailableError(CourseFlowError):
    """Raised when an external service is temporarily unavailable.

    Examples:
        - Gemini API is down
        - ChromaDB connection failed
        - SQLite database is locked
    """

    def __init__(self, message: str = "Service temporarily unavailable", **_: object):
        super().__init__(message)


class TimeoutError(CourseFlowError):
    """Raised when an operation exceeds its timeout.

    Examples:
        - LLM response takes too long
        - Embedding generation times out
    """

    def __init__(self, message: str = "Operation timed out", **_: object):
        super().__init__(message)


# =============================================================================
# Document Ingestion Exceptions
# =============================================================================


class DuplicateDocumentError(CourseFlowError):
    """Raised when attempting to ingest a document that already exists.

    Attributes:
        content_hash: The SHA-256 hash of the duplicate content
        existing_document_id: ID of the existing document with same content
    """

    def __init__(self, message: str, content_hash: str = "", existing_document_id: str = ""):
        super().__init__(message)
        self.content_hash = content_hash
        self.existing_document_id = existing_document_id


class InvalidFileFormatError(ValidationError):
    """Raised when uploaded file format is not supported.

    Examples:
        - Uploading .docx when only .pdf, .md, .txt are allowed
        - File extension doesn't match actual file type
    """

    pass


class FileSizeExceededError(ValidationError):
    """Raised when uploaded file exceeds maximum size limit.

    Attributes:
        file_size: Actual file size in bytes
        max_size: Maximum allowed size in bytes
    """

    def __init__(self, message: str, file_size: int = 0, max_size: int = 0):
        super().__init__(message)
        self.file_size = file_size
        self.max_size = max_size


class PDFCorruptedError(CourseFlowError):
    """Raised when PDF file is corrupted or password-protected.

    Examples:
        - PDF file is corrupted and cannot be parsed
        - PDF requires password to open
    """

    pass


class EmptyContentError(ValidationError):
    """Raised when document content is empty or whitespace-only.

    Examples:
        - PDF extraction yields no text
        - Markdown file contains only whitespace
    """

    pass


class SubjectNotFoundError(ValidationError):
    """Raised when specified subject does not exist in predefined list.

    Attributes:
        subject: The invalid subject name that was provided
    """

    def __init__(self, message: str, subject: str = ""):
        super().__init__(message)
        self.subject = subject


class IngestionFailedError(CourseFlowError):
    """Raised when document ingestion fails after retries exhausted.

    Attributes:
        document_id: ID of the document that failed to ingest (if created)
        retry_count: Number of retry attempts made
        last_error: The final error that caused failure
    """

    def __init__(
        self, message: str, document_id: str = "", retry_count: int = 0, last_error: str = ""
    ):
        super().__init__(message)
        self.document_id = document_id
        self.retry_count = retry_count
        self.last_error = last_error


class RateLimitExceededError(QuotaExceededError):
    """Raised when rate limit is exceeded after exhausting retries.

    This is a specialized form of QuotaExceededError specifically for
    retry exhaustion scenarios.
    """

    pass


class QueueFullError(QuotaExceededError):
    """Raised when rate limiter queue depth limit is reached.

    Indicates system is overloaded and cannot accept new requests.
    Client should implement backoff and retry later.
    """

    pass

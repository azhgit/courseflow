"""Domain exceptions for the RAG system.

Custom exceptions that represent business rule violations and infrastructure failures.
These exceptions are independent of HTTP status codes and infrastructure details.
"""


class CourseFlowError(Exception):
    """Base exception for all CourseFlow errors."""
    pass


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
    pass


class TimeoutError(CourseFlowError):
    """Raised when an operation exceeds its timeout.
    
    Examples:
        - LLM response takes too long
        - Embedding generation times out
    """
    pass

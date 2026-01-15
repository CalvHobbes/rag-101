"""
Custom exception classes for the RAG ingestion pipeline.
"""

class IngestionException(Exception):
    """Base exception for all ingestion-related errors."""
    pass

class StorageException(Exception):
    """Base exception for all storage-related errors."""
    pass

class FileDiscoveryError(IngestionException):
    """Raised when file discovery fails."""
    pass

class DocumentLoadError(IngestionException):
    """Raised when document loading fails."""
    pass

class ChunkingError(IngestionException):
    """Raised when text chunking fails."""
    pass

class EmbeddingError(IngestionException):
    """Raised when embedding generation fails."""
    pass

class DatabaseConnectionError(StorageException):
    """Raised when database connection fails."""
    pass


"""
Custom exception classes for the RAG query pipeline.
"""
class RetrievalException(Exception):
    """Base exception for all retrieval-related errors."""
    pass
class QueryPreprocessingError(RetrievalException):
    """Raised when query preprocessing fails."""
    pass
class SimilaritySearchError(RetrievalException):
    """Raised when similarity search fails."""
    pass

"""
Custom exception classes for LLM usage.
"""
class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass

class LLMRateLimitError(LLMError):
    """LLM API rate limit exceeded."""
    def __init__(self, message: str, retry_after: float = None):
        super().__init__(message)
        self.retry_after = retry_after

class LLMTimeoutError(LLMError):
    """LLM API call timed out."""
    pass
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

class ConfigurationError(Exception):
    """Raised when there is a configuration error."""
    pass

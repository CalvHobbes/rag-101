"""Custom exception handlers for the API."""
from fastapi import Request
from fastapi.responses import JSONResponse

from src.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    SimilaritySearchError,
    EmbeddingError,
    StorageException,
    QueryPreprocessingError,
)
from src.logging_config import get_logger

log = get_logger(__name__)


async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    """Handle LLM-related errors."""
    log.error("llm_error", path=request.url.path, error=str(exc))
    
    status_code = 503  # Service Unavailable
    detail = "LLM service temporarily unavailable. Please retry."
    
    if isinstance(exc, LLMRateLimitError):
        status_code = 429  # Too Many Requests
        detail = "Rate limit exceeded. Please wait and retry."
    elif isinstance(exc, LLMTimeoutError):
        detail = "LLM request timed out. Please retry."
    
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "error_type": exc.__class__.__name__}
    )


async def retrieval_error_handler(request: Request, exc: SimilaritySearchError) -> JSONResponse:
    """Handle retrieval/search errors."""
    log.error("retrieval_error", path=request.url.path, error=str(exc))
    
    return JSONResponse(
        status_code=503,
        content={"detail": "Search service temporarily unavailable.", "error_type": "SimilaritySearchError"}
    )


async def storage_error_handler(request: Request, exc: StorageException) -> JSONResponse:
    """Handle database/storage errors."""
    log.error("storage_error", path=request.url.path, error=str(exc))
    
    return JSONResponse(
        status_code=503,
        content={"detail": "Database service unavailable.", "error_type": "StorageException"}
    )


async def query_preprocessing_error_handler(request: Request, exc: QueryPreprocessingError) -> JSONResponse:
    """Handle query preprocessing errors."""
    log.error("query_preprocessing_error", path=request.url.path, error=str(exc))
    
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid query format.", "error_type": "QueryPreprocessingError"}
    )
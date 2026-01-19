"""Pydantic schemas for retrieval responses."""
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from src.schemas.chunks import ChunkResponse
from enum import Enum

class FileType(str, Enum):
    PDF = "pdf"
    TXT = "txt"

class RetrievalFilter(BaseModel):
    """
    Filter for retrieval queries.
    
    Args:
        source: specific file path to filter by (e.g. "/path/to/file.pdf")
    """
    source: Optional[str] = None
    file_type: Optional[FileType] = None
    
    # Allow other metadata keys if needed later
    model_config = ConfigDict(extra='allow') 

class RetrievalResult(ChunkResponse):
    """A single retrieved chunk with similarity score."""
    similarity: float = Field(ge=0, le=1, description="Cosine similarity from initial retrieval (1 = identical)")
    rerank_score: Optional[float] = Field(default=None, description="Reranker relevance score (if reranked)")

class RetrievalResponse(BaseModel):
    """Full retrieval response with query info."""
    query: str
    results: list[RetrievalResult]
    top_k: int
    
    @property
    def result_count(self) -> int:
        return len(self.results)


    
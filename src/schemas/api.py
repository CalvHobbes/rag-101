from pydantic import BaseModel, Field
from typing import List, Optional

class ContextChunk(BaseModel):
    """
    A single chunk of context, sanitized for public consumption.
    Hides internal details like absolute file paths and vector scores.
    """
    content: str = Field(..., description="The text content of the retrieved chunk.")
    source: str = Field(..., description="The source filename (e.g. 'document.pdf').")
    page: Optional[int] = Field(default=None, description="Page number if applicable.")

class QueryResponse(BaseModel):
    """
    Public API response for RAG queries.
    """
    query: str = Field(..., description="The original user query.")
    answer: str = Field(..., description="The generated answer.")
    citations: List[str] = Field(..., description="List of unique source filenames used.")
    retrieval_context: List[ContextChunk] = Field(..., description="The sanitized context chunks used.")

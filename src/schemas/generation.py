from typing import Optional, List
from pydantic import BaseModel, Field
from src.schemas.retrieval import RetrievalResponse, RetrievalFilter

class GenerateRequest(BaseModel):
    """
    Request payload for RAG generation.
    """
    query: str = Field(..., min_length=1, description="The user's question.")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of chunks to retrieve context from.")
    rerank: bool = Field(default=True, description="Whether to apply cross-encoder re-ranking.")
    filter: Optional[RetrievalFilter] = Field(default=None, description="Optional metadata filters (e.g. file_type).")

class GenerateResponse(BaseModel):
    """
    Response containing the generated answer and the source context, and citations.
    """
    query: str
    answer: str = Field(..., description="The LLM-generated answer.")
    citations: List[str] = Field(..., description="The source documents used to generate the answer.")
    retrieval_context: RetrievalResponse = Field(..., description="The context chunks provided to the LLM.")    
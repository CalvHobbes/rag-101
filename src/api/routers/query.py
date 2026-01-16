"""
Query endpoint for RAG generation.
"""
from fastapi import APIRouter, HTTPException

from src.schemas.generation import GenerateRequest
from src.schemas.api import QueryResponse, ContextChunk
from src.generation.service import generate_answer
from src.logging_config import get_logger
from src.observability import set_evaluation_source, track

log = get_logger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])

@router.post("", response_model=QueryResponse)
@track(name="rest_query_rag")
async def query(request: GenerateRequest) -> QueryResponse:
    """
    Submit a question and get an answer from the RAG system.
    
    - **query**: The user's question (required)
    - **top_k**: Number of chunks to retrieve (default: 5)
    - **rerank**: Whether to apply re-ranking (default: True)
    - **filter**: Optional metadata filters
    """
    set_evaluation_source("rest")
    log.info("query_endpoint_called", query=request.query)
    internal_response = await generate_answer(request)
    
    # Map to public DTO
    context_chunks = []
    for result in internal_response.retrieval_context.results:
        # Extract filename from "path/to/file.pdf"
        source_name = result.metadata.get("source", "Unknown").split("/")[-1]
        
        context_chunks.append(ContextChunk(
            content=result.content,
            source=source_name,
            page=result.metadata.get("page")
        ))
    
    return QueryResponse(
        query=internal_response.query,
        answer=internal_response.answer,
        citations=internal_response.citations,
        retrieval_context=context_chunks
    )
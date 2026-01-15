"""
Query endpoint for RAG generation.
"""
from fastapi import APIRouter, HTTPException

from src.schemas.generation import GenerateRequest, GenerateResponse
from src.generation.service import generate_answer
from src.logging_config import get_logger
from src.observability import set_evaluation_source, track

log = get_logger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])

@router.post("", response_model=GenerateResponse)
@track(name="rest_query_rag")
async def query(request: GenerateRequest) -> GenerateResponse:
    """
    Submit a question and get an answer from the RAG system.
    
    - **query**: The user's question (required)
    - **top_k**: Number of chunks to retrieve (default: 5)
    - **rerank**: Whether to apply re-ranking (default: True)
    - **filter**: Optional metadata filters
    """
    set_evaluation_source("rest")
    log.info("query_endpoint_called", query=request.query)
    response = await generate_answer(request)
    return response
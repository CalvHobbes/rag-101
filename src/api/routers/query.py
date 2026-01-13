"""
Query endpoint for RAG generation.
"""
from fastapi import APIRouter, HTTPException

from src.schemas.generation import GenerateRequest, GenerateResponse
from src.generation.service import generate_answer
from src.logging_config import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=GenerateResponse)
async def query(request: GenerateRequest) -> GenerateResponse:
    """
    Submit a question and get an answer from the RAG system.
    
    - **query**: The user's question (required)
    - **top_k**: Number of chunks to retrieve (default: 5)
    - **rerank**: Whether to apply re-ranking (default: True)
    - **filter**: Optional metadata filters
    """
    log.info("query_endpoint_called", query=request.query)
    
    try:
        response = await generate_answer(request)
        return response
    except Exception as e:
        log.error("query_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
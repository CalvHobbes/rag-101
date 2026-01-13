"""High-level retrieval orchestration."""
from typing import Optional
from src.retrieval.query_preprocessor import preprocess_query
from src.retrieval.query_embedder import embed_query
from src.retrieval.similarity_search import search_similar_chunks
from src.schemas.retrieval import RetrievalResponse, RetrievalFilter
from src.logging_config import get_logger
from src.retrieval.reranker import rerank_results
from src.observability import track, Phase
from src.config import get_settings

log = get_logger(__name__)


@track(name="retrieve", phase=Phase.RETRIEVAL)
async def retrieve(
    query: str,
    top_k: int = 5,
    distance_threshold: Optional[float] = None,
    metadata_filter: Optional[RetrievalFilter] = None ,
    rerank: bool = True  
) -> RetrievalResponse:
    """
    Full retrieval pipeline: preprocess → embed → search.
    
    Args:
        query: Raw user query
        top_k: Number of results to return
        distance_threshold: Optional max cosine distance
        metadata_filter: Optional metadata filter
        rerank: Whether to rerank results
    Returns:
        RetrievalResponse with query info and ranked results
    """
    # Step 1: Preprocess
    processed_query = preprocess_query(query)
    
    # Step 2: Embed
    embedding = embed_query(processed_query)
    
    # Step 3: Search
    # If reranking, fetch more candidates (e.g., top_k * 3)
    search_k = top_k * 3 if rerank else top_k
    results = await search_similar_chunks(
        embedding, 
        top_k=search_k, 
        distance_threshold=distance_threshold,
        metadata_filter=metadata_filter 
    )
    
    log.info(
        "retrieval_completed",  
        query_length=len(query),
        results_count=len(results),
        rerank=rerank
    )
    
    # Step 4: Rerank if enabled
    if rerank and results:
        results = rerank_results(query, results, top_k)
    
    return RetrievalResponse(
        query=query,
        results=results,
        top_k=top_k
    )

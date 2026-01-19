from typing import List
from sentence_transformers import CrossEncoder
from src.schemas.retrieval import RetrievalResult
from src.logging_config import get_logger
from src.observability import track

log = get_logger(__name__)

# Singleton implementation to avoid reloading model on every request
_reranker_model = None

def get_reranker_model() -> CrossEncoder:
    """Load the CrossEncoder model lazily."""
    global _reranker_model
    if _reranker_model is None:
        log.info("reranker_loading", model="ms-marco-MiniLM-L-6-v2")
        # Initialize CrossEncoder - we use a lightweight but effective model
        _reranker_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _reranker_model

@track(name="rerank_results")
def rerank_results(query: str, chunks: List[RetrievalResult], top_k: int) -> List[RetrievalResult]:
    """
    Re-rank the retrieved chunks using a CrossEncoder.
    
    Args:
        query: The user query
        chunks: List of initially retrieved chunks
        top_k: Number of results to keep after re-ranking (usually smaller than initial retrieval)
    
    Returns:
        Re-ordered and truncated list of chunks
    """
    if not chunks:
        return []
        
    model = get_reranker_model()
    
    # Prepare pairs for scoring: [(query, chunk_content), ...]
    pairs = [[query, chunk.content] for chunk in chunks]
    
    # Predict scores
    scores = model.predict(pairs)
    
    # Store CrossEncoder scores in dedicated rerank_score field
    # Note: CrossEncoder scores are not normalized cosine similarities (they can be negative)
    # but they are better for ranking. We preserve the original cosine similarity.
    for chunk, score in zip(chunks, scores):
        chunk.rerank_score = float(score)
        
    # Sort by rerank score (descending)
    chunks.sort(key=lambda x: x.rerank_score or 0, reverse=True)
    
    log.info("reranking_completed", input_count=len(chunks), top_k=top_k)
    
    return chunks[:top_k]
"""
Model warmup utilities for preloading ML models at startup.
Used by both REST API and MCP server to avoid cold-start latency.
"""
from src.logging_config import get_logger

log = get_logger(__name__)


def warmup_models() -> None:
    """
    Preload all ML models into memory.
    
    Call this at application startup (REST API lifespan or MCP server init)
    to avoid cold-start latency on first request.
    """
    log.info("warmup_started")
    
    # Embedder (HuggingFace SentenceTransformer)
    from src.ingestion.embedder import get_embedder
    log.info("warmup_embedder_loading")
    get_embedder()
    log.info("warmup_embedder_ready")
    
    # Reranker (CrossEncoder)
    from src.retrieval.reranker import get_reranker_model
    log.info("warmup_reranker_loading")
    get_reranker_model()
    log.info("warmup_reranker_ready")
    
    log.info("warmup_completed")

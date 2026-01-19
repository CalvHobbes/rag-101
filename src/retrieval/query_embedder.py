"""Query embedding for retrieval."""
import time
from src.ingestion.embedder import get_embedder
from src.config import get_settings
from src.exceptions import EmbeddingError
from src.logging_config import get_logger
from src.observability import track

log = get_logger(__name__)

@track(name="embed_query")
async def embed_query(query: str) -> list[float]:
    """
    Convert query text to embedding vector.
    
    Uses the same embedder as ingestion for consistency.
    
    Args:
        query: Preprocessed query string
        
    Returns:
        Embedding vector as list of floats
        
    Raises:
        EmbeddingError: If embedding fails
    """
    if not query:
        raise EmbeddingError("Cannot embed empty query")
    
    embedder = get_embedder()
    settings = get_settings().embedding
    
    start_time = time.perf_counter()
    
    try:
        # aembed_query is the async LangChain method for single text
        embedding = await embedder.aembed_query(query)
        
        # Validate dimension
        if len(embedding) != settings.dimension:
            raise EmbeddingError(
                f"Dimension mismatch: got {len(embedding)}, expected {settings.dimension}"
            )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        log.info("query_embedded", dimension=len(embedding), latency_ms=round(latency_ms, 2))
        
        return embedding
    
    except EmbeddingError:
        raise
    except Exception as e:
        log.error("query_embedding_failed", error=str(e))
        raise EmbeddingError(f"Failed to embed query: {e}")
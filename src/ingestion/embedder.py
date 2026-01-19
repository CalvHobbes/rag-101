from functools import lru_cache
from typing import List
from langchain_core.embeddings import Embeddings
from src.config import get_settings, EmbeddingProvider
from src.exceptions import EmbeddingError
from src.logging_config import get_logger
from src.observability import track

log = get_logger(__name__)

@lru_cache
def get_embedder() -> Embeddings:
    """
    Factory to return the configured embedding model.
    Cached to avoid re-initializing heavy models.
    """
    full_settings = get_settings()
    settings = full_settings.embedding
    timeout = full_settings.timeout.embedding_seconds
    
    try:
        if settings.provider == EmbeddingProvider.HUGGINGFACE:
            # Lazy import to avoid hard dependency if using OpenAI
            from langchain_huggingface import HuggingFaceEmbeddings
            log.info("embedder_initialized", provider=settings.provider.value, model=settings.model)
            return HuggingFaceEmbeddings(model_name=settings.model)
            
        elif settings.provider == EmbeddingProvider.OPENAI:
            from langchain_openai import OpenAIEmbeddings
            log.info("embedder_initialized", provider=settings.provider.value, model=settings.model)
            return OpenAIEmbeddings(
                model=settings.model, 
                api_key=settings.api_key,
                request_timeout=timeout
            )
            
        else:
            raise EmbeddingError(f"Unsupported embedding provider: {settings.provider.value}")
            
    except ImportError as e:
        log.error("embedder_import_failed", provider=settings.provider.value, error=str(e))
        raise EmbeddingError(f"Missing dependency for {settings.provider.value}: {e}")
    except Exception as e:
        log.error("embedder_init_failed", provider=settings.provider.value, error=str(e))
        raise EmbeddingError(f"Failed to initialize embedder: {e}")

@track(name="embed_documents")
async def embed_documents(embedder: Embeddings, texts: List[str]) -> List[List[float]]:
    """
    Wrapper to embed documents with observability tracking.
    """
    return await embedder.aembed_documents(texts)
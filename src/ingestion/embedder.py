from functools import lru_cache
from langchain_core.embeddings import Embeddings
from src.config import get_settings
from src.exceptions import EmbeddingError
from src.logging_config import get_logger

log = get_logger(__name__)

@lru_cache
def get_embedder() -> Embeddings:
    """
    Factory to return the configured embedding model.
    Cached to avoid re-initializing heavy models.
    """
    settings = get_settings().embedding
    
    try:
        if settings.provider == "huggingface":
            # Lazy import to avoid hard dependency if using OpenAI
            from langchain_huggingface import HuggingFaceEmbeddings
            log.info("embedder_initialized", provider=settings.provider, model=settings.model)
            return HuggingFaceEmbeddings(model_name=settings.model)
            
        elif settings.provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            if not settings.api_key:
                raise EmbeddingError("OpenAI API key is missing in configuration.")
                
            log.info("embedder_initialized", provider=settings.provider, model=settings.model)
            return OpenAIEmbeddings(
                model=settings.model, 
                api_key=settings.api_key
            )
            
        else:
            raise EmbeddingError(f"Unsupported embedding provider: {settings.provider}")
            
    except ImportError as e:
        log.error("embedder_import_failed", provider=settings.provider, error=str(e))
        raise EmbeddingError(f"Missing dependency for {settings.provider}: {e}")
    except Exception as e:
        log.error("embedder_init_failed", provider=settings.provider, error=str(e))
        raise EmbeddingError(f"Failed to initialize embedder: {e}")

from src.ingestion.text_normalizer import normalize_text
from src.logging_config import get_logger
from src.exceptions import QueryPreprocessingError
from src.observability import track
log = get_logger(__name__)

@track(name="preprocess_query")
def preprocess_query(query: str) -> str:
    """Preprocess query for retrieval."""
    try:
        normalized_query = normalize_text(query)
        normalized_query = " ".join(normalized_query.split())  
        log.debug("query_preprocessed", original_length=len(query),
         processed_length=len(normalized_query))
        return normalized_query
    except Exception as e:
        log.error("query_preprocessing_failed", error=str(e))
        raise QueryPreprocessingError(f"Failed to preprocess query: {e}") from e

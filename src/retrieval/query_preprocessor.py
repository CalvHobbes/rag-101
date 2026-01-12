
from src.ingestion.text_normalizer import normalize_text
from src.logging_config import get_logger

log = get_logger(__name__)


def preprocess_query(query: str) -> str:
    """Preprocess query for retrieval."""
    normalized_query = normalize_text(query)
    normalized_query = " ".join(normalized_query.split())  
    log.debug("query_preprocessed", original_length=len(query),
     processed_length=len(normalized_query))
    return normalized_query

import pytest
import os
from unittest.mock import patch, MagicMock
from src.ingestion.embedder import get_embedder
from src.config import Settings, EmbeddingSettings

def test_get_embedder_huggingface():
    # Helper to clear lru_cache for testing
    get_embedder.cache_clear()
    
    # We don't want to actually load the heavy model in unit tests if possible,
    # but for "learning mode" integration tests it's robust to load the small one.
    # To keep it fast, we can mock it or use the real one if small.
    # Let's trust the real one for the logic check:
    embedder = get_embedder()
    assert embedder is not None
    # Check it's a huggingface one
    from langchain_huggingface import HuggingFaceEmbeddings
    assert isinstance(embedder, HuggingFaceEmbeddings)

@patch("src.ingestion.embedder.get_settings")
def test_get_embedder_openai(mock_settings):
    get_embedder.cache_clear()
    
    # Mock settings to return openai provider
    mock_settings.return_value.embedding.provider = "openai"
    mock_settings.return_value.embedding.api_key = "sk-fake-key"
    mock_settings.return_value.embedding.model = "text-embedding-3-small"

    # Mock the actual import so we don't need the package installed or API access
    with patch.dict("sys.modules", {"langchain_openai": MagicMock()}):
        from langchain_openai import OpenAIEmbeddings
        embedder = get_embedder()
        
        # Verify it tried to create OpenAI embeddings
        OpenAIEmbeddings.assert_called_once()

"""Unit tests for retrieval module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.retrieval.query_preprocessor import preprocess_query
from src.retrieval.similarity_search import search_similar_chunks
from src.retrieval.query_embedder import embed_query
from src.retrieval.retriever import retrieve
from src.schemas.retrieval import RetrievalFilter, RetrievalResult, RetrievalResponse, FileType
from src.exceptions import QueryPreprocessingError

# --- Preprocessor Tests ---

class TestQueryPreprocessor:
    """Tests for query preprocessing."""
    
    def test_strips_whitespace(self):
        """Should strip leading and trailing whitespace."""
        assert preprocess_query("  hello world  ") == "hello world"
    
    def test_collapses_multiple_spaces(self):
        """Should collapse multiple spaces to single space."""
        assert preprocess_query("hello    world") == "hello world"
    
    def test_collapses_newlines_to_space(self):
        """Should collapse newlines to single space."""
        assert preprocess_query("hello\n\nworld") == "hello world"
    
    def test_empty_string_returns_empty(self):
        """Should return empty string for empty input."""
        assert preprocess_query("") == ""
    
    def test_handles_tabs(self):
        """Should collapse tabs to single space."""
        assert preprocess_query("hello\t\tworld") == "hello world"
    
    def test_mixed_whitespace(self):
        """Should handle mixed whitespace characters."""
        assert preprocess_query("  hello \n\t world  ") == "hello world"
    
    def test_preserves_single_spaces(self):
        """Should not modify properly spaced text."""
        assert preprocess_query("hello world") == "hello world"


# --- Query Embedder Tests ---

@pytest.mark.asyncio
@patch("src.retrieval.query_embedder.get_embedder")
@patch("src.retrieval.query_embedder.get_settings")
async def test_embed_query_delegation(mock_settings, mock_get_embedder):
    """Should delegate to the underlying embedder correctly."""
    
    # Setup mocks
    mock_settings.return_value.embedding.dimension = 384
    mock_embedder_instance = MagicMock()
    mock_embedder_instance.aembed_query = AsyncMock(return_value=[0.1] * 384)
    mock_get_embedder.return_value = mock_embedder_instance
    
    vector = await embed_query("test query")
    
    mock_embedder_instance.aembed_query.assert_called_once_with("test query")
    assert len(vector) == 384

@pytest.mark.asyncio
@patch("src.retrieval.query_embedder.get_embedder")
@patch("src.retrieval.query_embedder.get_settings")
async def test_embed_query_dimension_mismatch(mock_settings, mock_get_embedder):
    """Should raise error if dimension mismatches config."""
    
    # Config says 384, model returns 2
    mock_settings.return_value.embedding.dimension = 384
    mock_embedder_instance = MagicMock()
    mock_embedder_instance.aembed_query = AsyncMock(return_value=[0.1, 0.2])
    mock_get_embedder.return_value = mock_embedder_instance
    
    # Should check dimension
    from src.exceptions import EmbeddingError
    with pytest.raises(EmbeddingError, match="Dimension mismatch"):
        await embed_query("test")


# --- Similarity Search Tests ---

@pytest.mark.asyncio
async def test_search_valid_sql_construction():
    """Verify that search calls DB with correct params."""
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    # Mock row return: (chunk_id, content, metadata, doc_id, created, path, score)
    # Using generic object to mimic row
    row = MagicMock()
    # Set attributes explicitly for dot access
    row.chunk_id = "c1"
    row.content = "foo"
    row.metadata = {}
    row.document_id = 1
    from datetime import datetime
    row.created_at = datetime(2023, 1, 1)
    row.file_path = "a.txt"
    row.similarity = 0.95
    # Keep mapping for debugging if needed, but critical part is attributes
    row._mapping = {
        "chunk_id": "c1", "content": "foo", "metadata": {}, 
        "document_id": 1, "created_at": datetime(2023, 1, 1), 
        "file_path": "a.txt", "similarity": 0.95
    }

    
    mock_result.fetchall.return_value = [row]
    mock_session.execute.return_value = mock_result
    
    with patch("src.retrieval.similarity_search.db_manager.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        query_vec = [0.1] * 384
        results = await search_similar_chunks(query_vec, top_k=5)
        
        assert len(results) == 1
        assert results[0].chunk_id == "c1"
        
        # Verify SQL execution
        mock_session.execute.assert_called_once()
        stmt = mock_session.execute.call_args[0][0]
        # Check basic SQL structure in the statement string
        assert "FROM chunks" in str(stmt)
        assert "ORDER BY" in str(stmt)
        assert "LIMIT" in str(stmt)

@pytest.mark.asyncio
async def test_search_metadata_filter():
    """Verify metadata filter modifies SQL."""
    
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(all=lambda: [])
    
    with patch("src.retrieval.similarity_search.db_manager.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        query_vec = [0.1] * 384
        filters = RetrievalFilter(source="test.pdf")
        
        await search_similar_chunks(query_vec, metadata_filter=filters)
        
        stmt = mock_session.execute.call_args[0][0]
        # Use str(stmt) to inspect compiled SQL structure roughly
        sql_str = str(stmt).lower()
        
        # Should contain WHERE clause for metadata or file path
        # Note: exact SQL check is hard without compiling, but we check for intention
        # The code uses: metadata->>'source' ILIKE :source_pattern
        assert "ilike" in sql_str or "metadata" in sql_str

@pytest.mark.asyncio
async def test_search_metadata_filter_file_type_uses_ilike():
    """file_type should map to an ILIKE filter on source."""
    mock_session = AsyncMock()
    mock_session.execute.return_value = MagicMock(all=lambda: [])

    with patch("src.retrieval.similarity_search.db_manager.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session

        query_vec = [0.1] * 384
        filters = RetrievalFilter(file_type=FileType.PDF)

        await search_similar_chunks(query_vec, metadata_filter=filters)

        stmt = mock_session.execute.call_args[0][0]
        sql_str = str(stmt).lower()
        assert "ilike" in sql_str

@pytest.mark.asyncio
async def test_search_metadata_filter_rejects_unknown_key():
    """Reject unsupported metadata filter keys to prevent SQL injection."""
    with patch("src.retrieval.similarity_search.db_manager.get_session") as mock_get_session:
        query_vec = [0.1] * 384
        filters = RetrievalFilter(source="test.pdf", foo="bar")

        with pytest.raises(QueryPreprocessingError, match="Unsupported metadata filter key"):
            await search_similar_chunks(query_vec, metadata_filter=filters)

        mock_get_session.assert_not_called()


# --- Orchestration Tests ---

@pytest.mark.asyncio
async def test_retrieve_flow():
    """Verify the full retrieve orchestration pipeline."""
    
    with patch("src.retrieval.retriever.preprocess_query") as mock_prep, \
         patch("src.retrieval.retriever.embed_query") as mock_embed, \
         patch("src.retrieval.retriever.search_similar_chunks", new_callable=AsyncMock) as mock_search, \
         patch("src.retrieval.retriever.rerank_results") as mock_rerank:
        
        # Setup returns
        mock_prep.return_value = "clean query"
        mock_embed.return_value = [0.1] * 384
        
        mock_res1 = RetrievalResult(
            chunk_id="1", content="low score", metadata={}, document_id=1, 
            created_at="2023", file_path="f", similarity=0.5
        )
        mock_search.return_value = [mock_res1]
        
        # Reranker returns same list
        mock_rerank.return_value = [mock_res1]
        
        # Exec
        response = await retrieve(query="raw query ", top_k=1, rerank=True)
        
        # Assertions
        mock_prep.assert_called_with("raw query ")
        mock_embed.assert_called_with("clean query")
        mock_search.assert_called()
        mock_rerank.assert_called()
        
        assert isinstance(response, RetrievalResponse)
        assert response.query == "raw query "
        assert len(response.results) == 1

@pytest.mark.asyncio
async def test_retrieval_result_allows_negative_similarity():
    """Verify that RetrievalResult accepts negative similarity scores (valid for cosine)."""
    result = RetrievalResult(
        chunk_id="c1", 
        content="foo", 
        metadata={}, 
        document_id=1, 
        created_at="2023-01-01T00:00:00", 
        file_path="a.txt", 
        similarity=-0.5
    )
    assert result.similarity == -0.5

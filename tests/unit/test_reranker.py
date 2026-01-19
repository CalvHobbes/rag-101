import pytest
from unittest.mock import MagicMock, patch
from src.retrieval.reranker import rerank_results, get_reranker_model, _reranker_model
from src.schemas.retrieval import RetrievalResult, RetrievalFilter

@pytest.fixture
def mock_chunks():
    return [
        RetrievalResult(
            chunk_id="1", content="Apple is a fruit", metadata={}, 
            document_id=1, created_at="2023-01-01", file_path="doc1.txt", similarity=0.5
        ),
        RetrievalResult(
            chunk_id="2", content="Banana is yellow", metadata={}, 
            document_id=2, created_at="2023-01-01", file_path="doc2.txt", similarity=0.4
        ),
        RetrievalResult(
            chunk_id="3", content="Carrots are orange vegetables", metadata={}, 
            document_id=3, created_at="2023-01-01", file_path="doc3.txt", similarity=0.3
        ),
    ]

@patch('src.retrieval.reranker.CrossEncoder')
@pytest.mark.asyncio
async def test_rerank_results(mock_cross_encoder_cls, mock_chunks):
    # Setup mock behavior
    mock_model = MagicMock()
    # Mock scores: make the last item (Carrots) the most relevant for query "vegetable"
    mock_model.predict.return_value = [0.1, 0.2, 0.9] 
    mock_cross_encoder_cls.return_value = mock_model
    
    # We need to reset the global singleton to ensure our mock is used
    with patch('src.retrieval.reranker._reranker_model', None):
        query = "vegetable"
        top_k = 2
        
        results = await rerank_results(query, mock_chunks, top_k=top_k)
        
        # Verify call arguments
        # Pairs should be [(query, content)...]
        expected_pairs = [
            [query, "Apple is a fruit"],
            [query, "Banana is yellow"],
            [query, "Carrots are orange vegetables"]
        ]
        mock_model.predict.assert_called_with(expected_pairs)
        
        # Verify results
        assert len(results) == 2
        assert results[0].content == "Carrots are orange vegetables" # Highest score (0.9)
        assert results[0].rerank_score == 0.9
        assert results[1].content == "Banana is yellow" # Second highest (0.2)
        assert results[1].rerank_score == 0.2

@patch('src.retrieval.reranker.CrossEncoder')
def test_get_reranker_model_singleton(mock_cross_encoder_cls):
    # Reset singleton
    with patch('src.retrieval.reranker._reranker_model', None):
        # First call
        model1 = get_reranker_model()
        # Second call
        model2 = get_reranker_model()
        
        assert model1 is model2
        mock_cross_encoder_cls.assert_called_once()

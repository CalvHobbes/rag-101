
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from sqlalchemy import text
from src.generation.service import generate_answer
from src.schemas.generation import GenerateRequest
from src.schemas.retrieval import RetrievalResponse, RetrievalResult
from src.db.db_manager import DatabaseManager
from src.config import get_settings, TimeoutSettings

@pytest.mark.asyncio
async def test_graceful_degradation_on_timeout():
    """
    Test that generate_answer returns a degraded response when the LLM times out.
    """
    # 1. Mock dependencies
    # Create valid Pydantic objects for the mock return value
    mock_retrieval_response = RetrievalResponse(
        query="test timeout",
        top_k=1,
        results=[
            RetrievalResult(
                chunk_id="test_id",
                content="Relevant content",
                metadata={"source": "doc.pdf"},
                document_id=123,
                created_at=datetime.utcnow(),
                file_path="/path/to/doc.pdf",
                similarity=0.9
            )
        ]
    )

    mock_llm = AsyncMock()
    # Configure the mock to raise a TimeoutError
    mock_llm.ainvoke.side_effect = Exception("Request timed out")

    # Use patch context managers
    with patch("src.generation.service.retrieve", return_value=mock_retrieval_response):
        with patch("src.generation.service.get_llm", return_value=mock_llm):
            
            # 2. Call the service
            request = GenerateRequest(query="test timeout", top_k=1)
            response = await generate_answer(request)

            # 3. Verify Graceful Degradation
            assert response.query == "test timeout"
            # It should fallback to the degradation message
            assert "I'm having trouble generating a response" in response.answer, \
                f"Expected fallback message, got: {response.answer}"
            assert "Relevant content" in str(response.retrieval_context)
            assert response.citations == []



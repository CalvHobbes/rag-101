
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.generation.service import generate_answer, format_docs, _extract_citations, _parse_llm_content
from src.generation.llm_factory import get_llm
from src.generation.prompts import get_rag_prompt
from src.schemas.generation import GenerateRequest, GenerateResponse
from src.schemas.retrieval import RetrievalResponse, RetrievalResult
from src.config import Settings, LLMSettings

# --- Service Tests ---

class TestGenerationService:
    
    def test_extract_citations(self):
        """Should extract unique source filenames from [Source: ...] tags."""
        text = "Fact 1 [Source: doc1.pdf]. Fact 2 [Source: doc2.txt]. Fact 3 [Source: doc1.pdf]"
        citations = _extract_citations(text)
        assert citations == ["doc1.pdf", "doc2.txt"]
    
    def test_extract_citations_empty(self):
        """Should return empty list if no citations found."""
        text = "Just some text without sources."
        citations = _extract_citations(text)
        assert citations == []

    def test_format_docs_citation_format(self):
        """Should format documents with [Source: filename] prefix."""
        retrieval_response = RetrievalResponse(
            query="test",
            results=[
                RetrievalResult(
                    chunk_id="1", 
                    content="Content 1", 
                    metadata={"source": "/path/to/doc1.pdf"},
                    similarity=0.9,
                    document_id=1,
                    created_at="2023-01-01",
                    file_path="/path/to/doc1.pdf"
                ),
                RetrievalResult(
                    chunk_id="2", 
                    content="Content 2", 
                    metadata={"source": "doc2.txt"},
                    similarity=0.8,
                    document_id=2,
                    created_at="2023-01-01",
                    file_path="doc2.txt"
                )
            ],
            top_k=2
        )
        
        formatted = format_docs(retrieval_response)
        assert "[Source: doc1.pdf]" in formatted
        assert "Content 1" in formatted
        assert "[Source: doc2.txt]" in formatted
        assert "Content 2" in formatted

    def test_parse_llm_content_string(self):
        """Should return string content as-is."""
        assert _parse_llm_content("simple string") == "simple string"

    def test_parse_llm_content_gemini_list(self):
        """Should parse Gemini-style list content."""
        content = [{'type': 'text', 'text': 'Hello'}, {'type': 'text', 'text': ' World'}]
        assert _parse_llm_content(content) == "Hello  World"

    @pytest.mark.asyncio
    async def test_generate_answer_flow(self):
        """Should orchestrate retrieval and generation correctly."""
        
        # Mock dependencies
        with patch("src.generation.service.retrieve", new_callable=AsyncMock) as mock_retrieve, \
             patch("src.generation.service.get_llm") as mock_get_llm:
            
            # Setup retrieval mock
            mock_retrieval_response = RetrievalResponse(
                query="test query",
                results=[
                    RetrievalResult(
                        chunk_id="1", content="Fruit content", metadata={"source": "apple.txt"},
                        similarity=0.9, document_id=1, created_at="2023-01-01", file_path="apple.txt"
                    )
                ],
                top_k=1
            )
            mock_retrieve.return_value = mock_retrieval_response
            
            # Setup LLM mock
            mock_llm_instance = AsyncMock()
            mock_ai_message = MagicMock()
            mock_ai_message.content = "Apples are fruits [Source: apple.txt]"
            mock_llm_instance.ainvoke.return_value = mock_ai_message
            mock_get_llm.return_value = mock_llm_instance
            
            # Exec
            request = GenerateRequest(query="What are apples?", top_k=1)
            response = await generate_answer(request)
            
            # Verify retrieval called
            mock_retrieve.assert_called_once_with(
                query="What are apples?",
                top_k=1,
                metadata_filter=None,
                rerank=True
            )
            
            # Verify LLM called
            mock_llm_instance.ainvoke.assert_called_once()
            
            # Verify response structure
            assert response.answer == "Apples are fruits [Source: apple.txt]"
            assert response.citations == ["apple.txt"]
            assert response.retrieval_context == mock_retrieval_response

    @pytest.mark.asyncio
    async def test_generate_answer_no_context_fallback(self):
        """Should return fallback message if no documents retrieved."""
        
        with patch("src.generation.service.retrieve", new_callable=AsyncMock) as mock_retrieve:
            # Empty results
            mock_retrieval_response = RetrievalResponse(
                query="alien technology", results=[], top_k=5
            )
            mock_retrieve.return_value = mock_retrieval_response
            
            request = GenerateRequest(query="alien technology")
            response = await generate_answer(request)
            
            assert "could not find any relevant documents" in response.answer.lower()
            assert response.citations == []


# --- LLM Factory Tests ---

@patch("src.generation.llm_factory.get_settings")
def test_get_llm_openai(mock_settings):
    """Should initialize ChatOpenAI with correct settings."""
    # Setup settings
    from src.config import LLMProvider
    mock_settings.return_value.llm.provider = LLMProvider.OPENAI
    mock_settings.return_value.llm.model = "gpt-4o"
    mock_settings.return_value.llm.api_key = "sk-test"

    get_llm.cache_clear()


    # Mock imports
    with patch.dict("sys.modules", {"langchain_openai": MagicMock()}):
        from langchain_openai import ChatOpenAI
        
        get_llm()
        
        ChatOpenAI.assert_called_once_with(
            model="gpt-4o", 
            api_key="sk-test",
            temperature=0
        )

@patch("src.generation.llm_factory.get_settings")
def test_get_llm_invalid_provider(mock_settings):
    """Should raise ValueError for unknown provider."""
    get_llm.cache_clear()
    # Need a mock that has .value attribute for logging, but isn't equal to valid Enums
    mock_provider = MagicMock()
    mock_provider.value = "unknown_provider"
    # Ensure inequality with real Enums
    mock_provider.__eq__.return_value = False
    mock_settings.return_value.llm.provider = mock_provider
    
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_llm()


# --- Prompt Tests ---

def test_rag_prompt_structure():
    """Should have correct input variables."""
    prompt = get_rag_prompt()
    assert "context" in prompt.input_variables
    assert "question" in prompt.input_variables
    
    # Test formatting
    formatted = prompt.format(context="foo", question="bar")
    assert "foo" in formatted
    assert "bar" in formatted

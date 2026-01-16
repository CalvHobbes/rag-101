"""
MCP Server exposing RAG query as a tool for AI assistants.

Provides the same functionality as the REST /query endpoint
with equivalent error handling, logging, and observability.
"""
import os

# Suppress Opik SDK console output (it prints to stdout which breaks MCP JSON protocol)
# Must be set BEFORE importing opik
os.environ["OPIK_CONSOLE_LOGGING_LEVEL"] = "CRITICAL"

# Configure logging FIRST, before any other imports that might log
from src.config import get_settings
from src.logging_config import configure_logging, get_logger

settings = get_settings()
configure_logging(
    log_level=settings.log_level,
    json_format=settings.json_logs,
    use_stderr=True,  # MCP uses stdout for JSON protocol
)

log = get_logger(__name__)

# Now import everything else (safe - logging goes to stderr)
from fastmcp import FastMCP
from src.generation.service import generate_answer
from src.schemas.generation import GenerateRequest
from src.schemas.api import QueryResponse, ContextChunk
from src.observability import configure_observability, track, Phase, set_evaluation_source
from src.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    SimilaritySearchError,
    StorageException,
    QueryPreprocessingError,
)

# Initialize observability
configure_observability()

# Preload ML models (avoids timeout on first tool call)
from src.warmup import warmup_models
warmup_models()

mcp = FastMCP("rag-101")


@mcp.tool()
@track(name="mcp_query_rag")
async def query_rag(
    query: str,
    top_k: int = 5,
    rerank: bool = True,
) -> dict:
    """
    Query the RAG system with a question and get an answer with citations.
    
    Args:
        query: The user's question
        top_k: Number of chunks to retrieve (1-100, default: 5)
        rerank: Whether to apply cross-encoder re-ranking (default: True)
    
    Returns:
        A dict containing the answer, citations, and retrieval context.
    """
    set_evaluation_source("mcp")
    log.info("mcp_query_tool_called", query=query, top_k=top_k, rerank=rerank)
    
    try:
        request = GenerateRequest(query=query, top_k=top_k, rerank=rerank)
        internal_response = await generate_answer(request)
        
        # Map to public DTO
        context_chunks = []
        for result in internal_response.retrieval_context.results:
            source_name = result.metadata.get("source", "Unknown").split("/")[-1]
            context_chunks.append(ContextChunk(
                content=result.content,
                source=source_name,
                page=result.metadata.get("page")
            ))

        response = QueryResponse(
            query=internal_response.query,
            answer=internal_response.answer,
            citations=internal_response.citations,
            retrieval_context=context_chunks
        )
        
        log.info("mcp_query_tool_success", query=query)
        return response.model_dump()
    
    except QueryPreprocessingError as e:
        log.error("mcp_query_preprocessing_error", query=query, error=str(e))
        return {
            "error": True,
            "error_type": "QueryPreprocessingError",
            "message": "Invalid query format.",
        }
    
    except SimilaritySearchError as e:
        log.error("mcp_retrieval_error", query=query, error=str(e))
        return {
            "error": True,
            "error_type": "SimilaritySearchError",
            "message": "Search service temporarily unavailable. Please retry.",
        }
    
    except StorageException as e:
        log.error("mcp_storage_error", query=query, error=str(e))
        return {
            "error": True,
            "error_type": "StorageException",
            "message": "Database service unavailable. Please retry.",
        }
    
    except LLMRateLimitError as e:
        log.error("mcp_llm_rate_limit", query=query, error=str(e))
        return {
            "error": True,
            "error_type": "LLMRateLimitError",
            "message": "Rate limit exceeded. Please wait and retry.",
        }
    
    except LLMTimeoutError as e:
        log.error("mcp_llm_timeout", query=query, error=str(e))
        return {
            "error": True,
            "error_type": "LLMTimeoutError",
            "message": "LLM request timed out. Please retry.",
        }
    
    except LLMError as e:
        log.error("mcp_llm_error", query=query, error=str(e))
        return {
            "error": True,
            "error_type": "LLMError",
            "message": "LLM service temporarily unavailable. Please retry.",
        }
    
    except Exception as e:
        log.exception("mcp_unexpected_error", query=query, error=str(e))
        return {
            "error": True,
            "error_type": "UnexpectedError",
            "message": "An unexpected error occurred.",
        }
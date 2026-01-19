from typing import Any, List
from src.retrieval.retriever import retrieve
from src.generation.llm_factory import get_llm
from src.generation.prompts import get_rag_prompt
from src.schemas.generation import GenerateRequest, GenerateResponse
from src.schemas.retrieval import RetrievalResponse
from src.logging_config import get_logger

import re
from pathlib import Path
from src.config import get_settings
from src.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryCallState
from src.observability import track
log = get_logger(__name__)


import os
from src.observability import configure_observability, Phase, track, get_llm_callback_handler

# Configure observability (Opik)
configure_observability()

# Get the generic callback handler for LLM tracing
# Get the generic callback handler for LLM tracing
# MOVED inside generate_answer to support ContextVar propagation
# llm_tracer = get_llm_callback_handler(phase=Phase.GENERATION)

@track(name="format_docs")
def format_docs(retrieval_response: RetrievalResponse) -> str:
    """
    Format retrieved chunks into a single context string with citations.
    """
    formatted_chunks = []
    for result in retrieval_response.results:
        source_raw = result.metadata.get("source", "Unknown Source")
        source_name = Path(source_raw.replace("\\", "/")).name
        chunk_text = f"[Source: {source_name}]\n{result.content}"
        formatted_chunks.append(chunk_text)
    
    return "\n\n".join(formatted_chunks)

def _parse_llm_content(content: Any) -> str:
    """
    Parse LLM content, handling provider-specific quirks (e.g. Gemini AFC lists).
    """
    if isinstance(content, list):
        try:
            # Gemini may return [{'type': 'text', 'text': ...}, {'extras': ...}]
            text_blocks = [block['text'] for block in content if isinstance(block, dict) and block.get('type') == 'text']
            return " ".join(text_blocks)
        except (KeyError, AttributeError, TypeError):
            # Fallback
            log.warning("llm_content_structure_unexpected", content_type=type(content))
            return str(content)
    
    return str(content)

def _extract_citations(answer: str) -> List[str]:
    """
    Extracts unique source filenames from [Source: filename] tags.
    """
    # Regex to find [Source: <anything>]
    matches = re.findall(r"\[Source: (.*?)\]", answer)
    # Deduplicate and sort
    return sorted(list(set(matches)))

def wait_smart_backoff(retry_state: RetryCallState) -> float:
    """
    Custom wait strategy that respects 'retry_after' from LLMRateLimitError.
    Otherwise falls back to exponential backoff.
    """
    # Default exponential backoff: 2s -> 4s -> 8s ... max 10s (reduced from 70 to sync with fail-fast)
    exp_wait = wait_exponential(multiplier=1, min=2, max=10)(retry_state)
    
    last_exception = retry_state.outcome.exception()
    if isinstance(last_exception, LLMRateLimitError) and last_exception.retry_after:
        log.info("rate_limit_smart_wait_check", retry_after=last_exception.retry_after)
        # return the requested wait time + 1s buffer, but ensure it doesn't exceed reasonable limits implies
        # we strictly follow the API unless it's huge, but the exception raiser handles the "too huge" check.
        return max(exp_wait, last_exception.retry_after + 1.0)
    
    return exp_wait

@retry(
    stop=stop_after_attempt(6), # Increased from 3 to cover ~60s reset
    wait=wait_smart_backoff,    # Use smart custom wait
    retry=retry_if_exception_type((LLMRateLimitError, LLMTimeoutError)),
    reraise=True
)
async def _invoke_llm_with_retry(llm, messages, callbacks):
    """Invoke LLM with automatic retry on transient failures."""
    try:
        return await llm.ainvoke(messages, config={"callbacks": callbacks})
    except Exception as e:
        # Convert provider-specific errors to our exceptions
        error_str = str(e).lower()
        if "rate limit" in error_str or "429" in error_str:
            # Parse retry duration from "retry in 55.3s"
            retry_after = None
            # Regex to find number before 's'
            match = re.search(r"retry in (\d+\.?\d*)s", error_str)
            if match:
                retry_after = float(match.group(1))
                if retry_after > 5:
                    # Fail fast if wait is too long (user requirement: > 5s give up)
                    log.warning("rate_limit_exceeded_max_wait", wait_required=retry_after, max_allowed=5)
                    raise LLMError(f"Rate limit wait too long ({retry_after}s > 5s) - aborting retry to show documents.") from e
            
            raise LLMRateLimitError(str(e), retry_after=retry_after) from e
        elif "timeout" in error_str or "timed out" in error_str:
            raise LLMTimeoutError(str(e)) from e
        else:
            raise LLMError(str(e)) from e

@track(name="generate_answer", phase=Phase.QUERY)
async def generate_answer(request: GenerateRequest) -> GenerateResponse:
    """
    Orchestrate the RAG pipeline: Retrieve -> Format -> Generate.
    """
    log.info("generation_started", query=request.query)
        
    # 1. Retrieve
    retrieval_response = await retrieve(
        query=request.query,
        top_k=request.top_k,
        metadata_filter=request.filter,
        rerank=request.rerank
    )
    
    if not retrieval_response.results:
        log.warning("generation_no_context", query=request.query)
        return GenerateResponse(
            query=request.query,
            answer="I could not find any relevant documents to answer your question.",
            citations=[],
            retrieval_context=retrieval_response
        )

    # 2. Assemble Context
    context_text = format_docs(retrieval_response)
    
    # 3. Prepare Messages (Explicitly)
    prompt_template = get_rag_prompt()
    messages = prompt_template.format_messages(
        context=context_text,
        question=request.query
    )
    
    # 4. Invoke LLM (Directly)
    llm = get_llm()
    
    try:
        # returns AIMessage
        llm_tracer = get_llm_callback_handler(phase=Phase.GENERATION)
        ai_message = await _invoke_llm_with_retry(llm, messages, [llm_tracer])
        answer_text = _parse_llm_content(ai_message.content)
        
        log.info("generation_completed", query=request.query, answer_len=len(answer_text))
        citations = _extract_citations(answer_text)
        return GenerateResponse(
            query=request.query,
            answer=str(answer_text),
            citations=citations,
            retrieval_context=retrieval_response
        )
    except LLMError as e:
        log.error("generation_degraded", query=request.query, error=str(e))
        
        # Fallback: provide raw context so user still gets value
        fallback_answer = "I'm having trouble generating a detailed response. Here are the relevant documents I found:\n\n" + context_text
        
        # Extract sources directly from retrieval results
        fallback_citations = sorted(list(set(
            Path(r.metadata.get("source", "Unknown").replace("\\", "/")).name
            for r in retrieval_response.results
        )))

        return GenerateResponse(
            query=request.query,
            answer=fallback_answer,
            citations=fallback_citations,
            retrieval_context=retrieval_response
        )   
        
    except Exception as e:
        log.error("generation_failed", error=str(e))
        raise

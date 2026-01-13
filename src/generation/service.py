from typing import Any, List
from src.retrieval.retriever import retrieve
from src.generation.llm_factory import get_llm
from src.generation.prompts import get_rag_prompt
from src.schemas.generation import GenerateRequest, GenerateResponse
from src.schemas.retrieval import RetrievalResponse
from src.logging_config import get_logger
from opik.integrations.langchain import OpikTracer
import opik
import re
from src.config import get_settings

log = get_logger(__name__)

# Silence google_genai AFC logs
import logging
logging.getLogger("google_genai.models").setLevel(logging.WARNING)

import os
# Configure Opik globally using settings (auto-detects env vars too)
# pydantic settings will load OPIK__API_KEY
settings = get_settings()

# Handle environment variables for Opik SDK
# Since pydantic-settings reads .env but doesn't set os.environ, we must do it manually
# for the Opik SDK to pick up the project name automatically.
os.environ["OPIK_PROJECT_NAME"] = settings.opik.project_name
if settings.opik.api_key:
    os.environ["OPIK_API_KEY"] = settings.opik.api_key
if settings.opik.workspace:
    os.environ["OPIK_WORKSPACE"] = settings.opik.workspace

opik.configure(use_local=False)

opik_tracer = OpikTracer(
    tags=["rag-101"]
)

@opik.track(name="format_docs")
def format_docs(retrieval_response: RetrievalResponse) -> str:
    """
    Format retrieved chunks into a single context string with citations.
    """
    formatted_chunks = []
    for result in retrieval_response.results:
        source_name = result.metadata.get("source", "Unknown Source").split("/")[-1]
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

@opik.track(name="generate_answer")
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
        ai_message = await llm.ainvoke(messages, config={"callbacks": [opik_tracer]})
        answer_text = _parse_llm_content(ai_message.content)
        
        log.info("generation_completed", query=request.query, answer_len=len(answer_text))
        citations = _extract_citations(answer_text)
        return GenerateResponse(
            query=request.query,
            answer=str(answer_text),
            citations=citations,
            retrieval_context=retrieval_response
        )
        
    except Exception as e:
        log.error("generation_failed", error=str(e))
        raise
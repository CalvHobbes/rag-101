from enum import Enum
from typing import Optional, List, Any
import functools
import os
import contextvars
import inspect

from src.logging_config import get_logger
import opik

log = get_logger(__name__)

# Context variable for trace source (e.g., 'mcp', 'rest')
_source_context = contextvars.ContextVar("source_context", default="unknown")

class Phase(Enum):
    """
    Standardized phases for observability tagging.
    Using an Enum prevents string typos like 'retreival' or 'ingestion_phase'.
    """
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    QUERY = "query"         # Verification/Orchestration phase
    GENERATION = "generation" # LLM phase

def configure_observability():
    """
    Central entry point for observability configuration.
    Currently wraps Opik, but can be extended for others.
    """
    # Handle environment variables for Opik SDK from settings
    from src.config import get_settings
    settings = get_settings()
    
    os.environ["OPIK_PROJECT_NAME"] = settings.opik.project_name
    if settings.opik.api_key:
        os.environ["OPIK_API_KEY"] = settings.opik.api_key
    if settings.opik.workspace:
        os.environ["OPIK_WORKSPACE"] = settings.opik.workspace
    # Opik configuration via environment variables is standard,
    # but we can add programmatic overrides here.
    opik.configure(use_local=False)   
    log.info("observability_configured", provider="opik", project=settings.opik.project_name)

def set_evaluation_source(source: str) -> None:
    """
    Set the source context for the current execution flow.
    Example: 'mcp', 'rest', 'eval_script'
    """
    _source_context.set(source)
    # Also update the current span immediately so the entry point gets tagged
    try:
        opik.opik_context.update_current_trace(tags=[f"source:{source}"])
    except Exception:
        # Trace might not be active
        pass

def track(name: Optional[str] = None, phase: Optional[Phase] = None, tags: Optional[List[str]] = None):
    """
    Vendor-agnostic tracking decorator.
    
    Args:
        name: The name of the trace/span. Defaults to function name.
        phase: High-level phase enum (mapped to phase:X tag).
        tags: Additional list of string tags.
    """
    def decorator(func):
        # 1. Resolve static tags (copy to avoid mutating original)
        static_tags = tags.copy() if tags else []
        if phase:
            static_tags.append(f"phase:{phase.value}")
        
        # 2. Wrap with vendor SDK (Opik)
        @opik.track(name=name, tags=static_tags)
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 3. Resolve dynamic tags (ContextVar) at RUNTIME
            source = _source_context.get()
            if source != "unknown":
                try:
                    opik.opik_context.update_current_span(tags=[f"source:{source}"])
                except Exception:
                    pass
            
            return await func(*args, **kwargs)

        @opik.track(name=name, tags=static_tags)
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 3. Resolve dynamic tags (ContextVar) at RUNTIME
            source = _source_context.get()
            if source != "unknown":
                try:
                    opik.opik_context.update_current_span(tags=[f"source:{source}"])
                except Exception:
                    pass
            
            return func(*args, **kwargs)
            
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

def set_trace_metadata(metadata: dict[str, Any]) -> None:
    """
    Set metadata for the current trace (vendor-agnostic).
    """
    opik.opik_context.update_current_trace(metadata=metadata)

def get_llm_callback_handler(phase: Optional[Phase] = None, tags: Optional[List[str]] = None) -> Any:
    """
    Returns a LangChain callback handler for observability (vendor-agnostic wrapper).
    """
    from opik.integrations.langchain import OpikTracer
    
    final_tags = tags or []
    if phase:
        final_tags.append(f"phase:{phase.value}")

    # Add source tag from context
    source = _source_context.get()
    if source != "unknown":
        final_tags.append(f"source:{source}")
    
    
    return OpikTracer(tags=final_tags)

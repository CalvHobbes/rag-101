from enum import Enum
from typing import Optional, List, Any
import functools
import os

from src.logging_config import get_logger
import opik

log = get_logger(__name__)

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

def track(name: Optional[str] = None, phase: Optional[Phase] = None, tags: Optional[List[str]] = None):
    """
    Vendor-agnostic tracking decorator.
    
    Args:
        name: The name of the trace/span. Defaults to function name.
        phase: High-level phase enum (mapped to phase:X tag).
        tags: Additional list of string tags.
    """
    def decorator(func):
        # 1. Resolve tags
        final_tags = tags or []
        if phase:
            final_tags.append(f"phase:{phase.value}")
        
        # 2. Wrap with vendor SDK (Opik)
        # We use functools.wraps to preserve function metadata
        # which frameworks like FastAPI or Opik rely on.
        @opik.track(name=name, tags=final_tags)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
            
        return wrapper
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
    
    return OpikTracer(tags=final_tags)

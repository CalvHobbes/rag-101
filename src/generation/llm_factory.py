from functools import lru_cache
from langchain_core.language_models import BaseChatModel
from src.config import get_settings, LLMProvider
from src.logging_config import get_logger

log = get_logger(__name__)

@lru_cache
def get_llm() -> BaseChatModel:
    """
    Factory that returns the configured LLM (Chat Model).
    Supports: OpenAI, Google Gemini.
    """
    settings = get_settings()
    llm_context = settings.llm
    timeout = settings.timeout.llm_seconds
    
    try:
        if llm_context.provider == LLMProvider.OPENAI:
            from langchain_openai import ChatOpenAI
            log.info("llm_initialized", provider=llm_context.provider.value, model=llm_context.model)
            return ChatOpenAI(
                model=llm_context.model,
                api_key=llm_context.api_key,
                temperature=0,
                request_timeout=timeout
            )
            
        elif llm_context.provider == LLMProvider.GEMINI:
            from langchain_google_genai import ChatGoogleGenerativeAI
            # Enable converted system messages and disable AFC
            return ChatGoogleGenerativeAI(
                model=llm_context.model,
                google_api_key=llm_context.api_key,
                temperature=0,
                convert_system_message_to_human=True,
                timeout=timeout,
                model_kwargs={"tool_choice": "none"}
            )
            
        else:
            # Should be unreachable due to Pydantic validation, but good safety net
            raise ValueError(f"Unsupported LLM provider: {llm_context.provider}")
            
    except Exception as e:
        log.error("llm_init_failed", provider=settings.llm.provider.value, error=str(e))
        raise
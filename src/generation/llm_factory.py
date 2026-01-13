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
    settings = get_settings().llm
    
    try:
        if settings.provider == LLMProvider.OPENAI:
            from langchain_openai import ChatOpenAI
            log.info("llm_initialized", provider=settings.provider.value, model=settings.model)
            return ChatOpenAI(
                model=settings.model,
                api_key=settings.api_key,
                temperature=0
            )
            
        elif settings.provider == LLMProvider.GEMINI:
            from langchain_google_genai import ChatGoogleGenerativeAI
            log.info("llm_initialized", provider=settings.provider.value, model=settings.model)
            return ChatGoogleGenerativeAI(
                model=settings.model,
                google_api_key=settings.api_key,
                temperature=0,
                convert_system_message_to_human=True
            )
            
        else:
            # Should be unreachable due to Pydantic validation, but good safety net
            raise ValueError(f"Unsupported LLM provider: {settings.provider}")
            
    except Exception as e:
        log.error("llm_init_failed", provider=settings.provider.value, error=str(e))
        raise
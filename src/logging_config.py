"""
Structured logging configuration using structlog.

Usage:
    from src.logging_config import get_logger
    
    log = get_logger(__name__)
    log.info("event_name", key="value", count=42)
"""
import logging
import logging.handlers
import sys
import structlog
from typing import Optional


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None,
    use_stderr: bool = False,
) -> None:
    """
    Configure structlog with processors for structured output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, output JSON. If False, use colored console output.
        log_file: Optional path to log file. If provided, logs to both console and file.
        use_stderr: If True, log to stderr instead of stdout (required for MCP servers).
    """
    # Shared processors for both structlog and stdlib logging
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]
    
    # Console renderer (colored for dev, JSON for prod)
    if json_format:
        console_renderer = structlog.processors.JSONRenderer()
    else:
        console_renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    # File renderer (always JSON for parseability)
    file_renderer = structlog.processors.JSONRenderer()
    
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            console_renderer,
        ],
    )
    # Console handler - use stderr for MCP servers, stdout otherwise
    console_handler = logging.StreamHandler(sys.stderr if use_stderr else sys.stdout)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                file_renderer,
            ],
        )
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=7
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        A bound structlog logger
    """
    return structlog.get_logger(name)


def bind_contextvars(**kwargs) -> None:
    """
    Bind key-value pairs to the context that will be included in all logs.
    Useful for correlation IDs and request-scoped context.
    
    Example:
        bind_contextvars(ingestion_run_id="abc-123")
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_contextvars() -> None:
    """Clear all context variables (call at end of request/operation)."""
    structlog.contextvars.clear_contextvars()

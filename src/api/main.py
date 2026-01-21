"""
FastAPI application for the RAG system.
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.api.routers import query_router, ingest_router

from src.logging_config import get_logger

from src.exceptions import LLMError, SimilaritySearchError, StorageException, QueryPreprocessingError
from src.api.exception_handlers import (
    llm_error_handler,
    retrieval_error_handler,
    storage_error_handler,
    query_preprocessing_error_handler,
)

log = get_logger(__name__)

def _init_workflow_():
     # Initialize DBOS (connects to system database)
    from dbos import DBOS
    DBOS.launch()
    log.info("dbos_initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    log.info("api_startup")
    _init_workflow_()
    from src.warmup import warmup_models
    warmup_models()
    yield
    log.info("api_shutdown")


app = FastAPI(
    title="RAG 101 API",
    description="A production-grade Retrieval-Augmented Generation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(query_router)
app.include_router(ingest_router)   

# Exception handlers
app.add_exception_handler(LLMError, llm_error_handler)
app.add_exception_handler(SimilaritySearchError, retrieval_error_handler)
app.add_exception_handler(StorageException, storage_error_handler)
app.add_exception_handler(QueryPreprocessingError, query_preprocessing_error_handler)

@app.get("/health")
async def health_check():
    """Health check with dependency verification."""
    from fastapi.responses import JSONResponse
    from sqlalchemy import text
    from src.db.db_manager import db_manager
    
    checks = {"api": "healthy"}
    
    # Check database
    try:
        async with db_manager.get_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # Overall status
    all_healthy = all(v == "healthy" for v in checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        content={"status": "healthy" if all_healthy else "degraded", "checks": checks},
        status_code=status_code
    )
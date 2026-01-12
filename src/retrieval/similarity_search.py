"""Similarity search using pgvector."""
import time
from typing import Optional, Any
from sqlalchemy import text
from src.db.db_manager import db_manager
from src.exceptions import StorageException
from src.logging_config import get_logger
from src.schemas.retrieval import RetrievalResult, RetrievalFilter

log = get_logger(__name__)


async def search_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5,
    distance_threshold: Optional[float] = None,
    metadata_filter: Optional[RetrievalFilter] = None
) -> list[RetrievalResult]:
    """
    Find most similar chunks using pgvector cosine distance.
    """
    start_time = time.perf_counter()
    
    # 1. Initialize params dict FIRST
    params = {
        "query_embedding": str(query_embedding),
        "top_k": top_k,
    }

    # 2. Build Base SQL with WHERE 1=1 so we can append ANDs safely
    sql = """
        SELECT 
            c.chunk_id,
            c.content,
            c.metadata,
            c.document_id,
            c.created_at,
            sd.file_path,
            1 - (c.embedding <=> :query_embedding) AS similarity
        FROM chunks c
        LEFT JOIN source_documents sd ON c.document_id = sd.id
        WHERE 1=1
    """

    # 3. Dynamic Filter Construction
    if metadata_filter:
        filter_dict = metadata_filter.model_dump(exclude_unset=True)
        
        for key, value in filter_dict.items():
            if key == "file_type":
                # Special handling: map 'pdf' -> ILIKE '%.pdf' on source
                sql += " AND c.metadata->>'source' ILIKE :file_type_pattern"
                params["file_type_pattern"] = f"%.{value.value}"
            
            elif isinstance(value, list):
                # source IN [...]
                sql += f" AND c.metadata->>'{key}' = ANY(:{key}_val)"
                params[f"{key}_val"] = value
            else:
                # source = ...
                sql += f" AND c.metadata->>'{key}' = :{key}_val"
                params[f"{key}_val"] = value
    
    # 4. Add Threshold 
    if distance_threshold is not None:
        sql += " AND (c.embedding <=> :query_embedding) < :threshold"
        params["threshold"] = distance_threshold
    
    # 5. Order & Limit
    sql += """
        ORDER BY c.embedding <=> :query_embedding
        LIMIT :top_k
    """
    
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(text(sql), params)
            rows = result.fetchall()
        
        chunks = [
            RetrievalResult(
                chunk_id=row.chunk_id,
                content=row.content,
                metadata=row.metadata or {},
                document_id=row.document_id,
                created_at=row.created_at,
                file_path=row.file_path,
                similarity=float(row.similarity),
            )
            for row in rows
        ]
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        log.info(
            "similarity_search_completed",
            top_k=top_k,
            results_returned=len(chunks),
            latency_ms=round(latency_ms, 2)
        )
        
        return chunks
        
    except StorageException:
        raise
    except Exception as e:
        log.error("similarity_search_failed", error=str(e))
        raise StorageException(f"Similarity search failed: {e}")
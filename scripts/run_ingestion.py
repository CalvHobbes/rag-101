import asyncio
import hashlib
import sys
import uuid
from pathlib import Path
from typing import List

# Setup path so we can import src
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.logging_config import configure_logging, get_logger, bind_contextvars, clear_contextvars
from src.ingestion.file_discovery import discover_files, FileInfo
from src.ingestion.document_loader import load_document
from src.ingestion.text_normalizer import normalize_text
from src.ingestion.chunker import chunk_documents
from src.ingestion.embedder import get_embedder, embed_documents
from src.ingestion.storage import save_documents, check_document_exists
from src.db.db_manager import db_manager
from src.schemas.chunks import ChunkCreate
from src.config import get_settings
from src.observability import configure_observability, track, Phase, set_trace_metadata

configure_observability()

# Initialize structured logging
configure_logging(
    log_level=get_settings().log_level,
    json_format=get_settings().json_logs,
    log_file="ingestion.log"
)
log = get_logger(__name__)

def generate_chunk_id(file_hash: str, index: int) -> str:
    """Deterministic ID: hash(file_hash + index)"""
    return hashlib.sha256(f"{file_hash}:{index}".encode()).hexdigest()[:16]

@track(name="process_file")
async def process_file(file_info: FileInfo, embedder):
    """Run the full pipeline for a single file."""
    try:
        log.info("file_processing_started", file_name=file_info.file_path.name)
        
        if await check_document_exists(file_info):
             log.info("file_skipped", file_name=file_info.file_path.name, reason="already_processed")
             return
        
        # 1. Load
        raw_docs = load_document(file_info)
        
        # 2. Normalize
        for doc in raw_docs:
            doc.page_content = normalize_text(doc.page_content)
            
        # 3. Chunk
        chunked_docs = chunk_documents(raw_docs)
        
        if not chunked_docs:
            log.warning("no_chunks_generated", file_name=file_info.file_path.name)
            return

        # 4. Embed (Batch)
        texts = [doc.page_content for doc in chunked_docs]
        embeddings = await embed_documents(embedder, texts)
        
        # 5. Convert to Schemas (The missing link from before!)
        chunk_creates = []
        for i, (doc, vector) in enumerate(zip(chunked_docs, embeddings)):
            chunk_id = generate_chunk_id(file_info.file_hash, i)
            
            # Merge existing metadata with new stuff
            meta = doc.metadata.copy()
            meta["chunk_index"] = i
            
            chunk_creates.append(
                ChunkCreate(
                    chunk_id=chunk_id,
                    file_hash=file_info.file_hash,
                    content=doc.page_content,
                    embedding=vector,
                    metadata=meta
                )
            )
            
        await save_documents(file_info, chunk_creates)
        log.info("file_processed", file_name=file_info.file_path.name, chunks_saved=len(chunk_creates))

    except Exception as e:
        log.error("file_processing_failed", file_name=file_info.file_path.name, error=str(e))


    
@track(name="ingestion_run", phase=Phase.INGESTION, tags=["execution:manual"])
async def ingest_folder(folder_path: Path, run_id: str):
    """Core ingestion logic wrapped in observability."""
    set_trace_metadata({"ingestion_run_id": run_id})
    
    # Init DB
    await db_manager.init_db()
    
    # Discover
    files = discover_files(folder_path)
    log.info("discovery_complete", folder=str(folder_path), files_found=len(files))
    

    
    # Init Embedder (once)
    embedder = get_embedder()
    
    # Process sequentially (for now)
    for file_info in files:
        await process_file(file_info, embedder)
    
    log.info("ingestion_complete", files_processed=len(files))

async def main():
    # Generate a unique run ID for correlation
    run_id = str(uuid.uuid4())[:8]
    bind_contextvars(ingestion_run_id=run_id)
    
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_ingestion.py <folder_path>")
        sys.exit(1)
        
    folder_path = Path(sys.argv[1])
    
    await ingest_folder(folder_path, run_id)
    
    clear_contextvars()

if __name__ == "__main__":
    asyncio.run(main())
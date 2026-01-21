"""
DBOS workflow-based ingestion pipeline.
This module wraps existing ingestion functions in DBOS steps and workflows,
enabling durable execution with resume-from-failure capabilities.
"""
import os
from dbos import DBOS, DBOSConfig, Queue
from pathlib import Path
from typing import List
# Reuse existing functions
from src.ingestion.file_discovery import discover_files, get_file_hash
from src.ingestion.document_loader import load_document
from src.ingestion.text_normalizer import normalize_text
from src.ingestion.chunker import chunk_documents
from src.ingestion.embedder import get_embedder, embed_documents
from src.ingestion.storage import save_documents, check_document_exists
from src.schemas.files import FileInfo
from src.schemas.chunks import ChunkCreate
# --- DBOS Configuration ---
config: DBOSConfig = {
    "name": "rag-101",
    "system_database_url": os.environ.get("DBOS_SYSTEM_DATABASE_URL"),
    "conductor_key": os.environ.get("DBOS_CONDUCTOR_KEY"),
    "conductor_url": os.environ.get("DBOS_CONDUCTOR_URL"),  # For self-hosted Conductor
}
DBOS(config=config)
# Queue for concurrent file processing
file_queue = Queue("file_processing_queue", worker_concurrency=3)

# --- Steps (wrap existing functions) ---
@DBOS.step()
def discover_files_step(folder_path: Path) -> List[dict]:
    """Discover files in folder. Returns serializable dicts."""
    files = discover_files(folder_path)
    # Convert to dicts for serialization (DBOS requirement)
    return [file.model_dump() for file in files]

@DBOS.step()
async def check_exists_step(file_info_dict: dict) -> bool:
    """Check if document already processed."""
    file_info = FileInfo(**file_info_dict)
    return await check_document_exists(file_info)

@DBOS.step()
def load_and_normalize_step(file_info_dict: dict) -> List[dict]:
    """Load document and normalize text."""
    file_info = FileInfo(**file_info_dict)
    raw_docs = load_document(file_info)
    for doc in raw_docs:
        doc.page_content = normalize_text(doc.page_content)
    # Convert to serializable format
    return [{"page_content": d.page_content, "metadata": d.metadata} for d in raw_docs]

@DBOS.step()
def chunk_step(docs: List[dict]) -> List[dict]:
    """Chunk documents."""
    from langchain_core.documents import Document
    lc_docs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in docs]
    chunks = chunk_documents(lc_docs)
    return [{"page_content": c.page_content, "metadata": c.metadata} for c in chunks]

@DBOS.step(retries_allowed=True, max_attempts=3, backoff_rate=2.0)
async def embed_step(texts: List[str]) -> List[List[float]]:
    """Embed texts with retry for transient API failures."""
    embedder = get_embedder()
    return await embed_documents(embedder, texts)

@DBOS.step()
async def save_step(file_info_dict: dict, chunk_creates: List[dict]) -> None:
    """Save documents to database."""
    file_info = FileInfo(**file_info_dict)
    
    # SAFETY CHECK: Verify file on disk still matches the hash we processed
    # This prevents stale workflows (e.g. manual retries of old failures) from overwriting 
    # newer data if the file content has changed since the workflow started.
    
    if file_info.file_path.exists():
        current_hash = get_file_hash(file_info.file_path)
        if current_hash != file_info.file_hash:
            # File has changed! Abort save.
            DBOS.logger.warning(f"Aborting save for {file_info.file_path.name}: File changed on disk (Hash mismatch: {file_info.file_hash} vs {current_hash})")
            return

    from src.schemas.chunks import ChunkCreate
    chunks = [ChunkCreate(**c) for c in chunk_creates]
    await save_documents(file_info, chunks)

# --- Workflows ---
@DBOS.workflow()
async def process_file_workflow(file_info_dict: dict) -> dict:
    """
    Durable workflow for processing a single file.
    
    Each step is checkpointed - if we crash after embedding,
    we resume from save_step, not from the beginning.
    """
    import hashlib
    
    file_info = FileInfo(**file_info_dict)
    file_name = file_info.file_path.name
    
    # Step 1: Check if already processed
    if await check_exists_step(file_info_dict):
        return {"status": "skipped", "file": file_name, "reason": "already_processed"}
    
    # Step 2: Load and normalize
    docs = load_and_normalize_step(file_info_dict)
    if not docs:
        return {"status": "skipped", "file": file_name, "reason": "no_content"}
    
    # Step 3: Chunk
    chunks = chunk_step(docs)
    if not chunks:
        return {"status": "skipped", "file": file_name, "reason": "no_chunks"}
    
    # Step 4: Embed (with retries)
    texts = [c["page_content"] for c in chunks]
    embeddings = await embed_step(texts)
    
    # Step 5: Build ChunkCreate objects (deterministic, done in workflow)
    def generate_chunk_id(file_hash: str, index: int) -> str:
        return hashlib.sha256(f"{file_hash}:{index}".encode()).hexdigest()[:16]
    
    chunk_creates = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = generate_chunk_id(file_info.file_hash, i)
        meta = chunk["metadata"].copy()
        meta["chunk_index"] = i
        chunk_creates.append({
            "chunk_id": chunk_id,
            "file_hash": file_info.file_hash,
            "content": chunk["page_content"],
            "embedding": embedding,
            "metadata": meta
        })
    
    # Step 6: Save
    await save_step(file_info_dict, chunk_creates)
    
    return {"status": "success", "file": file_name, "chunks": len(chunk_creates)}

@DBOS.workflow()
async def ingest_folder_workflow(folder_path_str: str, run_id: str) -> dict:
    """
    Umbrella workflow for ingesting a folder.
    
    Discovers files and enqueues each for concurrent processing.
    """
    from pathlib import Path
    
    folder_path = Path(folder_path_str)
    
    # Step 1: Discover files
    file_dicts = discover_files_step(folder_path)
    
    DBOS.set_event("files_discovered", len(file_dicts))
    
    if not file_dicts:
        return {"status": "complete", "files_found": 0, "run_id": run_id}
    
    # Step 2: Enqueue all files for concurrent processing (async for coroutine workflows)
    handles = []
    for file_dict in file_dicts:
        # Use file hash as deterministic workflow ID
        # This allows DBOS to skip processing if this specific file version was already processed successfully
        child_id = f"process-{file_dict['file_hash']}"
        
        handle = await file_queue.enqueue_async(
            process_file_workflow, 
            file_dict, 
            workflow_id=child_id
        )
        handles.append(handle)
    
    # Summarize
    results = [] # Initialize results list for summary
    for handle in handles:
        result = await handle.get_result()
        results.append(result)

    success_count = sum(1 for r in results if r.get("status") == "success")
    skipped_count = sum(1 for r in results if r.get("status") == "skipped")
    
    DBOS.set_event("files_completed", success_count)
    DBOS.set_event("files_skipped", skipped_count)
    
    return {
        "status": "complete",
        "run_id": run_id,
        "files_found": len(file_dicts),
        "files_processed": success_count,
        "files_skipped": skipped_count,
        "results": results
    }
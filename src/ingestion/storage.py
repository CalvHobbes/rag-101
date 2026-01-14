from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from src.db.db_manager import db_manager
from src.schemas.files import FileInfo
from src.schemas.chunks import ChunkCreate
from src.models.source_document import SourceDocument
from src.models.chunk import Chunk
from src.exceptions import StorageException
from src.config import get_settings
from src.logging_config import get_logger

log = get_logger(__name__)
EMBEDDING_MODEL_NAME = get_settings().embedding.model

async def check_document_exists(file_info: FileInfo) -> bool:
    """Check if the file is already processed with the exact same hash."""
    async with db_manager.get_session() as session:
        query = select(SourceDocument.file_hash).where(
            SourceDocument.file_path == str(file_info.file_path)
        )
        result = await session.execute(query)
        existing_hash = result.scalar_one_or_none()
        
        # If it exists AND matches the current hash, return True
        return existing_hash == file_info.file_hash

from src.observability import track

@track(name="save_documents")
async def save_documents(file_info: FileInfo, chunks: List[ChunkCreate]):
    """
    Idempotent save: 
    1. Check if file exists.
    2. If changed, scrub old chunks.
    3. Save new tracking info + new chunks.
    """
    async with db_manager.get_session() as session:
        try:
            # 1. Check existing record
            query = select(SourceDocument).where(SourceDocument.file_path == str(file_info.file_path))
            result = await session.execute(query)
            existing_doc = result.scalar_one_or_none()

            # 2. Logic: Should we process this?
            if existing_doc:
                if existing_doc.file_hash == file_info.file_hash:
                    log.info("file_skipped", file_path=str(file_info.file_path), reason="unchanged")
                    return # IDEMPOTENCY HIT
                
                # If hash changed, we update the tracking record
                log.info("file_updating", file_path=str(file_info.file_path), reason="hash_changed")
                existing_doc.file_hash = file_info.file_hash
                existing_doc.file_size = file_info.file_size
                existing_doc.embedding_model = EMBEDDING_MODEL_NAME
                
                # Because we used cascade="all, delete-orphan", 
                # we technically just need to remove the relation, 
                # but explicit SQL delete is often safer/clearer for vectors.
                await session.execute(
                    delete(Chunk).where(Chunk.document_id == existing_doc.id)
                )
                doc_id = existing_doc.id

            else:
                # New file! Create tracking record
                log.info("file_creating", file_path=str(file_info.file_path))
                new_doc = SourceDocument(
                    file_path=str(file_info.file_path),
                    file_hash=file_info.file_hash,
                    file_size=file_info.file_size,
                    embedding_model=EMBEDDING_MODEL_NAME
                )
                session.add(new_doc)
                await session.flush() # Flush to get the ID back
                doc_id = new_doc.id

            # 3. Insert Chunks
            # We map Pydantic ChunkCreate -> SQLAlchemy Chunk
            db_chunks = [
                Chunk(
                    chunk_id=c.chunk_id, # Computed hash ID
                    document_id=doc_id,
                    content=c.content,
                    embedding=c.embedding,
                    metadata_=c.metadata
                )
                for c in chunks
            ]
            
            if db_chunks:
                session.add_all(db_chunks)

        except Exception as e:
            log.error("file_save_failed", file_path=str(file_info.file_path), error=str(e))
            raise StorageException(f"Database error: {e}")
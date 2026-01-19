import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from src.models.base import Base
from src.config import get_settings

# Get dimension from config at module level
# This means the table schema depends on what env vars are loaded 
# when you first run "create tables"
EMBEDDING_DIM = get_settings().embedding.dimension

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(Text, unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    
    embedding = Column(Vector(EMBEDDING_DIM))
    
    metadata_ = Column("metadata", JSONB, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime, default=datetime.utcnow)
    # --- Link to Parent ---
    document_id = Column(Integer, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=True)
    document = relationship("SourceDocument", back_populates="chunks")
    # ----------------------
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import relationship
from src.models.base import Base

class SourceDocument(Base):
    """
    Tracks the state of a file in the system.
    Used for idempotency: if file_hash matches, we skip re-ingestion.
    """
    __tablename__ = "source_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identify the file uniquely by path
    file_path = Column(String, unique=True, nullable=False, index=True)
    
    # State tracking
    file_hash = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    
    # Which embedding model was used? (Important if we switch models later)
    embedding_model = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to allow doc.chunks
    # We use string "Chunk" because Chunk might not be imported yet
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
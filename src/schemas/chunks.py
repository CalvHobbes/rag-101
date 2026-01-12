from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ChunkBase(BaseModel):
    chunk_id: str  # Always present - deterministic hash ID
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Input: What we send TO the database
class ChunkCreate(ChunkBase):
    file_hash: str
    embedding: List[float]    # The vector

# Output: What we read FROM the database (includes DB IDs)
class ChunkResponse(ChunkBase):
    model_config = ConfigDict(from_attributes=True)
    
    created_at: Optional[Any] = None  # Optional for flexibility
    document_id: Optional[int] = None
    file_path: Optional[str] = None   # Source file for citations
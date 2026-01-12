from typing import Dict, Any, List
from pydantic import BaseModel, Field

class ChunkBase(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Input: What we send TO the database
class ChunkCreate(ChunkBase):
    chunk_id: str             # The deterministic hash ID
    file_hash: str
    embedding: List[float]    # The vector

# Output: What we read FROM the database (includes DB IDs)
class ChunkResponse(ChunkBase):
    chunk_id: str
    created_at: Any           # Keep it flexible for datetime strings or objects
    
    class Config:
        from_attributes = True # Allows conversion from SQLAlchemy models
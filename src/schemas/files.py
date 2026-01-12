from pathlib import Path
from pydantic import BaseModel

class FileInfo(BaseModel):
    file_path: Path
    file_hash: str
    file_extension: str
    file_size: int

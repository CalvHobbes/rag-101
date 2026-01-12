import os
import hashlib
from pathlib import Path
from typing import List, Set
from src.exceptions import FileDiscoveryError
from src.schemas.files import FileInfo
from src.logging_config import get_logger

log = get_logger(__name__)

def get_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except OSError as e:
        raise FileDiscoveryError(f"Failed to hash file {file_path}: {e}")

def discover_files(folder_path: Path, extensions: List[str] = [".pdf", ".txt"]) -> List[FileInfo]:
    """
    Recursively find files with given extensions in a folder.
    
    Args:
        folder_path: Root directory to search
        extensions: List of allowed file extensions (e.g. ['.pdf', '.txt'])
        
    Returns:
        List of FileInfo objects
    """
    if not folder_path.exists():
        raise FileDiscoveryError(f"Directory not found: {folder_path}")

    discovered_files = []
    
    # Normalize extensions to lowercase
    allowed_exts = {ext.lower() for ext in extensions}

    try:
        for root, _, files in os.walk(folder_path):
            for file_name in files:
                file_path = Path(root) / file_name
                
                if file_path.suffix.lower() in allowed_exts:
                    try:
                        file_info = FileInfo(
                            file_path=file_path.absolute(),
                            file_hash=get_file_hash(file_path),
                            file_extension=file_path.suffix.lower(),
                            file_size=file_path.stat().st_size
                        )
                        discovered_files.append(file_info)
                    except Exception as e:
                        # Log error but skip file (don't crash entire discovery)
                        log.warning("file_discovery_skipped", file_name=file_name, error=str(e))
                        
        return discovered_files
        
    except OSError as e:
        raise FileDiscoveryError(f"Failed to scan directory {folder_path}: {e}")

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from src.ingestion.file_discovery import discover_files, get_file_hash
from src.exceptions import FileDiscoveryError

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory with some dummy files."""
    d = tmp_path / "test_docs"
    d.mkdir()
    (d / "file1.txt").write_text("Hello World", encoding="utf-8")
    (d / "file2.pdf").write_bytes(b"dummy pdf content")
    (d / "image.png").write_bytes(b"dummy image content")
    return d

def test_discover_files_found(temp_dir):
    """Should find only files with matching extensions."""
    files = discover_files(temp_dir, extensions=[".txt", ".pdf"])
    
    assert len(files) == 2
    filenames = sorted([f.file_path.name for f in files])
    assert filenames == ["file1.txt", "file2.pdf"]

def test_discover_files_extensions_case_insensitive(temp_dir):
    """Should match extensions regardless of case."""
    (temp_dir / "file3.TXT").write_text("Caps", encoding="utf-8")
    
    files = discover_files(temp_dir, extensions=[".txt"])
    
    filenames = sorted([f.file_path.name for f in files])
    assert filenames == ["file1.txt", "file3.TXT"]

def test_discover_files_recursive(temp_dir):
    """Should find files recursively."""
    sub = temp_dir / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested", encoding="utf-8")
    
    files = discover_files(temp_dir, extensions=[".txt"])
    
    filenames = sorted([f.file_path.name for f in files])
    assert "nested.txt" in filenames
    assert "file1.txt" in filenames

def test_discover_files_missing_dir():
    """Should raise error if directory does not exist."""
    with pytest.raises(FileDiscoveryError):
        discover_files(Path("/non/existent/path"))

def test_get_file_hash(temp_dir):
    """Should compute SHA256 hash."""
    fp = temp_dir / "file1.txt"
    # echo -n "Hello World" | shasum -a 256
    # a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e
    
    expected_hash = "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"
    assert get_file_hash(fp) == expected_hash

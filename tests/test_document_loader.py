import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.ingestion.document_loader import load_document
from src.schemas.files import FileInfo
from src.exceptions import DocumentLoadError
from langchain_core.documents import Document

@pytest.fixture
def mock_file_info():
    return FileInfo(
        file_path=Path("/tmp/test.pdf"),
        file_hash="abc123hash",
        file_extension=".pdf",
        file_size=1024
    )

@patch('src.ingestion.document_loader.PyMuPDFLoader')
def test_load_pdf_success(mock_loader_cls, mock_file_info):
    # Setup mock
    mock_loader = MagicMock()
    mock_loader.load.return_value = [
        Document(page_content="Page 1", metadata={"page": 1}),
        Document(page_content="Page 2", metadata={"page": 2})
    ]
    mock_loader_cls.return_value = mock_loader
    
    docs = load_document(mock_file_info)
    
    # Check loading
    mock_loader_cls.assert_called_with(str(mock_file_info.file_path))
    assert len(docs) == 2
    
    # VERY IMPORTANT: content check
    assert docs[0].page_content == "Page 1"
    
    # VERY IMPORTANT: Check metadata injection
    assert docs[0].metadata["source"] == str(mock_file_info.file_path)
    assert docs[0].metadata["file_hash"] == "abc123hash"
    assert docs[0].metadata["page"] == 1 

@patch('src.ingestion.document_loader.TextLoader')
def test_load_text_success(mock_loader_cls):
    info = FileInfo(
        file_path=Path("/tmp/test.txt"),
        file_hash="txt123",
        file_extension=".txt",
        file_size=500
    )
    
    mock_loader = MagicMock()
    mock_loader.load.return_value = [Document(page_content="Full text content", metadata={})]
    mock_loader_cls.return_value = mock_loader
    
    docs = load_document(info)
    
    assert len(docs) == 1
    assert docs[0].page_content == "Full text content"
    assert docs[0].metadata["source"] == str(info.file_path)

def test_unsupported_extension():
    info = FileInfo(
        file_path=Path("/tmp/test.jpg"),
        file_hash="hash",
        file_extension=".jpg", # Not supported
        file_size=100
    )
    
    with pytest.raises(DocumentLoadError) as exc:
        load_document(info)
    
    assert "Unsupported file type" in str(exc.value)

@patch('src.ingestion.document_loader.PyMuPDFLoader')
def test_load_failure(mock_loader_cls, mock_file_info):
    # Simulate loader crash
    mock_loader_cls.side_effect = Exception("Corrupted file")
    
    with pytest.raises(DocumentLoadError) as exc:
        load_document(mock_file_info)
        
    assert "Failed to load" in str(exc.value)

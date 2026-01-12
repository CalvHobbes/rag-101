import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ingestion.storage import save_documents, check_document_exists
from src.schemas.files import FileInfo
from src.schemas.chunks import ChunkCreate
from pathlib import Path

@pytest.mark.asyncio
async def test_check_document_exists_true():
    # Mock file info
    file_info = FileInfo(
        file_path=Path("/tmp/test.txt"),
        file_hash="hash123",
        file_extension=".txt",
        file_size=100
    )
    
    # Mock DB session execution
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "hash123"
    
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    
    # Mock db_manager to return our mock session
    with patch("src.ingestion.storage.db_manager.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        exists = await check_document_exists(file_info)
        assert exists is True

@pytest.mark.asyncio
async def test_save_documents_new():
    file_info = FileInfo(
        file_path=Path("/tmp/new.txt"),
        file_hash="newhash",
        file_extension=".txt",
        file_size=50
    )
    chunks = [ChunkCreate(
        chunk_id="c1", 
        file_hash="newhash", 
        chunk_index=0, 
        embedding=[0.1]*384, 
        content="foo"
    )]
    
    mock_exec_result = MagicMock()
    mock_exec_result.scalar_one_or_none.return_value = None # No existing doc
    
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_exec_result
    
    with patch("src.ingestion.storage.db_manager.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        await save_documents(file_info, chunks)
        
        # Verify we added the document and the chunk
        assert mock_session.add.called
        assert mock_session.add_all.called

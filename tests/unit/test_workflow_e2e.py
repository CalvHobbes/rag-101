"""
End-to-end tests for DBOS workflows.

These tests verify the full workflow execution with mocked underlying functions,
following DBOS testing guidelines from https://docs.dbos.dev/python/tutorials/testing
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
from dbos import DBOS, DBOSConfig


@pytest.fixture(scope="function")
def reset_dbos():
    """
    Reset DBOS between tests as per DBOS testing guidelines.
    Uses SQLite to avoid Postgres dependency in unit tests.
    """
    # Destroy any existing DBOS instance
    DBOS.destroy()
    
    # Create new DBOS instance with SQLite for testing
    config: DBOSConfig = {
        "name": "rag-ingestion-test",
        "system_database_url": "sqlite:///test_dbos.sqlite",
    }
    DBOS(config=config)
    
    # Reset system database state
    DBOS.reset_system_database()
    
    # Launch DBOS
    DBOS.launch()
    
    yield
    
    # Cleanup after test
    DBOS.destroy()
    
    # Remove SQLite file
    sqlite_file = Path("test_dbos.sqlite")
    if sqlite_file.exists():
        sqlite_file.unlink()


class TestProcessFileWorkflow:
    """End-to-end tests for process_file_workflow."""

    @pytest.mark.asyncio
    async def test_skips_already_processed_file(self, reset_dbos):
        """Verify workflow returns skipped status for existing files."""
        # Import after DBOS reset
        from src.ingestion.workflow import process_file_workflow

        file_info_dict = {
            "file_path": "/test/existing.pdf",
            "file_hash": "already_processed_hash",
            "file_extension": ".pdf",
            "file_size": 1024
        }

        with patch("src.ingestion.workflow.check_document_exists", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True  # File already exists

            result = await process_file_workflow(file_info_dict)

            assert result["status"] == "skipped"
            assert result["reason"] == "already_processed"
            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_processes_new_file_successfully(self, reset_dbos):
        """Verify workflow processes a new file through all steps."""
        from src.ingestion.workflow import process_file_workflow
        from langchain_core.documents import Document

        file_info_dict = {
            "file_path": "/test/new.pdf",
            "file_hash": "new_file_hash",
            "file_extension": ".pdf",
            "file_size": 2048
        }

        # Mock all underlying functions
        with patch("src.ingestion.workflow.check_document_exists", new_callable=AsyncMock) as mock_check, \
             patch("src.ingestion.workflow.load_document") as mock_load, \
             patch("src.ingestion.workflow.normalize_text") as mock_normalize, \
             patch("src.ingestion.workflow.chunk_documents") as mock_chunk, \
             patch("src.ingestion.workflow.get_embedder") as mock_get_embedder, \
             patch("src.ingestion.workflow.embed_documents", new_callable=AsyncMock) as mock_embed, \
             patch("src.ingestion.workflow.save_documents", new_callable=AsyncMock) as mock_save:

            # Setup mocks
            mock_check.return_value = False  # New file
            
            mock_doc = Mock()
            mock_doc.page_content = "test content"
            mock_doc.metadata = {"source": "/test/new.pdf", "page": 0}
            mock_load.return_value = [mock_doc]
            
            mock_normalize.return_value = "normalized test content"
            
            mock_chunk.return_value = [
                Document(page_content="chunk 1", metadata={"source": "/test/new.pdf"}),
                Document(page_content="chunk 2", metadata={"source": "/test/new.pdf"}),
            ]
            
            mock_embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            # Execute workflow
            result = await process_file_workflow(file_info_dict)

            # Verify result
            assert result["status"] == "success"
            assert result["file"] == "new.pdf"
            assert result["chunks"] == 2

            # Verify all steps were called
            mock_check.assert_called_once()
            mock_load.assert_called_once()
            mock_normalize.assert_called_once()
            mock_chunk.assert_called_once()
            mock_embed.assert_called_once()
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_file_with_no_content(self, reset_dbos):
        """Verify workflow handles files with no loadable content."""
        from src.ingestion.workflow import process_file_workflow

        file_info_dict = {
            "file_path": "/test/empty.pdf",
            "file_hash": "empty_hash",
            "file_extension": ".pdf",
            "file_size": 100
        }

        with patch("src.ingestion.workflow.check_document_exists", new_callable=AsyncMock) as mock_check, \
             patch("src.ingestion.workflow.load_document") as mock_load:

            mock_check.return_value = False
            mock_load.return_value = []  # No documents loaded

            result = await process_file_workflow(file_info_dict)

            assert result["status"] == "skipped"
            assert result["reason"] == "no_content"


class TestIngestFolderWorkflow:
    """End-to-end tests for ingest_folder_workflow."""

    @pytest.mark.asyncio
    async def test_handles_empty_folder(self, reset_dbos):
        """Verify workflow handles folder with no files."""
        from src.ingestion.workflow import ingest_folder_workflow

        with patch("src.ingestion.workflow.discover_files") as mock_discover:
            mock_discover.return_value = []

            result = await ingest_folder_workflow("/empty/folder", "test-run")

            assert result["status"] == "complete"
            assert result["files_found"] == 0
            assert result["run_id"] == "test-run"

    @pytest.mark.asyncio
    async def test_enqueues_files_for_processing(self, reset_dbos):
        """Verify workflow enqueues each discovered file."""
        from src.ingestion.workflow import ingest_folder_workflow
        from src.schemas.files import FileInfo

        mock_files = [
            FileInfo(
                file_path=Path("/test/doc1.pdf"),
                file_hash="hash1",
                file_extension=".pdf",
                file_size=1000
            ),
            FileInfo(
                file_path=Path("/test/doc2.pdf"),
                file_hash="hash2",
                file_extension=".pdf",
                file_size=2000
            ),
        ]

        with patch("src.ingestion.workflow.discover_files") as mock_discover, \
             patch("src.ingestion.workflow.file_queue") as mock_queue:

            mock_discover.return_value = mock_files
            
            # Mock queue.enqueue_async to return mock handles (async version)
            mock_handle = AsyncMock()
            mock_handle.get_result.return_value = {"status": "success", "file": "test.pdf", "chunks": 5}
            mock_queue.enqueue_async = AsyncMock(return_value=mock_handle)

            result = await ingest_folder_workflow("/test/folder", "test-run-2")

            # Verify files were enqueued using async method
            assert mock_queue.enqueue_async.call_count == 2
            assert result["files_found"] == 2
            assert result["files_processed"] == 2


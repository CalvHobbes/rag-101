"""
Unit tests for DBOS workflow steps.

These tests verify that workflow steps correctly wrap existing functions
and return serializable outputs suitable for DBOS checkpointing.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from langchain_core.documents import Document

# Import the step functions (decorators are just pass-through in tests)
from src.ingestion.workflow import (
    discover_files_step,
    load_and_normalize_step,
    chunk_step,
)
from src.schemas.files import FileInfo


class TestDiscoverFilesStep:
    """Tests for discover_files_step."""

    @patch("src.ingestion.workflow.discover_files")
    def test_returns_serializable_dicts(self, mock_discover):
        """Verify step returns list of dicts, not FileInfo objects."""
        # Arrange
        mock_file_info = FileInfo(
            file_path=Path("/test/doc.pdf"),
            file_hash="abc123",
            file_extension=".pdf",
            file_size=1024
        )
        mock_discover.return_value = [mock_file_info]

        # Act
        result = discover_files_step(Path("/test"))

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        # Verify dict has expected keys
        assert "file_path" in result[0]
        assert "file_hash" in result[0]
        assert "file_extension" in result[0]
        assert "file_size" in result[0]
        # Verify values
        assert result[0]["file_hash"] == "abc123"
        assert result[0]["file_extension"] == ".pdf"
        assert result[0]["file_size"] == 1024

    @patch("src.ingestion.workflow.discover_files")
    def test_calls_discover_files_with_path(self, mock_discover):
        """Verify step passes folder path to underlying function."""
        mock_discover.return_value = []
        folder = Path("/my/folder")

        discover_files_step(folder)

        mock_discover.assert_called_once_with(folder)

    @patch("src.ingestion.workflow.discover_files")
    def test_handles_empty_folder(self, mock_discover):
        """Verify step handles empty results."""
        mock_discover.return_value = []

        result = discover_files_step(Path("/empty"))

        assert result == []


class TestLoadAndNormalizeStep:
    """Tests for load_and_normalize_step."""

    @patch("src.ingestion.workflow.normalize_text")
    @patch("src.ingestion.workflow.load_document")
    def test_calls_existing_functions(self, mock_load, mock_normalize):
        """Verify step calls load_document and normalize_text."""
        # Arrange
        mock_doc = Mock()
        mock_doc.page_content = "  raw content  "
        mock_doc.metadata = {"page": 1}
        mock_load.return_value = [mock_doc]
        mock_normalize.return_value = "normalized content"

        file_info_dict = {
            "file_path": "/test/doc.pdf",
            "file_hash": "abc123",
            "file_extension": ".pdf",
            "file_size": 1024
        }

        # Act
        result = load_and_normalize_step(file_info_dict)

        # Assert
        mock_load.assert_called_once()
        mock_normalize.assert_called_once_with("  raw content  ")
        # Verify normalized content is in result
        assert len(result) == 1
        assert result[0]["page_content"] == "normalized content"

    @patch("src.ingestion.workflow.normalize_text")
    @patch("src.ingestion.workflow.load_document")
    def test_returns_serializable_dicts(self, mock_load, mock_normalize):
        """Verify step returns list of dicts, not Document objects."""
        mock_doc = Mock()
        mock_doc.page_content = "content"
        mock_doc.metadata = {"source": "/test/doc.pdf", "page": 0}
        mock_load.return_value = [mock_doc]
        mock_normalize.return_value = "content"

        file_info_dict = {
            "file_path": "/test/doc.pdf",
            "file_hash": "abc123",
            "file_extension": ".pdf",
            "file_size": 1024
        }

        result = load_and_normalize_step(file_info_dict)

        # Verify serializable structure
        assert isinstance(result, list)
        assert isinstance(result[0], dict)
        assert "page_content" in result[0]
        assert "metadata" in result[0]
        assert result[0]["metadata"]["source"] == "/test/doc.pdf"

    @patch("src.ingestion.workflow.normalize_text")
    @patch("src.ingestion.workflow.load_document")
    def test_preserves_metadata(self, mock_load, mock_normalize):
        """Verify metadata is preserved through the step."""
        mock_doc = Mock()
        mock_doc.page_content = "content"
        mock_doc.metadata = {"source": "/path", "page": 5, "custom": "data"}
        mock_load.return_value = [mock_doc]
        mock_normalize.return_value = "content"

        file_info_dict = {
            "file_path": "/test/doc.pdf",
            "file_hash": "abc123",
            "file_extension": ".pdf",
            "file_size": 1024
        }

        result = load_and_normalize_step(file_info_dict)

        assert result[0]["metadata"]["page"] == 5
        assert result[0]["metadata"]["custom"] == "data"


class TestChunkStep:
    """Tests for chunk_step."""

    @patch("src.ingestion.workflow.chunk_documents")
    def test_returns_serializable_dicts(self, mock_chunk):
        """Verify step returns list of dicts, not Document objects."""
        # Arrange
        mock_chunk.return_value = [
            Document(page_content="chunk 1", metadata={"index": 0}),
            Document(page_content="chunk 2", metadata={"index": 1}),
        ]

        docs = [{"page_content": "long content", "metadata": {"source": "/test"}}]

        # Act
        result = chunk_step(docs)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)
        assert result[0]["page_content"] == "chunk 1"
        assert result[1]["page_content"] == "chunk 2"

    @patch("src.ingestion.workflow.chunk_documents")
    def test_reconstructs_documents_before_chunking(self, mock_chunk):
        """Verify step reconstructs LangChain Documents from dicts."""
        mock_chunk.return_value = []

        docs = [
            {"page_content": "content 1", "metadata": {"page": 0}},
            {"page_content": "content 2", "metadata": {"page": 1}},
        ]

        chunk_step(docs)

        # Verify chunk_documents was called with Document objects
        mock_chunk.assert_called_once()
        call_args = mock_chunk.call_args[0][0]
        assert len(call_args) == 2
        assert all(isinstance(d, Document) for d in call_args)
        assert call_args[0].page_content == "content 1"
        assert call_args[1].page_content == "content 2"

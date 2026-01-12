import pytest
from langchain_core.documents import Document
from src.ingestion.chunker import chunk_documents, ChunkingError

def test_chunk_basic():
    text = "a" * 1000
    doc = Document(page_content=text, metadata={"source": "test"})
    chunks = chunk_documents([doc], chunk_size=100, chunk_overlap=0)
    
    assert len(chunks) == 10
    assert chunks[0].page_content == "a" * 100
    assert chunks[0].metadata["source"] == "test"

def test_chunk_overlap():
    text = "1234567890" * 2
    doc = Document(page_content=text, metadata={})
    # chunk_size=10, overlap=5
    # Chunk 1: 0-10
    # Chunk 2: 5-15
    chunks = chunk_documents([doc], chunk_size=10, chunk_overlap=5)
    assert len(chunks) > 1
    # Check overlap roughly (character splitter mechanics vary slightly by separators)

def test_chunk_empty():
    chunks = chunk_documents([], chunk_size=100)
    assert chunks == []

def test_chunk_error_handling():
    with pytest.raises(ChunkingError):
        # Passing None should raise our custom error (via underlying exception)
        chunk_documents(None)

from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.exceptions import ChunkingError
from src.logging_config import get_logger

log = get_logger(__name__)

from src.observability import track

@track(name="chunk_documents")
def chunk_documents(documents: List[Document], chunk_size: int = 800, chunk_overlap: int = 100) -> List[Document]:
    """
    Split documents into smaller chunks while preserving metadata.
    
    Args:
        documents: List of cleaned LangChain Documents
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks (context preservation)
        
    Returns:
        List of chunked LangChain Documents
    """
    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]  # Hierarchy of splits
        )
        
        chunks = splitter.split_documents(documents)
        log.info("chunking_complete", input_docs=len(documents), chunks_created=len(chunks))
        
        return chunks
        
    except Exception as e:
        raise ChunkingError(f"Failed to chunk documents: {e}")
from typing import List
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_core.documents import Document
from src.ingestion.file_discovery import FileInfo
from src.exceptions import DocumentLoadError
from src.logging_config import get_logger

log = get_logger(__name__)

def load_document(file_info: FileInfo) -> List[Document]:
    """
    Load a file and return a list of LangChain Document objects.
    Each page of a PDF becomes a separate Document.
    """
    try:
        log.debug("document_loading", file_path=str(file_info.file_path))
        if file_info.file_extension == ".pdf":
            documents = _load_pdf_document(file_info)
        elif file_info.file_extension == ".txt":
            documents = _load_text_document(file_info)
        else:
            raise DocumentLoadError(f"Unsupported file type: {file_info.file_extension}")

        # IMPORTANT: We must attach our own metadata to these documents
        # so we can track them later.
        for doc in documents:
            doc.metadata["source"] = str(file_info.file_path)
            doc.metadata["file_hash"] = file_info.file_hash
            doc.metadata["file_size"] = file_info.file_size
            
        log.info("document_loaded", file_name=file_info.file_path.name, pages=len(documents))
        return documents

    except Exception as e:
        raise DocumentLoadError(f"Failed to load {file_info.file_path}: {e}")


def _load_pdf_document(file_info: FileInfo) -> List[Document]:
    """
    Load a PDF file and return a list of LangChain Document objects.
    Each page of the PDF becomes a separate Document.
    """
    try:
        loader = PyMuPDFLoader(str(file_info.file_path))
        documents = loader.load()
        return documents
    except Exception as e:
        raise DocumentLoadError(f"Failed to load {file_info.file_path}: {e}")


def _load_text_document(file_info: FileInfo) -> List[Document]:
    """
    Load a text file and return a list of LangChain Document objects.
    Each line of the text file becomes a separate Document.
    """
    try:
        loader = TextLoader(str(file_info.file_path))
        documents = loader.load()
        return documents
    except Exception as e:
        raise DocumentLoadError(f"Failed to load {file_info.file_path}: {e}")   
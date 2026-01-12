import re

def normalize_text(text: str) -> str:
    """
    Clean and normalize text for embedding.
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Replace customized/weird whitespace characters with standard space
    # (keeps newlines intact for now)
    text = re.sub(r'[^\S\n]+', ' ', text)

    # Collapse explicit multiple newlines to max 2 (paragraph separation)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
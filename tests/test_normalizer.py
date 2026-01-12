import pytest
from src.ingestion.text_normalizer import normalize_text

def test_normalize_empty():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""

def test_normalize_whitespace():
    assert normalize_text("  hello   world  ") == "hello world"
    assert normalize_text("hello\tworld") == "hello world"
    
def test_normalize_newlines():
    # Single newlines preserved, multiple collapsed to 2
    text = "Line 1\nLine 2\n\n\nLine 3"
    expected = "Line 1\nLine 2\n\nLine 3"
    assert normalize_text(text) == expected

def test_normalize_null_chars():
    assert normalize_text("hello\x00world") == "helloworld"

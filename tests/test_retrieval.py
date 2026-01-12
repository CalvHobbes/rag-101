"""Unit tests for retrieval module."""
import pytest
from src.retrieval.query_preprocessor import preprocess_query


class TestQueryPreprocessor:
    """Tests for query preprocessing."""
    
    def test_strips_whitespace(self):
        """Should strip leading and trailing whitespace."""
        assert preprocess_query("  hello world  ") == "hello world"
    
    def test_collapses_multiple_spaces(self):
        """Should collapse multiple spaces to single space."""
        assert preprocess_query("hello    world") == "hello world"
    
    def test_collapses_newlines_to_space(self):
        """Should collapse newlines to single space."""
        assert preprocess_query("hello\n\nworld") == "hello world"
    
    def test_empty_string_returns_empty(self):
        """Should return empty string for empty input."""
        assert preprocess_query("") == ""
    
    def test_handles_tabs(self):
        """Should collapse tabs to single space."""
        assert preprocess_query("hello\t\tworld") == "hello world"
    
    def test_mixed_whitespace(self):
        """Should handle mixed whitespace characters."""
        assert preprocess_query("  hello \n\t world  ") == "hello world"
    
    def test_preserves_single_spaces(self):
        """Should not modify properly spaced text."""
        assert preprocess_query("hello world") == "hello world"

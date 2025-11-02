"""Unit test for citation format validation."""

import pytest
from src.lib.citation import (
    format_citation,
    parse_citation,
    format_citation_from_dict,
    validate_citation_format
)


class TestCitationFormat:
    """Unit tests for citation format validation."""
    
    def test_format_citation_with_speaker(self):
        """Test citation formatting with speaker."""
        citation = format_citation(
            "meeting_001",
            "2024-03-15",
            "Alice"
        )
        assert citation == "[meeting_001 | 2024-03-15 | Alice]"
    
    def test_format_citation_without_speaker(self):
        """Test citation formatting without speaker."""
        citation = format_citation(
            "meeting_001",
            "2024-03-15",
            None
        )
        assert citation == "[meeting_001 | 2024-03-15 | ]"
    
    def test_parse_citation_with_speaker(self):
        """Test citation parsing with speaker."""
        citation_str = "[meeting_001 | 2024-03-15 | Alice]"
        parsed = parse_citation(citation_str)
        assert parsed["meeting_id"] == "meeting_001"
        assert parsed["date"] == "2024-03-15"
        assert parsed["speaker"] == "Alice"
    
    def test_parse_citation_without_speaker(self):
        """Test citation parsing without speaker."""
        citation_str = "[meeting_001 | 2024-03-15 | ]"
        parsed = parse_citation(citation_str)
        assert parsed["meeting_id"] == "meeting_001"
        assert parsed["date"] == "2024-03-15"
        assert parsed["speaker"] is None
    
    def test_format_citation_from_dict(self):
        """Test citation formatting from dictionary."""
        citation_dict = {
            "meeting_id": "meeting_001",
            "date": "2024-03-15",
            "speaker": "Alice"
        }
        citation = format_citation_from_dict(citation_dict)
        assert citation == "[meeting_001 | 2024-03-15 | Alice]"
    
    def test_validate_citation_format_valid(self):
        """Test citation format validation - valid format."""
        valid_citations = [
            "[meeting_001 | 2024-03-15 | Alice]",
            "[meeting_001 | 2024-03-15 | ]",
            "[meeting-123 | 2024-01-01 | Bob Smith]"
        ]
        for citation in valid_citations:
            assert validate_citation_format(citation) is True
    
    def test_validate_citation_format_invalid(self):
        """Test citation format validation - invalid format."""
        invalid_citations = [
            "meeting_001 | 2024-03-15 | Alice",  # Missing brackets
            "[meeting_001 2024-03-15]",  # Missing pipe separators
            "[meeting_001]",  # Missing date
            ""  # Empty string
        ]
        for citation in invalid_citations:
            assert validate_citation_format(citation) is False


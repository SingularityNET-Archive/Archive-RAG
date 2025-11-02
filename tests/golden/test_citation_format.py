"""Golden file tests for citation format validation."""

import pytest
from pathlib import Path
from src.lib.citation import format_citation, validate_citation_format


class TestCitationFormatGolden:
    """Golden file tests for citation format."""
    
    def test_citation_format_golden(self):
        """Test citation format matches golden reference."""
        # Golden reference format: [meeting_id | date | speaker]
        golden_examples = [
            ("meeting_001", "2024-03-15", "Alice", "[meeting_001 | 2024-03-15 | Alice]"),
            ("meeting_002", "2024-04-20", None, "[meeting_002 | 2024-04-20 | ]"),
            ("meeting-123", "2024-01-01", "Bob Smith", "[meeting-123 | 2024-01-01 | Bob Smith]"),
        ]
        
        for meeting_id, date, speaker, expected in golden_examples:
            actual = format_citation(meeting_id, date, speaker)
            assert actual == expected, f"Citation format mismatch: {actual} != {expected}"
            assert validate_citation_format(actual), f"Citation format validation failed: {actual}"


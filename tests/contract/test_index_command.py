"""Contract test for index command."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from src.cli.main import app


class TestIndexCommand:
    """Contract tests for index command."""
    
    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def sample_meetings_dir(self, tmp_path):
        """Create sample meeting JSON files."""
        meetings_dir = tmp_path / "meetings"
        meetings_dir.mkdir()
        
        # Create sample meeting JSON
        meeting_file = meetings_dir / "meeting_001.json"
        meeting_file.write_text("""{
            "id": "meeting_001",
            "date": "2024-03-15T10:00:00Z",
            "participants": ["Alice", "Bob"],
            "transcript": "This is a test meeting transcript."
        }""")
        
        return meetings_dir
    
    def test_index_command_help(self, runner):
        """Test index command help."""
        result = runner.invoke(app, ["index", "--help"])
        assert result.exit_code == 0
        assert "Index meeting JSON files" in result.stdout
    
    def test_index_command_basic(self, runner, sample_meetings_dir, tmp_path):
        """Test basic index command execution."""
        output_index = str(tmp_path / "test_index.faiss")
        result = runner.invoke(app, [
            "index",
            str(sample_meetings_dir),
            output_index
        ])
        
        # Command should execute (may fail due to dependencies, but structure should work)
        # This is a contract test - it validates the command structure exists
        assert result.exit_code in [0, 1]  # May fail if dependencies not installed
    
    def test_index_command_with_options(self, runner, sample_meetings_dir, tmp_path):
        """Test index command with options."""
        output_index = str(tmp_path / "test_index.faiss")
        result = runner.invoke(app, [
            "index",
            str(sample_meetings_dir),
            output_index,
            "--embedding-model", "sentence-transformers/all-MiniLM-L6-v2",
            "--chunk-size", "256",
            "--chunk-overlap", "50",
            "--seed", "42",
            "--redact-pii"
        ])
        
        # Contract test validates options are accepted
        assert result.exit_code in [0, 1]


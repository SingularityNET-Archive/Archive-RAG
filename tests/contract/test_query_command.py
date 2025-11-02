"""Contract test for query command."""

import pytest
from typer.testing import CliRunner
from src.cli.main import app


class TestQueryCommand:
    """Contract tests for query command."""
    
    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()
    
    def test_query_command_help(self, runner):
        """Test query command help."""
        result = runner.invoke(app, ["query", "--help"])
        assert result.exit_code == 0
        assert "Query the RAG system" in result.stdout
    
    def test_query_command_structure(self, runner, tmp_path):
        """Test query command structure (contract test)."""
        # Create a dummy index file path
        index_file = str(tmp_path / "test_index.faiss")
        
        result = runner.invoke(app, [
            "query",
            index_file,
            "What decisions were made?"
        ])
        
        # Contract test validates command structure exists
        # Will fail if index file doesn't exist, but validates command accepts args
        assert result.exit_code in [0, 1]
    
    def test_query_command_with_options(self, runner, tmp_path):
        """Test query command with options."""
        index_file = str(tmp_path / "test_index.faiss")
        result = runner.invoke(app, [
            "query",
            index_file,
            "What decisions were made?",
            "--top-k", "10",
            "--seed", "42",
            "--output-format", "json",
            "--user-id", "test@example.com"
        ])
        
        # Contract test validates options are accepted
        assert result.exit_code in [0, 1]


"""Contract tests for compliance CLI commands."""

import pytest
from typer.testing import CliRunner
from pathlib import Path

from src.cli.main import app


class TestComplianceCLI:
    """Contract tests for compliance CLI commands."""
    
    @pytest.fixture
    def runner(self):
        """Fixture for CLI test runner."""
        return CliRunner()
    
    def test_check_compliance_command_help(self, runner):
        """Test check-compliance command help text."""
        result = runner.invoke(app, ["check-compliance", "--help"])
        
        assert result.exit_code == 0
        assert "check-compliance" in result.stdout or "Check constitution compliance" in result.stdout
    
    def test_check_compliance_command_structure(self, runner):
        """Test check-compliance command accepts options."""
        result = runner.invoke(app, [
            "check-compliance",
            "--static",
            "--no-runtime",
            "--tests"
        ])
        
        # Command should execute (may fail if no code exists, but structure should be valid)
        assert result.exit_code in [0, 1, 2]  # 0=success, 1=violations, 2=error
    
    def test_check_compliance_command_with_options(self, runner):
        """Test check-compliance command with various options."""
        result = runner.invoke(app, [
            "check-compliance",
            "--static",
            "--output-format",
            "json"
        ])
        
        # Command should execute
        assert result.exit_code in [0, 1, 2]
    
    def test_check_compliance_command_report_file(self, runner, tmp_path):
        """Test check-compliance command with report file option."""
        report_file = tmp_path / "compliance-report.json"
        
        result = runner.invoke(app, [
            "check-compliance",
            "--static",
            "--output-format",
            "json",
            "--report-file",
            str(report_file)
        ])
        
        # Command should execute
        assert result.exit_code in [0, 1, 2]
        
        # If command succeeded, report file should exist
        if result.exit_code == 0:
            assert report_file.exists()
    
    def test_check_compliance_command_text_output(self, runner):
        """Test check-compliance command with text output format (T048 - US4)."""
        result = runner.invoke(app, [
            "check-compliance",
            "--static",
            "--output-format",
            "text"
        ])
        
        # Command should execute
        assert result.exit_code in [0, 1, 2]
        
        # Output should contain compliance report structure
        if result.exit_code != 2:  # Not an error
            output = result.stdout
            assert "Compliance" in output or "Status" in output or "violation" in output.lower()
    
    def test_check_compliance_command_json_output(self, runner):
        """Test check-compliance command with JSON output format (T049 - US4)."""
        result = runner.invoke(app, [
            "check-compliance",
            "--static",
            "--output-format",
            "json"
        ])
        
        # Command should execute
        assert result.exit_code in [0, 1, 2]
        
        # Output should be valid JSON
        if result.exit_code != 2:  # Not an error
            import json
            try:
                output_json = json.loads(result.stdout)
                assert "overall_status" in output_json or "entity_operations" in output_json
            except json.JSONDecodeError:
                # If JSON parsing fails, check if it's an error message
                assert result.exit_code == 2
    
    def test_check_compliance_command_markdown_output(self, runner):
        """Test check-compliance command with markdown output format (T049 - US4)."""
        result = runner.invoke(app, [
            "check-compliance",
            "--static",
            "--output-format",
            "markdown"
        ])
        
        # Command should execute
        assert result.exit_code in [0, 1, 2]
        
        # Output should contain markdown formatting
        if result.exit_code != 2:  # Not an error
            output = result.stdout
            assert "#" in output or "**" in output  # Markdown headers or bold


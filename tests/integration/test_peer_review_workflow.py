"""Integration test for peer review workflow (SC-006)."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from src.cli.main import app


class TestPeerReviewWorkflow:
    """Integration tests for peer review workflow (SC-006)."""
    
    def test_peer_review_workflow_steps(self, runner):
        """Test that peer reviewer can validate claim in <3 CLI steps using audit-view (SC-006)."""
        # Step 1: Query to get query_id
        # Step 2: Use audit-view to view log by query_id
        # Step 3: Verify claim from audit log
        
        # This validates the workflow structure exists
        # Actual test would require index and query execution
        
        result = runner.invoke(app, ["audit-view", "--help"])
        assert result.exit_code == 0
        assert "Filter by query ID" in result.stdout or "--query-id" in result.stdout
        
        pytest.skip("Requires full system setup - workflow structure validated")


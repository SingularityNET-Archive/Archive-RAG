"""Integration tests for issue reporting flow."""

import pytest
from uuid import uuid4
from datetime import datetime
from pathlib import Path
import json

from src.bot.services.issue_reporting_service import IssueReportingService, IssueReportModal
from src.bot.services.issue_storage import IssueStorage
from src.bot.models.issue_report import IssueReport
from src.bot.models.discord_user import DiscordUser


class TestIssueReportingIntegration:
    """Integration tests for issue reporting service."""
    
    @pytest.fixture
    def temp_storage_dir(self, tmp_path):
        """Create temporary storage directory."""
        storage_dir = tmp_path / "issue_reports"
        storage_dir.mkdir()
        return storage_dir
    
    @pytest.fixture
    def issue_storage(self, temp_storage_dir):
        """Create issue storage instance."""
        return IssueStorage(storage_dir=temp_storage_dir)
    
    @pytest.fixture
    def service(self, issue_storage):
        """Create issue reporting service instance."""
        return IssueReportingService(issue_storage=issue_storage)
    
    @pytest.fixture
    def sample_user(self):
        """Create sample Discord user."""
        return DiscordUser(
            user_id="123456789012345678",
            username="testuser",
            roles=[]
        )
    
    def test_issue_report_save_and_load(self, service, issue_storage, sample_user):
        """Test that issue reports are saved and can be loaded."""
        # Create issue report
        report = IssueReport(
            id=uuid4(),
            query_text="Test query",
            response_text="Test response",
            citations=[],
            user_description="Test description",
            user_id=sample_user.user_id,
            username=sample_user.username,
            message_id=None,
            timestamp=datetime.utcnow()
        )
        
        # Save report
        issue_storage.save_issue_report(report)
        
        # Load report
        loaded_report = issue_storage.get_issue_report(report.id)
        
        assert loaded_report is not None
        assert loaded_report.id == report.id
        assert loaded_report.query_text == report.query_text
        assert loaded_report.user_id == report.user_id
    
    def test_spam_detection_rapid_fire(self, service, issue_storage, sample_user):
        """Test spam detection for rapid-fire submissions."""
        # Create multiple reports rapidly
        for i in range(6):
            report = IssueReport(
                id=uuid4(),
                query_text=f"Test query {i}",
                response_text=f"Test response {i}",
                citations=[],
                user_description=f"Test description {i}",
                user_id=sample_user.user_id,
                username=sample_user.username,
                message_id=None,
                timestamp=datetime.utcnow()
            )
            issue_storage.save_issue_report(report)
        
        # Check spam detection
        is_spam, spam_reason = service._detect_spam(
            IssueReport(
                id=uuid4(),
                query_text="Test query 7",
                response_text="Test response 7",
                citations=[],
                user_description="Test description 7",
                user_id=sample_user.user_id,
                username=sample_user.username,
                message_id=None,
                timestamp=datetime.utcnow()
            ),
            sample_user
        )
        
        # Should detect spam after 5 reports
        assert is_spam is True
        assert spam_reason == "rapid_fire"
    
    def test_spam_detection_duplicate_reports(self, service, issue_storage, sample_user):
        """Test spam detection for duplicate reports."""
        # Create multiple duplicate reports
        query_text = "What decisions were made?"
        response_text = "Test response"
        
        for i in range(4):
            report = IssueReport(
                id=uuid4(),
                query_text=query_text,
                response_text=response_text,
                citations=[],
                user_description=f"Test description {i}",
                user_id=f"user_{i}",
                username=f"user{i}",
                message_id=None,
                timestamp=datetime.utcnow()
            )
            issue_storage.save_issue_report(report)
        
        # Check spam detection
        is_spam, spam_reason = service._detect_spam(
            IssueReport(
                id=uuid4(),
                query_text=query_text,
                response_text=response_text,
                citations=[],
                user_description="Another duplicate",
                user_id="user_5",
                username="user5",
                message_id=None,
                timestamp=datetime.utcnow()
            ),
            DiscordUser(user_id="user_5", username="user5", roles=[])
        )
        
        # Should detect spam after 3 duplicate reports
        assert is_spam is True
        assert spam_reason == "duplicate"
    
    def test_issue_report_aggregation(self, service, issue_storage):
        """Test issue report aggregation by query/response pattern."""
        # Create multiple reports with same query/response
        query_text = "What decisions were made?"
        response_text = "Test response"
        
        for i in range(3):
            report = IssueReport(
                id=uuid4(),
                query_text=query_text,
                response_text=response_text,
                citations=[],
                user_description=f"Description {i}",
                user_id=f"user_{i}",
                username=f"user{i}",
                message_id=None,
                timestamp=datetime.utcnow()
            )
            issue_storage.save_issue_report(report)
        
        # Aggregate reports
        aggregated = service.aggregate_issue_reports(
            query_text=query_text,
            response_text=response_text
        )
        
        # Should find all duplicate reports
        assert len(aggregated) >= 3
    
    def test_issue_report_storage_persistence(self, temp_storage_dir, issue_storage):
        """Test that issue reports persist to disk."""
        report = IssueReport(
            id=uuid4(),
            query_text="Test query",
            response_text="Test response",
            citations=[],
            user_description="Test description",
            user_id="123456789012345678",
            username="testuser",
            message_id=None,
            timestamp=datetime.utcnow()
        )
        
        # Save report
        issue_storage.save_issue_report(report)
        
        # Check file exists
        report_file = temp_storage_dir / f"{report.id}.json"
        assert report_file.exists()
        
        # Verify file contents
        with open(report_file, 'r') as f:
            data = json.load(f)
            assert data['id'] == str(report.id)
            assert data['query_text'] == report.query_text



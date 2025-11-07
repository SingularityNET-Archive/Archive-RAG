"""Unit tests for issue reporting service."""

import pytest
from uuid import uuid4
from datetime import datetime
from pathlib import Path
import json

from src.bot.services.issue_reporting_service import IssueReportingService, IssueReportModal
from src.bot.services.issue_storage import IssueStorage
from src.bot.models.issue_report import IssueReport
from src.bot.models.discord_user import DiscordUser


class TestIssueReportingService:
    """Unit tests for IssueReportingService."""
    
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
    
    @pytest.fixture
    def sample_issue_report(self, sample_user):
        """Create sample issue report."""
        return IssueReport(
            id=uuid4(),
            query_text="What decisions were made?",
            response_text="Test response",
            citations=[],
            user_description="This is incorrect",
            user_id=sample_user.user_id,
            username=sample_user.username,
            timestamp=datetime.utcnow()
        )
    
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert service.issue_storage is not None
    
    def test_detect_spam_rapid_fire(self, service, issue_storage, sample_user):
        """Test spam detection for rapid-fire submissions."""
        # Create multiple reports in quick succession
        for i in range(6):
            report = IssueReport(
                id=uuid4(),
                query_text=f"Query {i}",
                response_text=f"Response {i}",
                citations=[],
                user_description=f"Issue {i}",
                user_id=sample_user.user_id,
                username=sample_user.username,
                timestamp=datetime.utcnow()
            )
            issue_storage.save_issue_report(report)
        
        # Check 6th report should be flagged as spam
        is_spam, reason = service._detect_spam(
            IssueReport(
                id=uuid4(),
                query_text="Query 7",
                response_text="Response 7",
                citations=[],
                user_description="Issue 7",
                user_id=sample_user.user_id,
                username=sample_user.username,
                timestamp=datetime.utcnow()
            ),
            sample_user
        )
        
        assert is_spam is True
        assert reason == "rapid_fire"
    
    def test_detect_spam_duplicate(self, service, issue_storage, sample_user):
        """Test spam detection for duplicate reports."""
        # Create 3 duplicate reports
        query_text = "What decisions were made?"
        response_text = "Test response"
        
        for i in range(3):
            report = IssueReport(
                id=uuid4(),
                query_text=query_text,
                response_text=response_text,
                citations=[],
                user_description=f"Issue {i}",
                user_id=sample_user.user_id,
                username=sample_user.username,
                timestamp=datetime.utcnow()
            )
            issue_storage.save_issue_report(report)
        
        # Check 4th duplicate should be flagged
        is_spam, reason = service._detect_spam(
            IssueReport(
                id=uuid4(),
                query_text=query_text,
                response_text=response_text,
                citations=[],
                user_description="Issue 4",
                user_id=sample_user.user_id,
                username=sample_user.username,
                timestamp=datetime.utcnow()
            ),
            sample_user
        )
        
        assert is_spam is True
        assert reason == "duplicate"
    
    def test_detect_spam_normal(self, service, sample_user):
        """Test that normal reports are not flagged as spam."""
        report = IssueReport(
            id=uuid4(),
            query_text="Normal query",
            response_text="Normal response",
            citations=[],
            user_description="Normal issue",
            user_id=sample_user.user_id,
            username=sample_user.username,
            timestamp=datetime.utcnow()
        )
        
        is_spam, reason = service._detect_spam(report, sample_user)
        
        assert is_spam is False
        assert reason is None
    
    def test_aggregate_issue_reports(self, service, issue_storage, sample_user):
        """Test issue report aggregation."""
        query_text = "What decisions were made?"
        response_text = "Test response"
        
        # Create multiple reports with same query/response
        for i in range(2):
            report = IssueReport(
                id=uuid4(),
                query_text=query_text,
                response_text=response_text,
                citations=[],
                user_description=f"Issue {i}",
                user_id=sample_user.user_id,
                username=sample_user.username,
                timestamp=datetime.utcnow()
            )
            issue_storage.save_issue_report(report)
        
        # Aggregate reports
        aggregated = service.aggregate_issue_reports(
            query_text=query_text,
            response_text=response_text
        )
        
        assert len(aggregated) >= 2


class TestIssueStorage:
    """Unit tests for IssueStorage."""
    
    @pytest.fixture
    def temp_storage_dir(self, tmp_path):
        """Create temporary storage directory."""
        storage_dir = tmp_path / "issue_reports"
        storage_dir.mkdir()
        return storage_dir
    
    @pytest.fixture
    def storage(self, temp_storage_dir):
        """Create issue storage instance."""
        return IssueStorage(storage_dir=temp_storage_dir)
    
    def test_save_and_load_issue_report(self, storage):
        """Test saving and loading issue report."""
        report = IssueReport(
            id=uuid4(),
            query_text="Test query",
            response_text="Test response",
            citations=[],
            user_description="Test issue",
            user_id="123",
            username="testuser",
            timestamp=datetime.utcnow()
        )
        
        # Save
        storage.save_issue_report(report)
        
        # Load
        loaded = storage.load_issue_report(report.id)
        
        assert loaded is not None
        assert loaded.id == report.id
        assert loaded.query_text == report.query_text
        assert loaded.user_id == report.user_id
    
    def test_get_recent_reports_for_user(self, storage):
        """Test getting recent reports for a user."""
        user_id = "123"
        
        # Create multiple reports
        for i in range(3):
            report = IssueReport(
                id=uuid4(),
                query_text=f"Query {i}",
                response_text=f"Response {i}",
                citations=[],
                user_description=f"Issue {i}",
                user_id=user_id,
                username="testuser",
                timestamp=datetime.utcnow()
            )
            storage.save_issue_report(report)
        
        # Get recent reports
        recent = storage.get_recent_reports_for_user(user_id, minutes=5)
        
        assert len(recent) >= 3
        assert all(r.user_id == user_id for r in recent)
    
    def test_find_duplicate_reports(self, storage):
        """Test finding duplicate reports."""
        query_text = "What decisions were made?"
        response_text = "Test response"
        
        # Create duplicate reports
        for i in range(2):
            report = IssueReport(
                id=uuid4(),
                query_text=query_text,
                response_text=response_text,
                citations=[],
                user_description=f"Issue {i}",
                user_id="123",
                username="testuser",
                timestamp=datetime.utcnow()
            )
            storage.save_issue_report(report)
        
        # Find duplicates
        duplicates = storage.find_duplicate_reports(
            query_text=query_text,
            response_text=response_text
        )
        
        assert len(duplicates) >= 2
        assert all(r.query_text == query_text for r in duplicates)
    
    def test_get_all_reports(self, storage):
        """Test getting all reports."""
        # Create multiple reports
        for i in range(3):
            report = IssueReport(
                id=uuid4(),
                query_text=f"Query {i}",
                response_text=f"Response {i}",
                citations=[],
                user_description=f"Issue {i}",
                user_id="123",
                username="testuser",
                timestamp=datetime.utcnow()
            )
            storage.save_issue_report(report)
        
        # Get all reports
        all_reports = storage.get_all_reports()
        
        assert len(all_reports) >= 3




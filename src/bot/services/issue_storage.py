"""Issue report storage service using local JSON files."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from ..models.issue_report import IssueReport
from ...lib.logging import get_logger

logger = get_logger(__name__)


# Issue reports storage directory (local JSON files)
ISSUE_REPORTS_DIR = Path("data/issue_reports")
ISSUE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class IssueStorage:
    """
    Service for storing and retrieving issue reports using local JSON files.
    
    Follows Archive-RAG constitution: local-first storage, no external database dependencies.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize issue storage service.
        
        Args:
            storage_dir: Optional custom storage directory (defaults to ISSUE_REPORTS_DIR)
        """
        self.storage_dir = storage_dir or ISSUE_REPORTS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("issue_storage_initialized", storage_dir=str(self.storage_dir))
    
    def save_issue_report(self, issue_report: IssueReport) -> None:
        """
        Save issue report to JSON file.
        
        Args:
            issue_report: IssueReport to save
        """
        issue_file = self.storage_dir / f"{issue_report.id}.json"
        
        try:
            # Convert to dict and save
            issue_dict = issue_report.model_dump(mode="json")
            # Convert datetime to ISO string for JSON
            if isinstance(issue_dict.get("timestamp"), datetime):
                issue_dict["timestamp"] = issue_dict["timestamp"].isoformat()
            if isinstance(issue_dict.get("resolved_at"), datetime):
                issue_dict["resolved_at"] = issue_dict["resolved_at"].isoformat()
            
            with open(issue_file, "w", encoding="utf-8") as f:
                json.dump(issue_dict, f, indent=2, ensure_ascii=False)
            
            logger.debug("issue_report_saved", issue_id=str(issue_report.id), file=str(issue_file))
        except Exception as e:
            logger.error("issue_report_save_failed", issue_id=str(issue_report.id), error=str(e))
            raise
    
    def load_issue_report(self, issue_id: UUID) -> Optional[IssueReport]:
        """
        Load issue report from JSON file.
        
        Args:
            issue_id: Issue report UUID
            
        Returns:
            IssueReport if found, None otherwise
        """
        issue_file = self.storage_dir / f"{issue_id}.json"
        
        if not issue_file.exists():
            return None
        
        try:
            with open(issue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Parse datetime strings back to datetime objects
            if "timestamp" in data and isinstance(data["timestamp"], str):
                data["timestamp"] = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            if "resolved_at" in data and isinstance(data["resolved_at"], str):
                data["resolved_at"] = datetime.fromisoformat(data["resolved_at"].replace("Z", "+00:00"))
            
            return IssueReport(**data)
        except Exception as e:
            logger.error("issue_report_load_failed", issue_id=str(issue_id), error=str(e))
            return None
    
    def get_recent_reports_for_user(
        self,
        user_id: str,
        minutes: int = 5,
    ) -> List[IssueReport]:
        """
        Get recent issue reports for a user (for spam detection).
        
        Args:
            user_id: Discord user ID
            minutes: Time window in minutes
            
        Returns:
            List of recent IssueReport objects
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_reports = []
        
        for issue_file in self.storage_dir.glob("*.json"):
            try:
                issue_id = UUID(issue_file.stem)
                report = self.load_issue_report(issue_id)
                if report and report.user_id == user_id and report.timestamp >= cutoff_time:
                    recent_reports.append(report)
            except (ValueError, AttributeError):
                continue
        
        return recent_reports
    
    def find_duplicate_reports(
        self,
        query_text: Optional[str] = None,
        response_text: Optional[str] = None,
    ) -> List[IssueReport]:
        """
        Find duplicate issue reports (same query/response pattern).
        
        Args:
            query_text: Optional query text to match
            response_text: Optional response text to match
            
        Returns:
            List of duplicate IssueReport objects
        """
        duplicate_reports = []
        
        for issue_file in self.storage_dir.glob("*.json"):
            try:
                issue_id = UUID(issue_file.stem)
                report = self.load_issue_report(issue_id)
                if not report:
                    continue
                
                # Match query text
                if query_text and report.query_text.lower() != query_text.lower():
                    continue
                
                # Match response text (exact or similar)
                if response_text:
                    # Use simple similarity check (could be enhanced with fuzzy matching)
                    if response_text.lower() not in report.response_text.lower() and \
                       report.response_text.lower() not in response_text.lower():
                        continue
                
                duplicate_reports.append(report)
            except (ValueError, AttributeError):
                continue
        
        return duplicate_reports
    
    def get_all_reports(
        self,
        include_spam: bool = False,
        resolved_only: bool = False,
    ) -> List[IssueReport]:
        """
        Get all issue reports (for admin review).
        
        Args:
            include_spam: Whether to include spam-flagged reports
            resolved_only: Whether to return only resolved reports
            
        Returns:
            List of IssueReport objects
        """
        all_reports = []
        
        for issue_file in self.storage_dir.glob("*.json"):
            try:
                issue_id = UUID(issue_file.stem)
                report = self.load_issue_report(issue_id)
                if not report:
                    continue
                
                # Filter spam
                if not include_spam and report.is_spam:
                    continue
                
                # Filter resolved
                if resolved_only and not report.is_resolved:
                    continue
                
                all_reports.append(report)
            except (ValueError, AttributeError):
                continue
        
        # Sort by timestamp (newest first)
        all_reports.sort(key=lambda r: r.timestamp, reverse=True)
        
        return all_reports
    
    def update_issue_report(self, issue_report: IssueReport) -> None:
        """
        Update an existing issue report.
        
        Args:
            issue_report: Updated IssueReport
        """
        self.save_issue_report(issue_report)


def create_issue_storage() -> IssueStorage:
    """
    Create an issue storage instance.
    
    Returns:
        IssueStorage instance
    """
    return IssueStorage()




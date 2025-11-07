"""Issue reporting service for Discord bot."""

from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

import discord
from discord import app_commands

from ..models.issue_report import IssueReport
from ..models.discord_user import DiscordUser
from .issue_storage import IssueStorage, create_issue_storage
from ...lib.logging import get_logger

logger = get_logger(__name__)


class IssueReportingService:
    """
    Service for handling issue reports from Discord bot users.
    
    Handles:
    - Issue report submission via Discord modal
    - Spam detection
    - Issue aggregation
    - Confirmation messages
    """
    
    def __init__(
        self,
        issue_storage: Optional[IssueStorage] = None,
    ):
        """
        Initialize issue reporting service.
        
        Args:
            issue_storage: Optional IssueStorage instance
        """
        self.issue_storage = issue_storage or create_issue_storage()
        
        logger.info("issue_reporting_service_initialized")
    
    async def create_report_modal(
        self,
        interaction: discord.Interaction,
        query_text: str,
        response_text: str,
        citations: list,
        message_id: Optional[str] = None,
    ) -> None:
        """
        Create and show Discord modal form for issue reporting.
        
        Args:
            interaction: Discord interaction
            query_text: Original query text
            response_text: Bot response text
            citations: List of citations
            message_id: Optional Discord message ID
        """
        # Phase 8: T062 - Logging for all issue reporting operations
        user_id = str(interaction.user.id) if interaction.user else "unknown"
        logger.info(
            "issue_report_modal_opened",
            user_id=user_id,
            username=interaction.user.name if interaction.user else "unknown",
            query_text_length=len(query_text),
            response_text_length=len(response_text),
            citation_count=len(citations),
            message_id=message_id
        )
        
        modal = IssueReportModal(
            query_text=query_text,
            response_text=response_text,
            citations=citations,
            message_id=message_id,
        )
        await interaction.response.send_modal(modal)
    
    async def handle_modal_submit(
        self,
        interaction: discord.Interaction,
        query_text: str,
        response_text: str,
        citations: list,
        user_description: str,
        message_id: Optional[str] = None,
    ) -> None:
        """
        Handle issue report modal submission.
        
        Args:
            interaction: Discord interaction
            query_text: Original query text
            response_text: Bot response text
            citations: List of citations
            user_description: User's description of the issue
            message_id: Optional Discord message ID
        """
        # Phase 8: T062 - Logging for all issue reporting operations
        user_id = str(interaction.user.id) if interaction.user else "unknown"
        username = interaction.user.name if interaction.user else "unknown"
        logger.info(
            "issue_report_submission_start",
            user_id=user_id,
            username=username,
            query_text_length=len(query_text),
            response_text_length=len(response_text),
            user_description_length=len(user_description),
            citation_count=len(citations),
            message_id=message_id
        )
        
        # Create DiscordUser from interaction
        user = DiscordUser(
            user_id=user_id,
            username=username,
            roles=[]  # Will be populated if needed
        )
        
        # Create issue report
        issue_report = IssueReport(
            id=uuid4(),
            query_text=query_text,
            response_text=response_text,
            citations=citations,
            user_description=user_description,
            user_id=user.user_id,
            username=user.username,
            message_id=message_id,
            timestamp=datetime.utcnow(),
        )
        
        # Check for spam
        is_spam, spam_reason = self._detect_spam(issue_report, user)
        if is_spam:
            issue_report.is_spam = True
            issue_report.spam_reason = spam_reason
            logger.warning(
                "issue_report_flagged_as_spam",
                issue_id=str(issue_report.id),
                user_id=user.user_id,
                username=user.username,
                reason=spam_reason,
                query_text_preview=query_text[:50] if query_text else ""
            )
        
        # Save issue report
        try:
            self.issue_storage.save_issue_report(issue_report)
            # Phase 8: T062 - Logging for all issue reporting operations
            logger.info(
                "issue_report_saved",
                issue_id=str(issue_report.id),
                user_id=user.user_id,
                username=user.username,
                is_spam=is_spam,
                spam_reason=spam_reason if is_spam else None,
                timestamp=issue_report.timestamp.isoformat() if issue_report.timestamp else None
            )
        except Exception as e:
            # Phase 8: T062 - Logging for all issue reporting operations
            logger.error(
                "issue_report_save_failed",
                error=str(e),
                error_type=type(e).__name__,
                issue_id=str(issue_report.id),
                user_id=user.user_id,
                username=user.username
            )
            await interaction.response.send_message(
                "❌ Failed to save issue report. Please try again or contact an admin.",
                ephemeral=True
            )
            return
        
        # Phase 8: T062 - Logging for all issue reporting operations
        logger.info(
            "issue_report_submission_complete",
            issue_id=str(issue_report.id),
            user_id=user.user_id,
            username=user.username,
            is_spam=is_spam
        )
        
        # Send confirmation
        await interaction.response.send_message(
            "✅ **Issue report submitted**\n\n"
            "Thank you for reporting this issue. Your feedback helps improve the system.\n\n"
            f"**Report ID:** `{issue_report.id}`\n"
            "Admin will review your report and take appropriate action.",
            ephemeral=True
        )
    
    def _detect_spam(
        self,
        issue_report: IssueReport,
        user: DiscordUser,
    ) -> tuple[bool, Optional[str]]:
        """
        Detect potentially spam or abusive issue reports.
        
        Args:
            issue_report: Issue report to check
            user: User who submitted the report
            
        Returns:
            Tuple of (is_spam, spam_reason)
        """
        # Phase 8: T062 - Logging for all issue reporting operations
        logger.debug(
            "issue_report_spam_check_start",
            user_id=user.user_id,
            username=user.username
        )
        
        # Check for rapid-fire submissions (same user, multiple reports in short time)
        recent_reports = self.issue_storage.get_recent_reports_for_user(
            user.user_id,
            minutes=5
        )
        
        if len(recent_reports) >= 5:
            # Phase 8: T062 - Logging for all issue reporting operations
            logger.warning(
                "issue_report_spam_detected_rapid_fire",
                user_id=user.user_id,
                username=user.username,
                recent_report_count=len(recent_reports)
            )
            return True, "rapid_fire"
        
        # Check for duplicate reports (same query/response pattern)
        duplicate_reports = self.issue_storage.find_duplicate_reports(
            query_text=issue_report.query_text,
            response_text=issue_report.response_text,
        )
        
        if len(duplicate_reports) >= 3:
            # Phase 8: T062 - Logging for all issue reporting operations
            logger.warning(
                "issue_report_spam_detected_duplicate",
                user_id=user.user_id,
                username=user.username,
                duplicate_count=len(duplicate_reports)
            )
            return True, "duplicate"
        
        # Phase 8: T062 - Logging for all issue reporting operations
        logger.debug(
            "issue_report_spam_check_passed",
            user_id=user.user_id,
            username=user.username,
            recent_report_count=len(recent_reports),
            duplicate_count=len(duplicate_reports)
        )
        
        return False, None
    
    def aggregate_issue_reports(
        self,
        query_text: Optional[str] = None,
        response_text: Optional[str] = None,
    ) -> list[IssueReport]:
        """
        Aggregate issue reports by query/response pattern.
        
        Args:
            query_text: Optional query text to filter by
            response_text: Optional response text to filter by
            
        Returns:
            List of aggregated issue reports
        """
        # Phase 8: T062 - Logging for all issue reporting operations
        logger.debug(
            "issue_report_aggregation_start",
            has_query_filter=bool(query_text),
            has_response_filter=bool(response_text)
        )
        
        aggregated = self.issue_storage.find_duplicate_reports(
            query_text=query_text,
            response_text=response_text,
        )
        
        # Phase 8: T062 - Logging for all issue reporting operations
        logger.info(
            "issue_report_aggregation_complete",
            aggregated_count=len(aggregated),
            has_query_filter=bool(query_text),
            has_response_filter=bool(response_text)
        )
        
        return aggregated


class IssueReportModal(discord.ui.Modal, title="Report Issue"):
    """Discord modal form for issue reporting."""
    
    def __init__(
        self,
        query_text: str,
        response_text: str,
        citations: list,
        message_id: Optional[str] = None,
    ):
        """
        Initialize issue report modal.
        
        Args:
            query_text: Original query text
            response_text: Bot response text
            citations: List of citations
            message_id: Optional Discord message ID
        """
        super().__init__()
        self.query_text = query_text
        self.response_text = response_text
        self.citations = citations
        self.message_id = message_id
        
        # Add description input field
        self.description_input = discord.ui.TextInput(
            label="What was incorrect or misleading?",
            placeholder="Describe the issue you found...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.description_input)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        # Phase 8: T062 - Logging for all issue reporting operations
        user_id = str(interaction.user.id) if interaction.user else "unknown"
        logger.debug(
            "issue_report_modal_submit",
            user_id=user_id,
            username=interaction.user.name if interaction.user else "unknown",
            description_length=len(self.description_input.value) if self.description_input.value else 0
        )
        
        # Get issue reporting service (use same instance if available)
        # For now, create new instance - in production, this could be passed via modal
        service = IssueReportingService()
        
        # Submit issue report
        await service.handle_modal_submit(
            interaction=interaction,
            query_text=self.query_text,
            response_text=self.response_text,
            citations=self.citations,
            user_description=self.description_input.value,
            message_id=self.message_id,
        )


def create_issue_reporting_service() -> IssueReportingService:
    """
    Create an issue reporting service instance.
    
    Returns:
        IssueReportingService instance
    """
    return IssueReportingService()


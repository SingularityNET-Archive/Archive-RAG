"""Discord button component for issue reporting."""

from typing import Optional
import discord
from discord.ui import View, Button

from .issue_reporting_service import IssueReportingService, create_issue_reporting_service
from ...models.rag_query import Citation
from ...lib.logging import get_logger

logger = get_logger(__name__)


class IssueReportButtonView(View):
    """
    Discord view containing the "Report Issue" button.
    
    This view can be attached to bot response messages to allow users
    to report incorrect or misleading information.
    """
    
    def __init__(
        self,
        query_text: str,
        response_text: str,
        citations: list,
        message_id: Optional[str] = None,
        issue_reporting_service: Optional[IssueReportingService] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize issue report button view.
        
        Args:
            query_text: Original query text that triggered the response
            response_text: Bot response text
            citations: List of Citation objects or dicts
            message_id: Optional Discord message ID
            issue_reporting_service: Optional IssueReportingService instance
            timeout: Optional view timeout in seconds (default: 15 minutes)
        """
        super().__init__(timeout=timeout or 900)  # 15 minutes default timeout
        
        self.query_text = query_text
        self.response_text = response_text
        self.citations = citations
        self.message_id = message_id
        self.issue_reporting_service = issue_reporting_service or create_issue_reporting_service()
        
        # Convert citations to dict format if needed
        self._normalize_citations()
        
        # Add "Report Issue" button
        self.report_button = Button(
            label="Report Issue",
            style=discord.ButtonStyle.danger,
            emoji="⚠️"
        )
        self.report_button.callback = self._on_report_button_click
        self.add_item(self.report_button)
    
    def _normalize_citations(self) -> None:
        """Normalize citations to dict format for storage."""
        normalized_citations = []
        for citation in self.citations:
            if isinstance(citation, Citation):
                normalized_citations.append({
                    "meeting_id": citation.meeting_id,
                    "date": citation.date,
                    "workgroup_name": citation.workgroup_name,
                    "excerpt": citation.excerpt,
                })
            elif isinstance(citation, dict):
                normalized_citations.append(citation)
            else:
                # Fallback: try to convert to dict
                normalized_citations.append({
                    "meeting_id": str(getattr(citation, "meeting_id", "")),
                    "date": str(getattr(citation, "date", "")),
                    "workgroup_name": getattr(citation, "workgroup_name", None),
                    "excerpt": getattr(citation, "excerpt", ""),
                })
        self.citations = normalized_citations
    
    async def _on_report_button_click(self, interaction: discord.Interaction) -> None:
        """
        Handle "Report Issue" button click.
        
        Opens the issue report modal form.
        
        Args:
            interaction: Discord button interaction
        """
        try:
            logger.info(
                "issue_report_button_clicked",
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                message_id=self.message_id
            )
            
            # Create and show modal
            await self.issue_reporting_service.create_report_modal(
                interaction=interaction,
                query_text=self.query_text,
                response_text=self.response_text,
                citations=self.citations,
                message_id=self.message_id or (str(interaction.message.id) if interaction.message else None),
            )
        except Exception as e:
            logger.error(
                "issue_report_button_click_failed",
                user_id=str(interaction.user.id),
                error=str(e)
            )
            # Try to send error message
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Failed to open issue report form. Please try again or contact an admin.",
                        ephemeral=True
                    )
            except Exception as send_error:
                logger.error("failed_to_send_button_error", error=str(send_error))
    
    async def on_timeout(self) -> None:
        """Handle view timeout - disable the button."""
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True
        logger.debug("issue_report_button_view_timed_out", message_id=self.message_id)


def create_issue_report_button_view(
    query_text: str,
    response_text: str,
    citations: list,
    message_id: Optional[str] = None,
) -> IssueReportButtonView:
    """
    Create an issue report button view.
    
    Args:
        query_text: Original query text
        response_text: Bot response text
        citations: List of citations
        message_id: Optional Discord message ID
        
    Returns:
        IssueReportButtonView instance
    """
    return IssueReportButtonView(
        query_text=query_text,
        response_text=response_text,
        citations=citations,
        message_id=message_id,
    )



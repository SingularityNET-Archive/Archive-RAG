"""Admin command for reviewing issue reports."""

import asyncio
from datetime import datetime
from typing import Optional, List
from uuid import UUID

import discord
from discord import app_commands
from discord.ui import View, Button, Select

from ..models.discord_user import DiscordUser
from ..bot import ArchiveRAGBot
from ..services.rate_limiter import RateLimiter
from ..services.permission_checker import PermissionChecker
from ..services.message_formatter import MessageFormatter
from ..services.issue_storage import IssueStorage, create_issue_storage
from src.lib.logging import get_logger
from src.bot.models.issue_report import IssueReport

logger = get_logger(__name__)


class ReportsCommand:
    """
    Command handler for /archive reports slash command.
    
    Admin-only command for reviewing and managing issue reports.
    """
    
    def __init__(
        self,
        bot: discord.Client,
        rate_limiter: RateLimiter,
        permission_checker: PermissionChecker,
        message_formatter: MessageFormatter,
        issue_storage: Optional[IssueStorage] = None,
    ):
        """
        Initialize reports command handler.
        
        Args:
            bot: Discord bot client
            rate_limiter: Rate limiter service
            permission_checker: Permission checker service
            message_formatter: Message formatter service
            issue_storage: Optional IssueStorage instance
        """
        self.bot = bot
        self.rate_limiter = rate_limiter
        self.permission_checker = permission_checker
        self.message_formatter = message_formatter
        self.issue_storage = issue_storage or create_issue_storage()
        
        logger.info("reports_command_initialized")
    
    def _create_discord_user(self, interaction: discord.Interaction) -> DiscordUser:
        """Create DiscordUser from Discord interaction."""
        roles = []
        if interaction.user and hasattr(interaction.user, 'roles'):
            member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
            if member:
                roles = [role.name.lower() for role in member.roles if role.name != "@everyone"]
        
        return DiscordUser(
            user_id=str(interaction.user.id),
            username=interaction.user.name,
            roles=roles
        )
    
    def _format_report_summary(self, report: IssueReport, index: int = None) -> str:
        """
        Format a report summary for listing.
        
        Args:
            report: IssueReport to format
            index: Optional index number
            
        Returns:
            Formatted summary string
        """
        prefix = f"{index}. " if index is not None else ""
        status = "✅ Resolved" if report.is_resolved else "🔴 Open"
        spam = " ⚠️ SPAM" if report.is_spam else ""
        timestamp = report.timestamp.strftime("%Y-%m-%d %H:%M")
        
        query_preview = report.query_text[:50] + "..." if len(report.query_text) > 50 else report.query_text
        
        return (
            f"{prefix}**{status}**{spam}\n"
            f"**Report ID:** `{report.id}`\n"
            f"**User:** {report.username} ({report.user_id})\n"
            f"**Query:** {query_preview}\n"
            f"**Reported:** {timestamp}\n"
        )
    
    def _format_report_details(self, report: IssueReport) -> str:
        """
        Format full report details.
        
        Args:
            report: IssueReport to format
            
        Returns:
            Formatted details string
        """
        status = "✅ Resolved" if report.is_resolved else "🔴 Open"
        spam = " ⚠️ **SPAM**" if report.is_spam else ""
        timestamp = report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        resolved_info = ""
        if report.is_resolved and report.resolved_at:
            resolved_info = f"\n**Resolved:** {report.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        admin_notes = ""
        if report.admin_notes:
            admin_notes = f"\n**Admin Notes:** {report.admin_notes}"
        
        spam_reason = ""
        if report.spam_reason:
            spam_reason = f"\n**Spam Reason:** {report.spam_reason}"
        
        citations_text = ""
        if report.citations:
            citations_text = "\n**Citations:**\n"
            for i, citation in enumerate(report.citations, 1):
                meeting_id = citation.get("meeting_id", "unknown")
                date = citation.get("date", "unknown")
                workgroup = citation.get("workgroup_name", "unknown")
                citations_text += f"{i}. [{meeting_id} | {date} | {workgroup}]\n"
        
        return (
            f"**Issue Report Details**\n"
            f"**Status:** {status}{spam}{spam_reason}\n"
            f"**Report ID:** `{report.id}`\n"
            f"**User:** {report.username} ({report.user_id})\n"
            f"**Reported:** {timestamp}{resolved_info}\n"
            f"\n**Original Query:**\n{report.query_text}\n"
            f"\n**Bot Response:**\n{report.response_text[:500]}{'...' if len(report.response_text) > 500 else ''}\n"
            f"{citations_text}"
            f"\n**User Description:**\n{report.user_description}\n"
            f"{admin_notes}"
        )
    
    async def handle_list_reports(
        self,
        interaction: discord.Interaction,
        status: Optional[str] = None,
        include_spam: bool = False,
    ) -> None:
        """
        Handle listing issue reports.
        
        Args:
            interaction: Discord interaction
            status: Optional status filter ("open", "resolved", "all")
            include_spam: Whether to include spam reports
        """
        try:
            discord_user = self._create_discord_user(interaction)
            
            # Check admin permission
            if not self.permission_checker.has_permission(discord_user, "archive reports"):
                await interaction.response.send_message(
                    self.message_formatter.format_error_message("admin_only"),
                    ephemeral=True
                )
                return
            
            await interaction.response.send_message("Loading issue reports...")
            
            # Get reports
            resolved_only = status == "resolved" if status else False
            reports = await asyncio.to_thread(
                self.issue_storage.get_all_reports,
                include_spam=include_spam,
                resolved_only=resolved_only
            )
            
            # Filter by status if needed
            if status == "open":
                reports = [r for r in reports if not r.is_resolved]
            elif status == "resolved":
                reports = [r for r in reports if r.is_resolved]
            # "all" means no additional filtering
            
            if not reports:
                await interaction.followup.send(
                    f"**No issue reports found**\n\n"
                    f"Filter: {status or 'all'}, Spam: {'included' if include_spam else 'excluded'}"
                )
                return
            
            # Format report list (limit to 10 for display)
            display_reports = reports[:10]
            response_lines = [
                f"**Issue Reports** ({len(reports)} total, showing {len(display_reports)})\n"
            ]
            
            for i, report in enumerate(display_reports, 1):
                response_lines.append(self._format_report_summary(report, index=i))
            
            if len(reports) > 10:
                response_lines.append(f"\n*Showing first 10 of {len(reports)} reports. Use `/archive reports view` to see details.*")
            
            response_text = "\n".join(response_lines)
            
            # Create interactive view with report selector
            view = ReportListView(
                reports=reports,
                issue_storage=self.issue_storage,
                message_formatter=self.message_formatter,
            )
            
            await interaction.followup.send(response_text, view=view)
            
            logger.info(
                "reports_listed",
                user_id=discord_user.user_id,
                report_count=len(reports),
                status=status,
                include_spam=include_spam
            )
            
        except Exception as e:
            logger.error("reports_list_failed", error=str(e))
            await interaction.followup.send(
                self.message_formatter.format_error_message("generic"),
                ephemeral=True
            )
    
    async def handle_view_report(
        self,
        interaction: discord.Interaction,
        report_id: str,
    ) -> None:
        """
        Handle viewing a specific report's details.
        
        Args:
            interaction: Discord interaction
            report_id: Report UUID string
        """
        try:
            discord_user = self._create_discord_user(interaction)
            
            # Check admin permission
            if not self.permission_checker.has_permission(discord_user, "archive reports"):
                await interaction.response.send_message(
                    self.message_formatter.format_error_message("admin_only"),
                    ephemeral=True
                )
                return
            
            await interaction.response.send_message("Loading report details...")
            
            # Load report
            try:
                parsed_id = UUID(report_id)
            except ValueError:
                await interaction.followup.send(f"❌ Invalid report ID format: `{report_id}`")
                return
            
            report = await asyncio.to_thread(
                self.issue_storage.load_issue_report,
                parsed_id
            )
            
            if not report:
                await interaction.followup.send(f"❌ Report not found: `{report_id}`")
                return
            
            # Format details
            details_text = self._format_report_details(report)
            
            # Create interactive view with actions
            view = ReportDetailView(
                report=report,
                issue_storage=self.issue_storage,
                message_formatter=self.message_formatter,
            )
            
            # Split if too long (Discord has 2000 char limit)
            if len(details_text) > 2000:
                from ..utils.message_splitter import split_text
                chunks = split_text(details_text, max_length=2000)
                for i, chunk in enumerate(chunks):
                    if i == len(chunks) - 1:
                        await interaction.followup.send(chunk, view=view)
                    else:
                        await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(details_text, view=view)
            
            logger.info(
                "report_viewed",
                user_id=discord_user.user_id,
                report_id=report_id
            )
            
        except Exception as e:
            logger.error("report_view_failed", error=str(e), report_id=report_id)
            await interaction.followup.send(
                self.message_formatter.format_error_message("generic"),
                ephemeral=True
            )


class ReportListView(View):
    """Interactive view for listing reports with selection."""
    
    def __init__(
        self,
        reports: List[IssueReport],
        issue_storage: IssueStorage,
        message_formatter: MessageFormatter,
    ):
        """
        Initialize report list view.
        
        Args:
            reports: List of IssueReport objects
            issue_storage: IssueStorage service
            message_formatter: MessageFormatter service
        """
        super().__init__(timeout=300)  # 5 minutes
        
        self.reports = reports
        self.issue_storage = issue_storage
        self.message_formatter = message_formatter
        
        # Add report selector
        if reports:
            options = []
            for report in reports[:25]:  # Discord limit is 25 options
                status = "✅" if report.is_resolved else "🔴"
                spam = " ⚠️" if report.is_spam else ""
                query_preview = report.query_text[:50] + "..." if len(report.query_text) > 50 else report.query_text
                label = f"{status}{spam} {query_preview}"
                options.append(
                    discord.SelectOption(
                        label=label[:100],  # Discord limit is 100 chars
                        value=str(report.id),
                        description=f"By {report.username} • {report.timestamp.strftime('%Y-%m-%d')}"[:100]
                    )
                )
            
            self.report_select = Select(
                placeholder="Select a report to view details...",
                options=options,
                min_values=1,
                max_values=1
            )
            self.report_select.callback = self._on_report_selected
            self.add_item(self.report_select)
    
    async def _on_report_selected(self, interaction: discord.Interaction) -> None:
        """Handle report selection."""
        selected_id = interaction.data["values"][0]
        
        try:
            report_id = UUID(selected_id)
            report = await asyncio.to_thread(
                self.issue_storage.load_issue_report,
                report_id
            )
            
            if not report:
                await interaction.response.send_message(
                    f"❌ Report not found: `{selected_id}`",
                    ephemeral=True
                )
                return
            
            # Format details
            details_text = self._format_report_details(report)
            
            # Create detail view
            detail_view = ReportDetailView(
                report=report,
                issue_storage=self.issue_storage,
                message_formatter=self.message_formatter,
            )
            
            # Send details (Discord has 2000 char limit)
            if len(details_text) > 2000:
                from ..utils.message_splitter import split_text
                chunks = split_text(details_text, max_length=2000)
                await interaction.response.send_message(chunks[0], ephemeral=True)
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk, ephemeral=True)
                await interaction.followup.send(view=detail_view, ephemeral=True)
            else:
                await interaction.response.send_message(details_text, view=detail_view, ephemeral=True)
                
        except Exception as e:
            logger.error("report_selection_failed", error=str(e))
            await interaction.response.send_message(
                "❌ Failed to load report details.",
                ephemeral=True
            )
    
    def _format_report_details(self, report: IssueReport) -> str:
        """Format report details (same as ReportsCommand method)."""
        status = "✅ Resolved" if report.is_resolved else "🔴 Open"
        spam = " ⚠️ **SPAM**" if report.is_spam else ""
        timestamp = report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        resolved_info = ""
        if report.is_resolved and report.resolved_at:
            resolved_info = f"\n**Resolved:** {report.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        admin_notes = ""
        if report.admin_notes:
            admin_notes = f"\n**Admin Notes:** {report.admin_notes}"
        
        spam_reason = ""
        if report.spam_reason:
            spam_reason = f"\n**Spam Reason:** {report.spam_reason}"
        
        citations_text = ""
        if report.citations:
            citations_text = "\n**Citations:**\n"
            for i, citation in enumerate(report.citations, 1):
                meeting_id = citation.get("meeting_id", "unknown")
                date = citation.get("date", "unknown")
                workgroup = citation.get("workgroup_name", "unknown")
                citations_text += f"{i}. [{meeting_id} | {date} | {workgroup}]\n"
        
        return (
            f"**Issue Report Details**\n"
            f"**Status:** {status}{spam}{spam_reason}\n"
            f"**Report ID:** `{report.id}`\n"
            f"**User:** {report.username} ({report.user_id})\n"
            f"**Reported:** {timestamp}{resolved_info}\n"
            f"\n**Original Query:**\n{report.query_text}\n"
            f"\n**Bot Response:**\n{report.response_text[:500]}{'...' if len(report.response_text) > 500 else ''}\n"
            f"{citations_text}"
            f"\n**User Description:**\n{report.user_description}\n"
            f"{admin_notes}"
        )


class ReportDetailView(View):
    """Interactive view for report details with actions."""
    
    def __init__(
        self,
        report: IssueReport,
        issue_storage: IssueStorage,
        message_formatter: MessageFormatter,
    ):
        """
        Initialize report detail view.
        
        Args:
            report: IssueReport to display
            issue_storage: IssueStorage service
            message_formatter: MessageFormatter service
        """
        super().__init__(timeout=300)  # 5 minutes
        
        self.report = report
        self.issue_storage = issue_storage
        self.message_formatter = message_formatter
        
        # Add action buttons
        if not report.is_resolved:
            resolve_button = Button(
                label="Mark as Resolved",
                style=discord.ButtonStyle.success,
                emoji="✅"
            )
            resolve_button.callback = self._on_resolve
            self.add_item(resolve_button)
        
        # Always show back button
        back_button = Button(
            label="Back to List",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️"
        )
        back_button.callback = self._on_back
        self.add_item(back_button)
    
    async def _on_resolve(self, interaction: discord.Interaction) -> None:
        """Handle marking report as resolved."""
        try:
            # Update report
            self.report.is_resolved = True
            self.report.resolved_at = datetime.utcnow()
            
            # Save
            await asyncio.to_thread(
                self.issue_storage.update_issue_report,
                self.report
            )
            
            await interaction.response.send_message(
                f"✅ Report `{self.report.id}` marked as resolved.",
                ephemeral=True
            )
            
            logger.info(
                "report_resolved",
                report_id=str(self.report.id),
                user_id=str(interaction.user.id)
            )
            
            # Update view (disable resolve button)
            for item in self.children:
                if isinstance(item, Button) and item.label == "Mark as Resolved":
                    item.disabled = True
                    break
            
            await interaction.message.edit(view=self)
            
        except Exception as e:
            logger.error("report_resolve_failed", error=str(e))
            await interaction.response.send_message(
                "❌ Failed to mark report as resolved.",
                ephemeral=True
            )
    
    async def _on_back(self, interaction: discord.Interaction) -> None:
        """Handle back button - return to list."""
        # Get all reports
        reports = await asyncio.to_thread(
            self.issue_storage.get_all_reports,
            include_spam=False,
            resolved_only=False
        )
        
        if not reports:
            await interaction.response.send_message(
                "No open reports found.",
                ephemeral=True
            )
            return
        
        # Format list
        response_lines = [
            f"**Issue Reports** ({len(reports)} total, showing {min(10, len(reports))})\n"
        ]
        
        for i, report in enumerate(reports[:10], 1):
            status = "✅ Resolved" if report.is_resolved else "🔴 Open"
            spam = " ⚠️ SPAM" if report.is_spam else ""
            timestamp = report.timestamp.strftime("%Y-%m-%d %H:%M")
            query_preview = report.query_text[:50] + "..." if len(report.query_text) > 50 else report.query_text
            
            response_lines.append(
                f"{i}. **{status}**{spam}\n"
                f"**Report ID:** `{report.id}`\n"
                f"**User:** {report.username} ({report.user_id})\n"
                f"**Query:** {query_preview}\n"
                f"**Reported:** {timestamp}\n"
            )
        
        response_text = "\n".join(response_lines)
        
        # Create list view
        list_view = ReportListView(
            reports=reports,
            issue_storage=self.issue_storage,
            message_formatter=self.message_formatter,
        )
        
        await interaction.response.send_message(response_text, view=list_view, ephemeral=True)


def register_reports_command(
    bot: ArchiveRAGBot,
    rate_limiter: RateLimiter,
    permission_checker: PermissionChecker,
    message_formatter: MessageFormatter,
    issue_storage: Optional[IssueStorage] = None,
) -> None:
    """
    Register /archive reports command with Discord bot.
    
    Args:
        bot: ArchiveRAGBot instance
        rate_limiter: RateLimiter service
        permission_checker: PermissionChecker service
        message_formatter: MessageFormatter service
        issue_storage: Optional IssueStorage instance
    """
    command_handler = ReportsCommand(
        bot=bot,
        rate_limiter=rate_limiter,
        permission_checker=permission_checker,
        message_formatter=message_formatter,
        issue_storage=issue_storage,
    )
    
    # Find existing archive group (should already exist from other command registrations)
    archive_group = None
    for command in bot.tree.get_commands():
        if command.name == "archive":
            archive_group = command
            break
    
    if archive_group is None:
        # Create archive group if it doesn't exist
        archive_group = app_commands.Group(name="archive", description="Archive-RAG commands")
        try:
            bot.tree.add_command(archive_group)
        except Exception as e:
            # If it already exists (race condition), find it again
            logger.debug("archive_group_add_failed_finding_again", error=str(e))
            for command in bot.tree.get_commands():
                if command.name == "archive":
                    archive_group = command
                    break
            if archive_group is None:
                # If we still can't find it, re-raise the error
                raise
    
    # Check if reports group already exists
    reports_group = None
    if hasattr(archive_group, 'commands'):
        for cmd in archive_group.commands:
            if cmd.name == "reports":
                reports_group = cmd
                break
    
    # Create reports subcommand group if it doesn't exist
    if reports_group is None:
        reports_group = app_commands.Group(
            name="reports",
            description="Admin commands for reviewing issue reports",
            parent=archive_group
        )
        
        @reports_group.command(name="list", description="List issue reports (admin only)")
        @app_commands.describe(
            status="Filter by status (open, resolved, all)",
            include_spam="Whether to include spam reports"
        )
        @app_commands.choices(status=[
            app_commands.Choice(name="Open", value="open"),
            app_commands.Choice(name="Resolved", value="resolved"),
            app_commands.Choice(name="All", value="all"),
        ])
        async def reports_list(
            interaction: discord.Interaction,
            status: Optional[str] = None,
            include_spam: bool = False,
        ):
            """Execute /archive reports list command."""
            await command_handler.handle_list_reports(
                interaction,
                status=status,
                include_spam=include_spam,
            )
        
        @reports_group.command(name="view", description="View a specific issue report (admin only)")
        @app_commands.describe(report_id="Report UUID to view")
        async def reports_view(
            interaction: discord.Interaction,
            report_id: str,
        ):
            """Execute /archive reports view command."""
            await command_handler.handle_view_report(
                interaction,
                report_id=report_id,
            )
        
        # When parent is set in Group constructor, it's automatically added to the parent
        # No need to explicitly call add_command


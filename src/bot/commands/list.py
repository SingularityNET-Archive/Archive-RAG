"""List command handler for /archive list slash command."""

import asyncio
import re
from datetime import datetime, date
from typing import Optional, List

import discord
from discord import app_commands

from ..models.discord_user import DiscordUser
from ..bot import ArchiveRAGBot
from ..services.rate_limiter import RateLimiter
from ..services.permission_checker import PermissionChecker
from ..services.message_formatter import MessageFormatter
from src.services.entity_query import EntityQueryService
from src.lib.logging import get_logger

logger = get_logger(__name__)


class ListCommand:
    """
    Command handler for /archive list slash command.
    
    Handles natural language list queries for entities (topics, meetings, etc.).
    """
    
    def __init__(
        self,
        bot: discord.Client,
        rate_limiter: RateLimiter,
        permission_checker: PermissionChecker,
        message_formatter: MessageFormatter,
        entity_query_service: EntityQueryService
    ):
        """
        Initialize list command handler.
        
        Args:
            bot: Discord bot client
            rate_limiter: Rate limiter service
            permission_checker: Permission checker service
            message_formatter: Message formatter service
            entity_query_service: Entity query service
        """
        self.bot = bot
        self.rate_limiter = rate_limiter
        self.permission_checker = permission_checker
        self.message_formatter = message_formatter
        self.entity_query_service = entity_query_service
    
    def _create_discord_user(self, interaction: discord.Interaction) -> DiscordUser:
        """
        Create DiscordUser from Discord interaction.
        
        Args:
            interaction: Discord interaction
            
        Returns:
            DiscordUser model
        """
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
    
    def _parse_date_from_query(self, query: str) -> tuple[Optional[int], Optional[int]]:
        """
        Parse year and month from natural language query.
        
        Examples:
            "March 2025" -> (2025, 3)
            "2025" -> (2025, None)
            "meetings in March" -> (None, 3)
        
        Args:
            query: Natural language query text
            
        Returns:
            Tuple of (year, month) or (None, None) if not found
        """
        query_lower = query.lower()
        
        # Month names mapping
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        year = None
        month = None
        
        # Find year (4-digit number)
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        if year_match:
            year = int(year_match.group())
        
        # Find month name
        for month_name, month_num in months.items():
            if month_name in query_lower:
                month = month_num
                break
        
        # If month found but no year, try to find current year context
        if month and not year:
            # Use current year as default
            year = datetime.now().year
        
        return year, month
    
    def _format_topics_list(self, topics: List[str], limit: int = 50) -> str:
        """
        Format list of topics for Discord message.
        
        Args:
            topics: List of topic strings
            limit: Maximum number of topics to show
            
        Returns:
            Formatted message text
        """
        if not topics:
            return "**Topics:**\n\nNo topics found in the archive."
        
        response_lines = [f"**Topics:** ({len(topics)} total)\n"]
        
        # Show up to limit topics
        topics_to_show = topics[:limit]
        for i, topic in enumerate(topics_to_show, 1):
            response_lines.append(f"{i}. {topic}")
        
        if len(topics) > limit:
            response_lines.append(f"\n_(Showing first {limit} of {len(topics)} topics)_")
        
        return "\n".join(response_lines)
    
    def _format_meetings_list(self, meetings: List, limit: int = 20) -> str:
        """
        Format list of meetings for Discord message.
        
        Args:
            meetings: List of Meeting entities
            limit: Maximum number of meetings to show
            
        Returns:
            Formatted message text
        """
        if not meetings:
            return "**Meetings:**\n\nNo meetings found matching your criteria."
        
        response_lines = [f"**Meetings:** ({len(meetings)} total)\n"]
        
        # Show up to limit meetings
        meetings_to_show = meetings[:limit]
        for i, meeting in enumerate(meetings_to_show, 1):
            citation = self.message_formatter.format_meeting_citation(meeting)
            response_lines.append(f"{i}. {citation}")
        
        if len(meetings) > limit:
            response_lines.append(f"\n_(Showing first {limit} of {len(meetings)} meetings)_")
        
        return "\n".join(response_lines)
    
    def _detect_list_type(self, query: str) -> str:
        """
        Detect what type of list is being requested from natural language.
        
        Args:
            query: Natural language query text
            
        Returns:
            Type of list: "topics", "meetings", or "unknown"
        """
        query_lower = query.lower()
        
        # Check for topics
        if any(word in query_lower for word in ["topic", "tag", "extant topics", "all topics", "list topics"]):
            return "topics"
        
        # Check for meetings
        if any(word in query_lower for word in ["meeting", "meetings", "list meetings"]):
            return "meetings"
        
        return "unknown"
    
    async def handle_list_command(
        self,
        interaction: discord.Interaction,
        query: str
    ) -> None:
        """
        Handle /archive list command execution.
        
        Args:
            interaction: Discord interaction
            query: Natural language list query (e.g., "List extant topics", "List meetings in March 2025")
        """
        start_time = datetime.utcnow()
        
        try:
            # Create DiscordUser from interaction
            discord_user = self._create_discord_user(interaction)
            
            # Send immediate acknowledgment
            await interaction.response.send_message("Processing your list query...")
            
            # Check permissions (public access for list queries)
            # Note: Could restrict to contributor+ if needed
            
            # Check rate limit
            is_allowed, remaining_seconds = self.rate_limiter.check_rate_limit(discord_user.user_id)
            if not is_allowed:
                error_message = self.message_formatter.format_error_message(
                    "rate_limit",
                    str(remaining_seconds) if remaining_seconds else None
                )
                await interaction.followup.send(error_message)
                logger.warning(
                    "list_rate_limit_exceeded",
                    user_id=discord_user.user_id,
                    username=discord_user.username,
                    remaining_seconds=remaining_seconds
                )
                return
            
            # Record query for rate limiting
            self.rate_limiter.record_query(discord_user.user_id)
            
            # Detect list type
            list_type = self._detect_list_type(query)
            
            # Handle topics list
            if list_type == "topics":
                try:
                    topics = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.entity_query_service.get_all_topics
                        ),
                        timeout=30.0
                    )
                    response_text = self._format_topics_list(topics)
                    await interaction.followup.send(response_text)
                    
                    execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    execution_time_seconds = execution_time_ms / 1000.0
                    performance_status = "within_target" if execution_time_seconds < 3.0 else "exceeded_target"
                    
                    logger.info(
                        "list_topics_executed",
                        user_id=discord_user.user_id,
                        username=discord_user.username,
                        topic_count=len(topics),
                        execution_time_ms=execution_time_ms,
                        execution_time_seconds=round(execution_time_seconds, 2),
                        performance_status=performance_status,
                        command="archive list"
                    )
                    
                    if execution_time_seconds >= 3.0:
                        logger.warning(
                            "list_topics_performance_exceeded_target",
                            execution_time_seconds=round(execution_time_seconds, 2),
                            target_seconds=3.0
                        )
                    return
                except asyncio.TimeoutError:
                    await interaction.followup.send(
                        self.message_formatter.format_error_message("timeout", "30")
                    )
                    return
                except Exception as e:
                    logger.error(
                        "list_topics_failed",
                        user_id=discord_user.user_id,
                        error=str(e)
                    )
                    await interaction.followup.send(
                        self.message_formatter.format_error_message("generic")
                    )
                    return
            
            # Handle meetings list
            elif list_type == "meetings":
                try:
                    # Parse date from query
                    year, month = self._parse_date_from_query(query)
                    
                    meetings = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.entity_query_service.get_meetings_by_date_range,
                            year=year,
                            month=month
                        ),
                        timeout=30.0
                    )
                    
                    response_text = self._format_meetings_list(meetings)
                    await interaction.followup.send(response_text)
                    
                    execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    execution_time_seconds = execution_time_ms / 1000.0
                    performance_status = "within_target" if execution_time_seconds < 3.0 else "exceeded_target"
                    
                    logger.info(
                        "list_meetings_executed",
                        user_id=discord_user.user_id,
                        username=discord_user.username,
                        meeting_count=len(meetings),
                        year=year,
                        month=month,
                        execution_time_ms=execution_time_ms,
                        execution_time_seconds=round(execution_time_seconds, 2),
                        performance_status=performance_status,
                        command="archive list"
                    )
                    
                    if execution_time_seconds >= 3.0:
                        logger.warning(
                            "list_meetings_performance_exceeded_target",
                            year=year,
                            month=month,
                            execution_time_seconds=round(execution_time_seconds, 2),
                            target_seconds=3.0
                        )
                    return
                except asyncio.TimeoutError:
                    await interaction.followup.send(
                        self.message_formatter.format_error_message("timeout", "30")
                    )
                    return
                except Exception as e:
                    logger.error(
                        "list_meetings_failed",
                        user_id=discord_user.user_id,
                        error=str(e)
                    )
                    await interaction.followup.send(
                        self.message_formatter.format_error_message("generic")
                    )
                    return
            
            # Unknown list type
            else:
                error_message = (
                    "❓ **Unable to determine list type**\n\n"
                    "I can help you list:\n"
                    "• **Topics** - Use queries like \"List topics\" or \"List extant topics\"\n"
                    "• **Meetings** - Use queries like \"List meetings in March 2025\" or \"List meetings in 2025\"\n\n"
                    "**Examples:**\n"
                    "• `/archive list query:\"List extant topics\"`\n"
                    "• `/archive list query:\"List meetings in March 2025\"`\n"
                    "• `/archive list query:\"List meetings in 2025\"`"
                )
                await interaction.followup.send(error_message)
                logger.info(
                    "list_unknown_type",
                    user_id=discord_user.user_id,
                    query=query
                )
                return
            
        except Exception as e:
            logger.error(
                "list_command_error",
                user_id=discord_user.user_id if 'discord_user' in locals() else "unknown",
                query=query,
                error=str(e)
            )
            
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        self.message_formatter.format_error_message("generic")
                    )
                else:
                    await interaction.response.send_message(
                        self.message_formatter.format_error_message("generic")
                    )
            except Exception as send_error:
                logger.error("failed_to_send_error_message", error=str(send_error))


def register_list_command(
    bot: ArchiveRAGBot,
    rate_limiter: RateLimiter,
    permission_checker: PermissionChecker,
    message_formatter: MessageFormatter,
    entity_query_service: EntityQueryService
) -> None:
    """
    Register /archive list command with Discord bot.
    
    Args:
        bot: Discord bot client
        rate_limiter: Rate limiter service
        permission_checker: Permission checker service
        message_formatter: Message formatter service
        entity_query_service: Entity query service
    """
    command_handler = ListCommand(
        bot=bot,
        rate_limiter=rate_limiter,
        permission_checker=permission_checker,
        message_formatter=message_formatter,
        entity_query_service=entity_query_service
    )
    
    # Get or create the archive command group
    archive_group = None
    for command in bot.tree.get_commands():
        if command.name == "archive":
            archive_group = command
            break
    
    if archive_group is None:
        # Create archive group if it doesn't exist
        archive_group = app_commands.Group(name="archive", description="Archive-RAG commands")
        bot.tree.add_command(archive_group)
    
    # Register list command
    @archive_group.command(name="list", description="List entities (topics, meetings, etc.) using natural language")
    async def list_command(interaction: discord.Interaction, query: str):
        """Execute /archive list command."""
        await command_handler.handle_list_command(interaction, query)


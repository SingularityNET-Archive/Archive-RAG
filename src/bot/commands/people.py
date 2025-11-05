"""People command handler for /archive people slash command."""

import asyncio
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands

from ..models.discord_user import DiscordUser
from ..bot import ArchiveRAGBot
from ..services.rate_limiter import RateLimiter
from ..services.permission_checker import PermissionChecker
from ..services.message_formatter import MessageFormatter
from src.services.entity_query import EntityQueryService
from src.lib.config import ENTITIES_PEOPLE_DIR
from src.models.person import Person
from src.lib.logging import get_logger

logger = get_logger(__name__)


class PeopleCommand:
    """
    Command handler for /archive people slash command.
    
    Handles people/participant searches in archived meetings (contributor+ only).
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
        Initialize people command handler.
        
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
        # Extract roles from interaction
        roles = []
        if interaction.user and hasattr(interaction.user, 'roles'):
            # Get role names from guild member
            member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
            if member:
                roles = [role.name.lower() for role in member.roles if role.name != "@everyone"]
        
        return DiscordUser(
            user_id=str(interaction.user.id),
            username=interaction.user.name,
            roles=roles
        )
    
    def _format_people_response(self, person: Person, meetings: list) -> str:
        """
        Format people search results for Discord.
        
        Args:
            person: Person entity found
            meetings: List of Meeting entities (limited to top 5)
            
        Returns:
            Formatted response text
        """
        response_lines = [f"**Person:** {person.display_name}"]
        
        if person.alias:
            response_lines.append(f"**Alias:** {person.alias}")
        
        if person.role:
            response_lines.append(f"**Role:** {person.role}")
        
        response_lines.append("")
        
        if not meetings:
            response_lines.append("No meetings found for this person.")
            return "\n".join(response_lines)
        
        response_lines.append("**Mentions:**")
        
        # Limit to top 5
        meetings = meetings[:5]
        
        for i, meeting in enumerate(meetings, 1):
            # Format meeting citation
            citation = self.message_formatter.format_meeting_citation(meeting)
            response_lines.append(f"{i}. {citation}")
        
        if len(meetings) == 5:
            response_lines.append("")
            response_lines.append("(Showing top 5 results)")
        
        return "\n".join(response_lines)
    
    async def handle_people_command(
        self,
        interaction: discord.Interaction,
        person: str
    ) -> None:
        """
        Handle /archive people command execution.
        
        Args:
            interaction: Discord interaction
            person: Person name to search for
        """
        start_time = datetime.utcnow()
        error_occurred = False
        rate_limit_status = "allowed"
        
        try:
            # Create DiscordUser from interaction
            discord_user = self._create_discord_user(interaction)
            
            # Send immediate acknowledgment
            await interaction.response.send_message("Processing your people search...")
            
            # Check permissions (contributor+ required)
            if not self.permission_checker.has_permission(discord_user, "archive people"):
                error_message = self.message_formatter.format_error_message("permission_denied")
                await interaction.followup.send(error_message)
                logger.warning(
                    "people_permission_denied",
                    user_id=discord_user.user_id,
                    username=discord_user.username
                )
                return
            
            # Check rate limit
            is_allowed, remaining_seconds = self.rate_limiter.check_rate_limit(discord_user.user_id)
            if not is_allowed:
                rate_limit_status = "exceeded"
                error_message = self.message_formatter.format_error_message(
                    "rate_limit",
                    str(remaining_seconds) if remaining_seconds else None
                )
                await interaction.followup.send(error_message)
                logger.warning(
                    "people_rate_limit_exceeded",
                    user_id=discord_user.user_id,
                    username=discord_user.username,
                    remaining_seconds=remaining_seconds
                )
                return
            
            # Record query for rate limiting
            self.rate_limiter.record_query(discord_user.user_id)
            
            # Find person by name (case-insensitive search)
            # Try display_name first, then alias
            person_entity = None
            try:
                # Search by display_name with timeout
                person_entity = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.entity_query_service.find_by_name,
                        person,
                        ENTITIES_PEOPLE_DIR,
                        Person,
                        "display_name"
                    ),
                    timeout=30.0  # 30 second timeout
                )
                
                # If not found, try searching by alias
                if not person_entity:
                    all_people = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.entity_query_service.find_all,
                            ENTITIES_PEOPLE_DIR,
                            Person
                        ),
                        timeout=30.0
                    )
                    # Case-insensitive search
                    person_lower = person.lower()
                    for p in all_people:
                        if (p.display_name and person_lower in p.display_name.lower()) or \
                           (p.alias and person_lower in p.alias.lower()):
                            person_entity = p
                            break
            except asyncio.TimeoutError:
                error_occurred = True
                await interaction.followup.send(
                    self.message_formatter.format_error_message("timeout", "30")
                )
                logger.error(
                    "people_search_timeout",
                    user_id=discord_user.user_id,
                    person=person
                )
                return
            except Exception as e:
                error_occurred = True
                await interaction.followup.send(
                    self.message_formatter.format_error_message("generic")
                )
                logger.error(
                    "people_search_failed",
                    user_id=discord_user.user_id,
                    person=person,
                    error=str(e)
                )
                return
            
            if not person_entity:
                error_message = f"No person found matching '{person}'. Try a different search term."
                await interaction.followup.send(error_message)
                logger.info(
                    "people_no_results",
                    user_id=discord_user.user_id,
                    person=person
                )
                return
            
            # Get meetings for this person
            try:
                meetings = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.entity_query_service.get_meetings_by_person,
                        person_entity.id
                    ),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                error_occurred = True
                await interaction.followup.send(
                    self.message_formatter.format_error_message("timeout", "30")
                )
                logger.error(
                    "people_meetings_timeout",
                    user_id=discord_user.user_id,
                    person_id=str(person_entity.id)
                )
                return
            except Exception as e:
                error_occurred = True
                await interaction.followup.send(
                    self.message_formatter.format_error_message("generic")
                )
                logger.error(
                    "people_meetings_failed",
                    user_id=discord_user.user_id,
                    person_id=str(person_entity.id),
                    error=str(e)
                )
                return
            
            # Format and send response
            response_text = self._format_people_response(person_entity, meetings)
            await interaction.followup.send(response_text)
            
            # Audit logging and Performance Monitoring (T035, T047)
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            execution_time_seconds = execution_time_ms / 1000.0
            performance_status = "within_target" if execution_time_seconds < 3.0 else "exceeded_target"
            
            logger.info(
                "people_command_executed",
                user_id=discord_user.user_id,
                username=discord_user.username,
                person=person,
                person_id=str(person_entity.id),
                meeting_count=len(meetings) if meetings else 0,
                execution_time_ms=execution_time_ms,
                execution_time_seconds=round(execution_time_seconds, 2),
                performance_status=performance_status,
                command="archive people"
            )
            
            # Performance monitoring warning
            if execution_time_seconds >= 3.0:
                logger.warning(
                    "people_performance_exceeded_target",
                    person=person,
                    execution_time_seconds=round(execution_time_seconds, 2),
                    target_seconds=3.0
                )
            
        except Exception as e:
            error_occurred = True
            logger.error(
                "people_command_error",
                user_id=discord_user.user_id if 'discord_user' in locals() else "unknown",
                person=person,
                error=str(e)
            )
            
            # Send generic error message
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


def register_people_command(
    bot: ArchiveRAGBot,
    rate_limiter: RateLimiter,
    permission_checker: PermissionChecker,
    message_formatter: MessageFormatter,
    entity_query_service: EntityQueryService
) -> None:
    """
    Register /archive people command with Discord bot.
    
    Args:
        bot: Discord bot client
        rate_limiter: Rate limiter service
        permission_checker: Permission checker service
        message_formatter: Message formatter service
        entity_query_service: Entity query service
    """
    command_handler = PeopleCommand(
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
    
    # Register people command
    @archive_group.command(name="people", description="Search for people/participants in archived meetings (contributor+)")
    async def people_command(interaction: discord.Interaction, person: str):
        """Execute /archive people command."""
        await command_handler.handle_people_command(interaction, person)


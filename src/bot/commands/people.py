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
from src.services.entity_normalization import EntityNormalizationService
from src.lib.config import ENTITIES_PEOPLE_DIR
from src.models.person import Person
from src.lib.logging import get_logger

logger = get_logger(__name__)


class PeopleCommand:
    """
    Command handler for /archive people slash command.
    
    Handles people/participant searches in archived meetings (public access).
    """
    
    def __init__(
        self,
        bot: discord.Client,
        rate_limiter: RateLimiter,
        permission_checker: PermissionChecker,
        message_formatter: MessageFormatter,
        entity_query_service: EntityQueryService,
        normalization_service: EntityNormalizationService = None
    ):
        """
        Initialize people command handler.
        
        Args:
            bot: Discord bot client
            rate_limiter: Rate limiter service
            permission_checker: Permission checker service
            message_formatter: Message formatter service
            entity_query_service: Entity query service
            normalization_service: Optional entity normalization service
        """
        self.bot = bot
        self.rate_limiter = rate_limiter
        self.permission_checker = permission_checker
        self.message_formatter = message_formatter
        self.entity_query_service = entity_query_service
        self.normalization_service = normalization_service or EntityNormalizationService()
    
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
    
    def _get_name_variations(self, canonical_name: str, all_people: list) -> tuple[list, list]:
        """
        Get all name variations and person IDs that normalize to the canonical name.
        
        Args:
            canonical_name: Canonical entity name
            all_people: List of all Person entities
            
        Returns:
            Tuple of (name_variations_list, person_ids_list)
            - name_variations: List of name variations (display_name and alias) that normalize to canonical_name
            - person_ids: List of person IDs that normalize to canonical_name
        """
        variations = []
        person_ids = []
        if not canonical_name:
            return variations, person_ids
        
        for person in all_people:
            try:
                # Check if this person normalizes to the same canonical name
                normalized_id, normalized_name = self.normalization_service.normalize_entity_name(
                    person.display_name,
                    existing_entities=all_people,
                    context={}
                )
                
                if normalized_name.lower() == canonical_name.lower():
                    # This person normalizes to the same canonical name
                    if person.display_name not in variations:
                        variations.append(person.display_name)
                    if person.alias and person.alias not in variations:
                        variations.append(person.alias)
                    # Add person ID to list
                    if person.id not in person_ids:
                        person_ids.append(person.id)
            except Exception:
                # If normalization fails for this person, skip it
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            if v and v.lower() not in seen:
                seen.add(v.lower())
                unique_variations.append(v)
        
        return unique_variations, person_ids
    
    def _format_people_response(
        self,
        person: Person,
        meetings: list,
        original_query: str = None,
        canonical_name: str = None,
        name_variations: list = None
    ) -> str:
        """
        Format people search results for Discord.
        
        Args:
            person: Person entity found
            meetings: List of Meeting entities (limited to top 5)
            original_query: Original search query (for showing normalization)
            canonical_name: Normalized canonical name (if different from person.display_name)
            name_variations: List of name variations that normalized to canonical name
            
        Returns:
            Formatted response text
        """
        response_lines = []
        
        # Show normalized name if normalization occurred
        if canonical_name and canonical_name != person.display_name:
            response_lines.append(f"**Person:** {canonical_name} (normalized from '{original_query}')")
        else:
            response_lines.append(f"**Person:** {person.display_name}")
        
        # Show name variations if available
        if name_variations and len(name_variations) > 1:
            variations_text = ", ".join([f"'{v}'" for v in name_variations if v != canonical_name])
            if variations_text:
                response_lines.append(f"**Name variations:** {variations_text}")
        
        # Show alias if different from display_name
        if person.alias and person.alias != person.display_name:
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
            
            # Check permissions (public access - check still performed for consistency)
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
            
            # Try to normalize entity name first
            person_entity = None
            canonical_name = None
            name_variations = []
            related_person_ids = []  # Store person IDs that normalize to same canonical name
            normalization_failed = False
            
            try:
                # Load all people for normalization
                all_people = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.entity_query_service.find_all,
                        ENTITIES_PEOPLE_DIR,
                        Person
                    ),
                    timeout=30.0
                )
                
                # Try normalization
                try:
                    normalized_id, canonical_name = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.normalization_service.normalize_entity_name,
                            person,
                            all_people,
                            {}
                        ),
                        timeout=10.0
                    )
                    
                    # If normalization returned a valid entity ID, use it
                    if normalized_id.int != 0:
                        person_entity = await asyncio.wait_for(
                            asyncio.to_thread(
                                self.entity_query_service.get_by_id,
                                normalized_id,
                                ENTITIES_PEOPLE_DIR,
                                Person
                            ),
                            timeout=10.0
                        )
                        
                        # Get all name variations and person IDs that normalize to this canonical name
                        if person_entity:
                            name_variations, related_person_ids = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self._get_name_variations,
                                    canonical_name,
                                    all_people
                                ),
                                timeout=10.0
                            )
                    else:
                        # Normalization didn't find existing entity, try exact match
                        normalization_failed = True
                except Exception as norm_error:
                    logger.debug(
                        "people_normalization_failed",
                        user_id=discord_user.user_id,
                        person=person,
                        error=str(norm_error)
                    )
                    normalization_failed = True
                
                # If normalization failed or didn't find entity, try exact match
                if not person_entity:
                    # Try exact match by display_name
                    person_entity = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.entity_query_service.find_by_name,
                            person,
                            ENTITIES_PEOPLE_DIR,
                            Person,
                            "display_name"
                        ),
                        timeout=10.0
                    )
                    
                    # If not found, try case-insensitive search in all people
                    if not person_entity:
                        person_lower = person.lower()
                        for p in all_people:
                            if (p.display_name and person_lower in p.display_name.lower()) or \
                               (p.alias and person_lower in p.alias.lower()):
                                person_entity = p
                                break
                    
                    # If still not found, try fuzzy matching for suggestions
                    if not person_entity:
                        suggestions = []
                        for p in all_people:
                            if p.display_name:
                                # Simple similarity check
                                if person_lower in p.display_name.lower() or \
                                   p.display_name.lower() in person_lower:
                                    suggestions.append(p.display_name)
                        
                        error_message = f"No person found matching '{person}'."
                        if suggestions:
                            error_message += f"\n\nDid you mean: {', '.join(suggestions[:3])}?"
                        else:
                            error_message += "\n\nTry checking the spelling or using a different search term."
                        
                        await interaction.followup.send(error_message)
                        logger.info(
                            "people_no_results",
                            user_id=discord_user.user_id,
                            person=person,
                            suggestions=suggestions[:3] if suggestions else []
                        )
                        return
                    
                    # Use display_name as canonical if normalization failed
                    if normalization_failed:
                        canonical_name = person_entity.display_name
                        
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
            
            # Get meetings for this person
            # If we have related person IDs (from normalization), search all of them
            try:
                all_meetings = []
                person_ids_to_search = [person_entity.id]
                
                # Add related person IDs if we found them during normalization
                if related_person_ids:
                    person_ids_to_search.extend(related_person_ids)
                    # Remove duplicates
                    seen_ids = set()
                    unique_person_ids = []
                    for pid in person_ids_to_search:
                        if pid not in seen_ids:
                            seen_ids.add(pid)
                            unique_person_ids.append(pid)
                    person_ids_to_search = unique_person_ids
                
                # Get meetings for all person IDs
                for person_id in person_ids_to_search:
                    person_meetings = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.entity_query_service.get_meetings_by_person,
                            person_id
                        ),
                        timeout=30.0
                    )
                    all_meetings.extend(person_meetings)
                
                # Remove duplicate meetings (by ID)
                seen_meeting_ids = set()
                meetings = []
                for meeting in all_meetings:
                    if meeting.id not in seen_meeting_ids:
                        seen_meeting_ids.add(meeting.id)
                        meetings.append(meeting)
                
                # Sort by date (most recent first)
                meetings.sort(key=lambda m: m.date if m.date else "", reverse=True)
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
            response_text = self._format_people_response(
                person_entity,
                meetings,
                original_query=person,
                canonical_name=canonical_name or person_entity.display_name,
                name_variations=name_variations if name_variations else [person_entity.display_name]
            )
            # Create issue report button view
            report_button_view = self.message_formatter.create_issue_report_button_view(
                query_text=f"/archive people person:\"{person}\"",
                response_text=response_text,
                citations=[],  # People command doesn't have citations in RAGQuery format
                message_id=None,
            )
            message = await interaction.followup.send(response_text, view=report_button_view)
            # Update button view with message ID
            if report_button_view:
                report_button_view.message_id = str(message.id)
            
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
    @archive_group.command(name="people", description="Search for people/participants in archived meetings")
    async def people_command(interaction: discord.Interaction, person: str):
        """Execute /archive people command."""
        await command_handler.handle_people_command(interaction, person)


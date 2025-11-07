"""Relationships command handler for /archive relationships slash command."""

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

import discord
from discord import app_commands

from ..models.discord_user import DiscordUser
from ..bot import ArchiveRAGBot
from ..services.rate_limiter import RateLimiter
from ..services.permission_checker import PermissionChecker
from ..services.message_formatter import MessageFormatter
from ..services.relationship_query_service import RelationshipQueryService, create_relationship_query_service
from ...lib.logging import get_logger

logger = get_logger(__name__)


class RelationshipsCommand:
    """
    Command handler for /archive relationships slash command.
    
    Handles entity relationship queries to show connections between entities.
    """
    
    def __init__(
        self,
        bot: discord.Client,
        rate_limiter: RateLimiter,
        permission_checker: PermissionChecker,
        message_formatter: MessageFormatter,
        relationship_query_service: RelationshipQueryService,
    ):
        """
        Initialize relationships command handler.
        
        Args:
            bot: Discord bot client
            rate_limiter: Rate limiter service
            permission_checker: Permission checker service
            message_formatter: Message formatter service
            relationship_query_service: Relationship query service
        """
        self.bot = bot
        self.rate_limiter = rate_limiter
        self.permission_checker = permission_checker
        self.message_formatter = message_formatter
        self.relationship_query_service = relationship_query_service
    
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
    
    def _format_relationship_triple(self, triple) -> str:
        """
        Format a relationship triple as "Subject → Relationship → Object".
        
        Args:
            triple: RelationshipTriple object
            
        Returns:
            Formatted string: "Subject → Relationship → Object"
        """
        return f"{triple.subject_name} ({triple.subject_type}) → {triple.relationship} → {triple.object_name} ({triple.object_type})"
    
    def _format_relationships_response(
        self,
        entity_name: str,
        entity_type: str,
        canonical_name: Optional[str],
        triples: list,
        error_message: Optional[str] = None,
    ) -> str:
        """
        Format relationship query response for Discord.
        
        Args:
            entity_name: Original entity name queried
            entity_type: Type of entity (person, workgroup, meeting, etc.)
            canonical_name: Normalized/canonical entity name
            triples: List of RelationshipTriple objects
            error_message: Optional error message
            
        Returns:
            Formatted response text
        """
        if error_message:
            response_lines = [f"❌ **Error**", "", error_message]
            return "\n".join(response_lines)
        
        response_lines = []
        
        # Header
        if canonical_name and canonical_name != entity_name:
            response_lines.append(f"**Entity:** {canonical_name} (normalized from '{entity_name}')")
        else:
            response_lines.append(f"**Entity:** {entity_name}")
        
        response_lines.append(f"**Type:** {entity_type.capitalize()}")
        response_lines.append("")
        
        if not triples:
            response_lines.append("No relationships found for this entity.")
            return "\n".join(response_lines)
        
        # Group triples by relationship type
        response_lines.append(f"**Relationships ({len(triples)}):**")
        response_lines.append("")
        
        # Format each relationship
        for i, triple in enumerate(triples[:20], 1):  # Limit to 20 relationships
            formatted = self._format_relationship_triple(triple)
            response_lines.append(f"{i}. {formatted}")
        
        if len(triples) > 20:
            response_lines.append("")
            response_lines.append(f"*(Showing first 20 of {len(triples)} relationships)*")
        
        return "\n".join(response_lines)
    
    async def handle_relationships_command(
        self,
        interaction: discord.Interaction,
        person: Optional[str] = None,
        workgroup: Optional[str] = None,
        meeting: Optional[str] = None,
        decision: Optional[str] = None,
        action: Optional[str] = None,
    ) -> None:
        """
        Handle /archive relationships command execution.
        
        Args:
            interaction: Discord interaction
            person: Optional person name to query
            workgroup: Optional workgroup name to query
            meeting: Optional meeting ID to query
            decision: Optional decision ID to query
            action: Optional action item ID to query
        """
        start_time = datetime.utcnow()
        error_occurred = False
        rate_limit_status = "allowed"
        
        try:
            # Create DiscordUser from interaction
            discord_user = self._create_discord_user(interaction)
            
            # Send immediate acknowledgment
            await interaction.response.send_message("Processing your relationship query...")
            
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
                    "relationships_rate_limit_exceeded",
                    user_id=discord_user.user_id,
                    username=discord_user.username,
                    remaining_seconds=remaining_seconds
                )
                return
            
            # Record query for rate limiting
            self.rate_limiter.record_query(discord_user.user_id)
            
            # Determine which entity type to query
            entity_type = None
            entity_name = None
            
            if person:
                entity_type = "person"
                entity_name = person
            elif workgroup:
                entity_type = "workgroup"
                entity_name = workgroup
            elif meeting:
                entity_type = "meeting"
                entity_name = meeting
            elif decision:
                entity_type = "decision"
                entity_name = decision
            elif action:
                entity_type = "action"
                entity_name = action
            else:
                # No entity specified
                error_message = (
                    "Please specify an entity to query relationships for.\n\n"
                    "**Usage:**\n"
                    "`/archive relationships person:\"Stephen\"`\n"
                    "`/archive relationships workgroup:\"Archives WG\"`\n"
                    "`/archive relationships meeting:\"meeting-id\"`"
                )
                await interaction.followup.send(error_message)
                logger.info(
                    "relationships_no_entity_specified",
                    user_id=discord_user.user_id
                )
                return
            
            # Phase 8: T063 - Logging for relationship query operations
            logger.info(
                "relationships_query_start",
                user_id=discord_user.user_id,
                username=discord_user.username,
                entity_type=entity_type,
                entity_name=entity_name
            )
            
            # Execute relationship query (run in thread to bridge sync/async)
            try:
                if entity_type == "person":
                    # Phase 8: T063 - Logging for relationship query operations
                    logger.debug(
                        "relationships_query_person",
                        user_id=discord_user.user_id,
                        person_name=entity_name
                    )
                    triples, canonical_name, error_msg = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.relationship_query_service.get_relationships_for_person,
                            entity_name
                        ),
                        timeout=30.0  # 30 second timeout
                    )
                    # Phase 8: T063 - Logging for relationship query operations
                    logger.debug(
                        "relationships_query_person_complete",
                        user_id=discord_user.user_id,
                        person_name=entity_name,
                        canonical_name=canonical_name,
                        relationship_count=len(triples) if triples else 0,
                        has_error=bool(error_msg)
                    )
                elif entity_type == "workgroup":
                    # Phase 8: T063 - Logging for relationship query operations
                    logger.debug(
                        "relationships_query_workgroup",
                        user_id=discord_user.user_id,
                        workgroup_name=entity_name
                    )
                    triples, canonical_name, error_msg = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.relationship_query_service.get_relationships_for_workgroup,
                            entity_name
                        ),
                        timeout=30.0
                    )
                    # Phase 8: T063 - Logging for relationship query operations
                    logger.debug(
                        "relationships_query_workgroup_complete",
                        user_id=discord_user.user_id,
                        workgroup_name=entity_name,
                        canonical_name=canonical_name,
                        relationship_count=len(triples) if triples else 0,
                        has_error=bool(error_msg)
                    )
                elif entity_type == "meeting":
                    # Phase 8: T063 - Logging for relationship query operations
                    logger.debug(
                        "relationships_query_meeting",
                        user_id=discord_user.user_id,
                        meeting_id=entity_name
                    )
                    # Parse meeting ID
                    try:
                        meeting_id = UUID(entity_name)
                        triples, error_msg = await asyncio.wait_for(
                            asyncio.to_thread(
                                self.relationship_query_service.get_relationships_for_meeting,
                                meeting_id
                            ),
                            timeout=30.0
                        )
                        canonical_name = None  # Meetings don't have canonical names
                        # Phase 8: T063 - Logging for relationship query operations
                        logger.debug(
                            "relationships_query_meeting_complete",
                            user_id=discord_user.user_id,
                            meeting_id=str(meeting_id),
                            relationship_count=len(triples) if triples else 0,
                            has_error=bool(error_msg)
                        )
                    except ValueError:
                        error_msg = f"Invalid meeting ID format: '{entity_name}'. Expected UUID format."
                        triples = []
                        canonical_name = None
                        # Phase 8: T063 - Logging for relationship query operations
                        logger.warning(
                            "relationships_query_meeting_invalid_id",
                            user_id=discord_user.user_id,
                            meeting_id=entity_name
                        )
                elif entity_type == "decision":
                    # Decision queries not yet implemented in service
                    error_msg = "Decision entity relationship queries are not yet implemented."
                    triples = []
                    canonical_name = None
                    # Phase 8: T063 - Logging for relationship query operations
                    logger.info(
                        "relationships_query_decision_not_implemented",
                        user_id=discord_user.user_id,
                        decision_id=entity_name
                    )
                elif entity_type == "action":
                    # Action item queries not yet implemented in service
                    error_msg = "Action item entity relationship queries are not yet implemented."
                    triples = []
                    canonical_name = None
                    # Phase 8: T063 - Logging for relationship query operations
                    logger.info(
                        "relationships_query_action_not_implemented",
                        user_id=discord_user.user_id,
                        action_id=entity_name
                    )
                else:
                    error_msg = f"Unknown entity type: {entity_type}"
                    triples = []
                    canonical_name = None
                    # Phase 8: T063 - Logging for relationship query operations
                    logger.warning(
                        "relationships_query_unknown_entity_type",
                        user_id=discord_user.user_id,
                        entity_type=entity_type,
                        entity_name=entity_name
                    )
            except asyncio.TimeoutError:
                error_occurred = True
                await interaction.followup.send(
                    self.message_formatter.format_error_message("timeout", "30")
                )
                logger.error(
                    "relationships_query_timeout",
                    user_id=discord_user.user_id,
                    entity_type=entity_type,
                    entity_name=entity_name
                )
                return
            except Exception as e:
                error_occurred = True
                await interaction.followup.send(
                    self.message_formatter.format_error_message("generic")
                )
                logger.error(
                    "relationships_query_failed",
                    user_id=discord_user.user_id,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    error=str(e)
                )
                return
            
            # Phase 8: T063 - Logging for relationship query operations
            if error_msg:
                logger.warning(
                    "relationships_query_error",
                    user_id=discord_user.user_id,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    error_message=error_msg
                )
            
            # Format and send response
            response_text = self._format_relationships_response(
                entity_name=entity_name,
                entity_type=entity_type,
                canonical_name=canonical_name,
                triples=triples,
                error_message=error_msg
            )
            
            # Create issue report button view (only if not an error)
            report_button_view = None
            if not error_msg:
                report_button_view = self.message_formatter.create_issue_report_button_view(
                    query_text=f"/archive relationships {entity_type}:\"{entity_name}\"",
                    response_text=response_text,
                    citations=[],  # Relationships command doesn't have citations in RAGQuery format
                    message_id=None,
                )
            
            message = await interaction.followup.send(response_text, view=report_button_view)
            # Update button view with message ID
            if report_button_view:
                report_button_view.message_id = str(message.id)
            
            # Phase 8: T063 - Logging for relationship query operations
            logger.info(
                "relationships_query_complete",
                user_id=discord_user.user_id,
                entity_type=entity_type,
                entity_name=entity_name,
                canonical_name=canonical_name,
                relationship_count=len(triples) if triples else 0,
                has_error=bool(error_msg),
                response_length=len(response_text)
            )
            
            # Audit logging and Performance Monitoring
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            execution_time_seconds = execution_time_ms / 1000.0
            performance_status = "within_target" if execution_time_seconds < 3.0 else "exceeded_target"
            
            logger.info(
                "relationships_command_executed",
                user_id=discord_user.user_id,
                username=discord_user.username,
                entity_type=entity_type,
                entity_name=entity_name,
                relationship_count=len(triples) if triples else 0,
                execution_time_ms=execution_time_ms,
                execution_time_seconds=round(execution_time_seconds, 2),
                performance_status=performance_status,
                command="archive relationships"
            )
            
            # Performance monitoring warning
            if execution_time_seconds >= 3.0:
                logger.warning(
                    "relationships_performance_exceeded_target",
                    entity_type=entity_type,
                    entity_name=entity_name,
                    execution_time_seconds=round(execution_time_seconds, 2),
                    target_seconds=3.0
                )
            
        except Exception as e:
            error_occurred = True
            logger.error(
                "relationships_command_error",
                user_id=discord_user.user_id if 'discord_user' in locals() else "unknown",
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


def register_relationships_command(
    bot: ArchiveRAGBot,
    rate_limiter: RateLimiter,
    permission_checker: PermissionChecker,
    message_formatter: MessageFormatter,
    relationship_query_service: Optional[RelationshipQueryService] = None,
) -> None:
    """
    Register /archive relationships command with Discord bot.
    
    Args:
        bot: Discord bot client
        rate_limiter: Rate limiter service
        permission_checker: Permission checker service
        message_formatter: Message formatter service
        relationship_query_service: Optional relationship query service
    """
    service = relationship_query_service or create_relationship_query_service()
    
    command_handler = RelationshipsCommand(
        bot=bot,
        rate_limiter=rate_limiter,
        permission_checker=permission_checker,
        message_formatter=message_formatter,
        relationship_query_service=service
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
    
    # Register relationships command
    @archive_group.command(name="relationships", description="Query entity relationships (e.g., person → attended → meeting)")
    @app_commands.describe(
        person="Person name to query relationships for",
        workgroup="Workgroup name to query relationships for",
        meeting="Meeting ID (UUID) to query relationships for",
        decision="Decision ID to query relationships for (not yet implemented)",
        action="Action item ID to query relationships for (not yet implemented)"
    )
    async def relationships_command(
        interaction: discord.Interaction,
        person: Optional[str] = None,
        workgroup: Optional[str] = None,
        meeting: Optional[str] = None,
        decision: Optional[str] = None,
        action: Optional[str] = None,
    ):
        """Execute /archive relationships command."""
        await command_handler.handle_relationships_command(
            interaction,
            person=person,
            workgroup=workgroup,
            meeting=meeting,
            decision=decision,
            action=action
        )


"""Topics command handler for /archive topics slash command."""

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
from src.lib.config import ENTITIES_PEOPLE_DIR, ENTITIES_MEETINGS_DIR
from src.lib.logging import get_logger

logger = get_logger(__name__)


class TopicsCommand:
    """
    Command handler for /archive topics slash command.
    
    Handles topic/tag searches in archived meetings (public access).
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
        Initialize topics command handler.
        
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
    
    def _format_topics_response(
        self,
        topic: str,
        meetings: list,
        original_query: str = None,
        canonical_topic: str = None,
        topic_variations: list = None
    ) -> str:
        """
        Format topics search results for Discord.
        
        Args:
            topic: Topic name searched (or canonical topic)
            meetings: List of Meeting entities (limited to top 5)
            original_query: Original search query (for showing normalization)
            canonical_topic: Normalized canonical topic (if different from topic)
            topic_variations: List of topic variations that normalized to canonical topic
            
        Returns:
            Formatted response text
        """
        response_lines = []
        
        # Show normalized topic if normalization occurred
        if canonical_topic and canonical_topic != topic:
            response_lines.append(f"**Topic:** {canonical_topic} (normalized from '{original_query}')")
        else:
            response_lines.append(f"**Topic:** {topic}")
        
        # Show topic variations if available
        if topic_variations and len(topic_variations) > 1:
            variations_text = ", ".join([f"'{v}'" for v in topic_variations if v != canonical_topic])
            if variations_text:
                response_lines.append(f"**Topic variations:** {variations_text}")
        
        response_lines.append("")
        
        if not meetings:
            response_lines.append("No meetings found with this topic.")
            return "\n".join(response_lines)
        
        response_lines.append("**References:**")
        
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
    
    async def handle_topics_command(
        self,
        interaction: discord.Interaction,
        topic: str
    ) -> None:
        """
        Handle /archive topics command execution.
        
        Args:
            interaction: Discord interaction
            topic: Topic name to search for
        """
        start_time = datetime.utcnow()
        query_id = None
        error_occurred = False
        rate_limit_status = "allowed"
        
        try:
            # Create DiscordUser from interaction
            discord_user = self._create_discord_user(interaction)
            
            # Send immediate acknowledgment
            await interaction.response.send_message("Processing your topic search...")
            
            # Check permissions (public access - check still performed for consistency)
            if not self.permission_checker.has_permission(discord_user, "archive topics"):
                error_message = self.message_formatter.format_error_message("permission_denied")
                await interaction.followup.send(error_message)
                logger.warning(
                    "topics_permission_denied",
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
                    "topics_rate_limit_exceeded",
                    user_id=discord_user.user_id,
                    username=discord_user.username,
                    remaining_seconds=remaining_seconds
                )
                return
            
            # Record query for rate limiting
            self.rate_limiter.record_query(discord_user.user_id)
            
            # Try to normalize topic name first
            canonical_topic = None
            topic_variations = []
            normalization_failed = False
            all_meetings = []
            
            try:
                # Get all unique topics for normalization
                all_topics = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.entity_query_service.get_all_topics
                    ),
                    timeout=30.0
                )
                
                # Try normalization if we have topics to compare against
                if all_topics:
                    try:
                        # Create a simple entity-like structure for normalization
                        # (topics are strings, not entities, but normalization can still find similar strings)
                        class TopicEntity:
                            def __init__(self, name):
                                self.name = name
                                self.display_name = name
                                self.id = None  # Topics don't have IDs
                        
                        topic_entities = [TopicEntity(t) for t in all_topics]
                        
                        # Find similar topics using normalization's similarity matching
                        similar_topic_entities = await asyncio.wait_for(
                            asyncio.to_thread(
                                self.normalization_service.find_similar_entities,
                                topic,
                                topic_entities
                            ),
                            timeout=10.0
                        )
                        
                        if similar_topic_entities:
                            # Found similar topics - use the first one as canonical
                            canonical_topic = similar_topic_entities[0].display_name
                            
                            # Collect all similar topic names
                            topic_variations = [t.display_name for t in similar_topic_entities]
                            
                            # Search for meetings using all similar topics
                            search_topics = topic_variations
                        else:
                            # No similar topics found, use original query
                            canonical_topic = topic
                            topic_variations = [topic]
                            search_topics = [topic]
                            normalization_failed = True
                    except Exception as norm_error:
                        logger.debug(
                            "topics_normalization_failed",
                            user_id=discord_user.user_id,
                            topic=topic,
                            error=str(norm_error)
                        )
                        normalization_failed = True
                        canonical_topic = topic
                        topic_variations = [topic]
                        search_topics = [topic]
                else:
                    # No topics available, use original query
                    canonical_topic = topic
                    topic_variations = [topic]
                    search_topics = [topic]
                    normalization_failed = True
                
                # Search for meetings using all search topics
                all_meeting_ids = set()
                for search_topic in search_topics:
                    try:
                        topic_meetings = await asyncio.wait_for(
                            asyncio.to_thread(
                                self.entity_query_service.get_meetings_by_tag,
                                search_topic,
                                "topics"
                            ),
                            timeout=30.0
                        )
                        for meeting in topic_meetings:
                            all_meeting_ids.add(meeting.id)
                            # Add to all_meetings if not already present
                            if not any(m.id == meeting.id for m in all_meetings):
                                all_meetings.append(meeting)
                    except Exception as search_error:
                        logger.warning(
                            "topics_search_for_variation_failed",
                            topic=search_topic,
                            error=str(search_error)
                        )
                        continue
                
                # Sort meetings by date (most recent first)
                all_meetings.sort(key=lambda m: m.date if m.date else "", reverse=True)
                meetings = all_meetings
                
            except asyncio.TimeoutError:
                error_occurred = True
                await interaction.followup.send(
                    self.message_formatter.format_error_message("timeout", "30")
                )
                logger.error(
                    "topics_search_timeout",
                    user_id=discord_user.user_id,
                    topic=topic
                )
                return
            except Exception as e:
                error_occurred = True
                await interaction.followup.send(
                    self.message_formatter.format_error_message("generic")
                )
                logger.error(
                    "topics_search_failed",
                    user_id=discord_user.user_id,
                    topic=topic,
                    error=str(e)
                )
                return
            
            # Format and send response
            if not meetings:
                # Try to provide suggestions if no results
                suggestions = []
                try:
                    all_topics_list = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.entity_query_service.get_all_topics
                        ),
                        timeout=10.0
                    )
                    topic_lower = topic.lower()
                    for t in all_topics_list:
                        if topic_lower in t.lower() or t.lower() in topic_lower:
                            suggestions.append(t)
                            if len(suggestions) >= 3:
                                break
                except Exception:
                    pass
                
                error_message = f"No topics found matching '{topic}'."
                if suggestions:
                    error_message += f"\n\nDid you mean: {', '.join(suggestions[:3])}?"
                else:
                    error_message += "\n\nTry checking the spelling or using a different search term."
                
                await interaction.followup.send(error_message)
                logger.info(
                    "topics_no_results",
                    user_id=discord_user.user_id,
                    topic=topic,
                    suggestions=suggestions[:3] if suggestions else []
                )
            else:
                response_text = self._format_topics_response(
                    canonical_topic or topic,
                    meetings,
                    original_query=topic,
                    canonical_topic=canonical_topic,
                    topic_variations=topic_variations if topic_variations else [canonical_topic or topic]
                )
                # Create issue report button view
                report_button_view = self.message_formatter.create_issue_report_button_view(
                    query_text=f"/archive topics topic:\"{topic}\"",
                    response_text=response_text,
                    citations=[],  # Topics command doesn't have citations in RAGQuery format
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
                "topics_command_executed",
                user_id=discord_user.user_id,
                username=discord_user.username,
                topic=topic,
                meeting_count=len(meetings) if meetings else 0,
                execution_time_ms=execution_time_ms,
                execution_time_seconds=round(execution_time_seconds, 2),
                performance_status=performance_status,
                command="archive topics"
            )
            
            # Performance monitoring warning
            if execution_time_seconds >= 3.0:
                logger.warning(
                    "topics_performance_exceeded_target",
                    topic=topic,
                    execution_time_seconds=round(execution_time_seconds, 2),
                    target_seconds=3.0
                )
            
        except Exception as e:
            error_occurred = True
            logger.error(
                "topics_command_error",
                user_id=discord_user.user_id if 'discord_user' in locals() else "unknown",
                topic=topic,
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


def register_topics_command(
    bot: ArchiveRAGBot,
    rate_limiter: RateLimiter,
    permission_checker: PermissionChecker,
    message_formatter: MessageFormatter,
    entity_query_service: EntityQueryService
) -> None:
    """
    Register /archive topics command with Discord bot.
    
    Args:
        bot: Discord bot client
        rate_limiter: Rate limiter service
        permission_checker: Permission checker service
        message_formatter: Message formatter service
        entity_query_service: Entity query service
    """
    command_handler = TopicsCommand(
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
    
    # Register topics command
    @archive_group.command(name="topics", description="Search for topics/tags in archived meetings")
    async def topics_command(interaction: discord.Interaction, topic: str):
        """Execute /archive topics command."""
        await command_handler.handle_topics_command(interaction, topic)


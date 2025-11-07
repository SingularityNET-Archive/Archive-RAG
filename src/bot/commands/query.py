"""Query command handler for /archive query slash command."""

import hashlib
import asyncio
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands

from ..models.discord_user import DiscordUser
from ..bot import ArchiveRAGBot
from ..services.rate_limiter import RateLimiter
from ..services.permission_checker import PermissionChecker
from ..services.async_query_service import AsyncQueryService
from ..services.message_formatter import MessageFormatter
from ..utils.message_splitter import split_answer_and_citations
from src.services.audit_writer import AuditWriter
from src.services.citation_verifier import verify_citations_with_entity_extraction, get_verification_error_message
from src.lib.logging import get_logger

logger = get_logger(__name__)


class QueryCommand:
    """
    Command handler for /archive query slash command.
    
    Handles natural language queries against the Archive-RAG system.
    """
    
    def __init__(
        self,
        bot: discord.Client,
        rate_limiter: RateLimiter,
        permission_checker: PermissionChecker,
        async_query_service: AsyncQueryService,
        message_formatter: MessageFormatter,
        audit_writer: AuditWriter,
        index_name: str
    ):
        """
        Initialize query command handler.
        
        Args:
            bot: Discord bot client
            rate_limiter: Rate limiter service
            permission_checker: Permission checker service
            async_query_service: Async query service
            message_formatter: Message formatter service
            audit_writer: Audit writer service
            index_name: RAG index name
        """
        self.bot = bot
        self.rate_limiter = rate_limiter
        self.permission_checker = permission_checker
        self.async_query_service = async_query_service
        self.message_formatter = message_formatter
        self.audit_writer = audit_writer
        self.index_name = index_name
    
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
    
    def _calculate_response_hash(self, response_text: str) -> str:
        """
        Calculate SHA-256 hash of response for audit logging.
        
        Args:
            response_text: Response text to hash
            
        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(response_text.encode('utf-8')).hexdigest()
    
    async def _send_response_chunks(
        self,
        interaction: discord.Interaction,
        answer_chunks: list[str],
        citation_chunks: list[str],
        report_button_view: Optional[discord.ui.View] = None
    ) -> None:
        """
        Send response chunks to Discord channel.
        
        Sends answer chunks first, then citation chunks.
        Adds delays between messages to respect Discord rate limits.
        Attaches report button view to the last message.
        
        Args:
            interaction: Discord interaction
            answer_chunks: List of answer text chunks
            citation_chunks: List of citation text chunks
            report_button_view: Optional Discord view with "Report Issue" button
        """
        # Send answer chunks first (all via followup)
        last_answer_message = None
        for i, chunk in enumerate(answer_chunks):
            # Attach report button to last answer chunk only if no citations
            is_last = (i == len(answer_chunks) - 1 and not citation_chunks)
            view = report_button_view if is_last else None
            
            # Only include view parameter if it's not None (Discord.py doesn't accept None)
            if view:
                message = await interaction.followup.send(chunk, view=view)
                last_answer_message = message
            else:
                message = await interaction.followup.send(chunk)
            # Small delay between chunks
            await asyncio.sleep(0.5)
        
        # Send citation chunks with header if present
        if citation_chunks:
            # Send citations header
            await interaction.followup.send("**Citations:**")
            await asyncio.sleep(0.5)
            
            last_citation_message = None
            for i, chunk in enumerate(citation_chunks):
                # Attach report button to last citation chunk
                is_last = (i == len(citation_chunks) - 1)
                view = report_button_view if is_last else None
                
                # Only include view parameter if it's not None (Discord.py doesn't accept None)
                if view:
                    message = await interaction.followup.send(chunk, view=view)
                    last_citation_message = message
                else:
                    message = await interaction.followup.send(chunk)
                await asyncio.sleep(0.5)
            
            # Update button view with message ID from last message
            if report_button_view and last_citation_message:
                report_button_view.message_id = str(last_citation_message.id)
        elif report_button_view and last_answer_message:
            # Update button view with message ID from last answer message
            report_button_view.message_id = str(last_answer_message.id)
    
    def _validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """
        Validate query text and return helpful suggestions if invalid.
        
        Args:
            query: User query text
            
        Returns:
            Tuple of (is_valid, error_message)
            is_valid: True if query is valid, False otherwise
            error_message: Helpful error message with suggestions if invalid
        """
        # Check for empty or whitespace-only queries
        if not query or not query.strip():
            return False, (
                "Please provide a question or query. "
                "Examples:\n"
                "- \"What decisions were made last January?\"\n"
                "- \"What is the tag taxonomy?\"\n"
                "- \"What meetings discussed budget allocation?\""
            )
        
        # Check for very short queries (likely typos or unclear)
        if len(query.strip()) < 3:
            return False, (
                "Your query seems too short. Please provide more details. "
                "Examples:\n"
                "- \"What decisions were made in the Archives Workgroup?\"\n"
                "- \"Tell me about recent meetings\""
            )
        
        # Check for queries that are just punctuation or symbols
        if query.strip().replace("?", "").replace("!", "").replace(".", "").strip() == "":
            return False, (
                "Please provide a meaningful question. "
                "Examples:\n"
                "- \"What decisions were made last January?\"\n"
                "- \"What is the tag taxonomy?\""
            )
        
        return True, None
    
    async def handle_query_command(
        self,
        interaction: discord.Interaction,
        query: str
    ) -> None:
        """
        Handle /archive query command execution.
        
        Args:
            interaction: Discord interaction
            query: User query text
        """
        start_time = datetime.utcnow()
        query_id = None
        error_occurred = False
        error_message = None
        rate_limit_status = "allowed"
        
        try:
            # Create DiscordUser from interaction
            discord_user = self._create_discord_user(interaction)
            
            # Validate query (T040)
            is_valid, validation_error = self._validate_query(query)
            if not is_valid:
                await interaction.response.send_message(validation_error)
                logger.info(
                    "query_validation_failed",
                    user_id=discord_user.user_id,
                    query_length=len(query) if query else 0
                )
                return
            
            # Send immediate acknowledgment (FR-013) with query text
            await interaction.response.send_message(f"**Query:** {query}\n\nProcessing your query...")
            
            # Check rate limit (FR-010)
            is_allowed, remaining_seconds = self.rate_limiter.check_rate_limit(discord_user.user_id)
            if not is_allowed:
                rate_limit_status = "exceeded"
                error_message = self.message_formatter.format_error_message(
                    "rate_limit",
                    str(remaining_seconds) if remaining_seconds else None
                )
                await interaction.followup.send(error_message)
                logger.warning(
                    "rate_limit_exceeded",
                    user_id=discord_user.user_id,
                    username=discord_user.username,
                    remaining_seconds=remaining_seconds
                )
                return
            
            # Record query for rate limiting
            self.rate_limiter.record_query(discord_user.user_id)
            
            # Execute query (FR-002) with timeout handling (T038)
            try:
                rag_query = await self.async_query_service.execute_query_async(
                    query_text=query,
                    index_name=self.index_name,
                    user_id=discord_user.user_id
                )
            except TimeoutError as e:
                error_occurred = True
                error_message = self.message_formatter.format_error_message(
                    "timeout",
                    str(self.async_query_service.timeout_seconds)
                )
                await interaction.followup.send(error_message)
                logger.error(
                    "query_timeout",
                    user_id=discord_user.user_id,
                    query=query[:100],  # Log first 100 chars
                    error=str(e)
                )
                return
            except RuntimeError as e:
                # Check if it's RAG service unavailable
                if "unavailable" in str(e).lower():
                    error_occurred = True
                    error_message = self.message_formatter.format_error_message("rag_unavailable")
                    await interaction.followup.send(error_message)
                    logger.error(
                        "rag_service_unavailable",
                        user_id=discord_user.user_id,
                        query=query[:100],
                        error=str(e)
                    )
                    return
                # Other runtime errors
                error_occurred = True
                error_message = self.message_formatter.format_error_message("generic")
                await interaction.followup.send(error_message)
                logger.error(
                    "query_execution_failed",
                    user_id=discord_user.user_id,
                    query=query[:100],
                    error=str(e)
                )
                return
            
            # Get query_id for logging
            query_id = rag_query.query_id
            
            # Verify citations with entity extraction before returning results
            # Note: For entity-based queries (topic queries, quantitative queries), entity extraction
            # may not be required if citations reference valid meetings
            # For RAG queries, entity extraction is required for verification
            is_entity_query = rag_query.model_version in ("entity-query", "quantitative-query")
            verification_result = verify_citations_with_entity_extraction(
                rag_query.citations,
                require_entity_extraction=not is_entity_query  # Entity queries may not have entity extraction metadata
            )
            
            # If verification fails, return informative error message
            if not verification_result.is_verified:
                error_message = get_verification_error_message(verification_result, query)
                await interaction.followup.send(error_message)
                logger.warning(
                    "citation_verification_failed",
                    user_id=discord_user.user_id,
                    query=query,
                    query_id=query_id,
                    citation_count=verification_result.citation_count,
                    valid_citation_count=verification_result.valid_citation_count,
                    missing_citations=verification_result.missing_citations,
                    invalid_citations=verification_result.invalid_citations,
                    missing_entity_extraction=verification_result.missing_entity_extraction
                )
                return
            
            # Format response (FR-003) with issue report button
            answer_text, citation_strings, report_button_view = self.message_formatter.format_query_response(
                rag_query,
                include_report_button=True
            )
            
            # Handle no evidence found (additional check)
            if not rag_query.evidence_found:
                error_message = self.message_formatter.format_error_message("no_evidence")
                await interaction.followup.send(error_message)
                logger.info(
                    "no_evidence_found",
                    user_id=discord_user.user_id,
                    query=query,
                    query_id=query_id
                )
            else:
                # Split response if needed (FR-012)
                answer_chunks, citation_chunks = split_answer_and_citations(
                    answer_text,
                    citation_strings
                )
                
                # Send response chunks with report button on last message
                await self._send_response_chunks(interaction, answer_chunks, citation_chunks, report_button_view)
            
            # Audit logging (FR-005, SC-006) and Performance Monitoring (T047)
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            execution_time_seconds = execution_time_ms / 1000.0
            
            # Write audit log (using existing AuditWriter for RAGQuery)
            # The RAGQuery already contains all necessary information for audit
            self.audit_writer.write_query_audit_log(rag_query)
            
            # Performance monitoring (T047: Track SC-001: 95% under 3 seconds)
            performance_status = "within_target" if execution_time_seconds < 3.0 else "exceeded_target"
            
            logger.info(
                "query_command_executed",
                user_id=discord_user.user_id,
                username=discord_user.username,
                query_id=query_id,
                execution_time_ms=execution_time_ms,
                execution_time_seconds=round(execution_time_seconds, 2),
                performance_status=performance_status,
                evidence_found=rag_query.evidence_found,
                citation_count=len(rag_query.citations)
            )
            
            # Log performance warning if exceeded target
            if execution_time_seconds >= 3.0:
                logger.warning(
                    "query_performance_exceeded_target",
                    query_id=query_id,
                    execution_time_seconds=round(execution_time_seconds, 2),
                    target_seconds=3.0
                )
            
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            
            # Get user ID if available
            user_id = "unknown"
            if 'discord_user' in locals():
                user_id = discord_user.user_id
            
            # Log full error with traceback for debugging
            import traceback
            logger.error(
                "query_command_error",
                user_id=user_id,
                query=query,
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc()
            )
            
            # Send generic error message
            try:
                # Check if interaction was already responded to
                if interaction.response.is_done():
                    await interaction.followup.send(
                        self.message_formatter.format_error_message("generic")
                    )
                else:
                    await interaction.response.send_message(
                        self.message_formatter.format_error_message("generic")
                    )
            except Exception as send_error:
                logger.error("failed_to_send_error_message", error=str(send_error), original_error=str(e))


def register_query_command(
    bot: ArchiveRAGBot,
    rate_limiter: RateLimiter,
    permission_checker: PermissionChecker,
    async_query_service: AsyncQueryService,
    message_formatter: MessageFormatter,
    audit_writer: AuditWriter,
    index_name: str
) -> None:
    """
    Register /archive query command with Discord bot.
    
    Args:
        bot: Discord bot client
        rate_limiter: Rate limiter service
        permission_checker: Permission checker service
        async_query_service: Async query service
        message_formatter: Message formatter service
        audit_writer: Audit writer service
        index_name: RAG index name
    """
    command_handler = QueryCommand(
        bot=bot,
        rate_limiter=rate_limiter,
        permission_checker=permission_checker,
        async_query_service=async_query_service,
        message_formatter=message_formatter,
        audit_writer=audit_writer,
        index_name=index_name
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
    
    # Register query command
    @archive_group.command(name="query", description="Ask a question about archived meetings")
    async def query_command(interaction: discord.Interaction, query: str):
        """Execute /archive query command."""
        await command_handler.handle_query_command(interaction, query)


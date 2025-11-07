"""Message formatter service for formatting RAG results for Discord."""

from typing import List, Optional
from uuid import UUID

import discord

from ...models.rag_query import RAGQuery, Citation
from ...lib.logging import get_logger
from .enhanced_citation_formatter import EnhancedCitationFormatter, create_enhanced_citation_formatter
from .issue_report_button import create_issue_report_button_view

logger = get_logger(__name__)


class MessageFormatter:
    """
    Message formatter service for formatting RAG results for Discord.
    
    Formats RAGQuery results into Discord message format with citations.
    """
    
    def __init__(
        self,
        enhanced_citation_formatter: Optional[EnhancedCitationFormatter] = None,
    ):
        """
        Initialize message formatter.
        
        Args:
            enhanced_citation_formatter: Optional EnhancedCitationFormatter instance
        """
        self.enhanced_citation_formatter = enhanced_citation_formatter or create_enhanced_citation_formatter()
    
    def format_query_response(
        self,
        rag_query: RAGQuery,
        include_view_link: bool = True,
        include_report_button: bool = True,
    ) -> tuple[str, List[str], Optional[discord.ui.View]]:
        """
        Format RAGQuery result for Discord message.
        
        Args:
            rag_query: RAGQuery model with query results
            include_view_link: Whether to include "View full meeting record" link
            include_report_button: Whether to include "Report Issue" button
            
        Returns:
            Tuple of (answer_text, citation_strings, view)
            answer_text: Formatted answer text
            citation_strings: List of formatted citation strings
            view: Optional Discord view with "Report Issue" button
        """
        answer_text = rag_query.output
        
        # Format citations
        citation_strings = []
        for citation in rag_query.citations:
            citation_str = self.format_citation(citation)
            citation_strings.append(citation_str)
        
        # Add view link if requested
        if include_view_link and citation_strings:
            # Note: Actual link URL would need to be configured based on deployment
            # For now, we'll include a placeholder
            answer_text += "\n\nView full meeting record: [link to meeting viewer]"
        
        # Create issue report button view if requested
        view = None
        if include_report_button:
            try:
                view = create_issue_report_button_view(
                    query_text=rag_query.user_input,
                    response_text=answer_text,
                    citations=rag_query.citations,
                    message_id=None,  # Will be set when message is sent
                )
            except Exception as e:
                logger.debug("failed_to_create_issue_report_button", error=str(e))
                # Continue without button if creation fails
        
        return answer_text, citation_strings, view
    
    def create_issue_report_button_view(
        self,
        query_text: str,
        response_text: str,
        citations: List[Citation],
        message_id: Optional[str] = None,
    ) -> Optional[discord.ui.View]:
        """
        Create an issue report button view for a bot response.
        
        Args:
            query_text: Original query text
            response_text: Bot response text
            citations: List of Citation objects
            message_id: Optional Discord message ID
            
        Returns:
            IssueReportButtonView instance or None if creation fails
        """
        try:
            return create_issue_report_button_view(
                query_text=query_text,
                response_text=response_text,
                citations=citations,
                message_id=message_id,
            )
        except Exception as e:
            logger.debug("failed_to_create_issue_report_button_view", error=str(e))
            return None
    
    def format_citation(self, citation: Citation, meeting_id: Optional[UUID] = None) -> str:
        """
        Format a citation into Discord message format with enhanced entity context.
        
        Args:
            citation: Citation model
            meeting_id: Optional UUID of the meeting (will be parsed from citation.meeting_id if not provided)
            
        Returns:
            Formatted citation string: [meeting_id | date | workgroup_name]
            Enhanced with normalized entity names, relationship triples, and chunk type
        """
        # Use enhanced citation formatter for enriched formatting
        try:
            parsed_meeting_id = meeting_id
            if not parsed_meeting_id:
                try:
                    parsed_meeting_id = UUID(citation.meeting_id)
                except (ValueError, AttributeError):
                    pass
            
            formatted = self.enhanced_citation_formatter.format_citation(citation, parsed_meeting_id)
            
            # Phase 8: T068 - Validate citation meets Discord message length limits
            from ..config import DISCORD_MAX_MESSAGE_LENGTH
            if len(formatted) > DISCORD_MAX_MESSAGE_LENGTH:
                logger.warning(
                    "citation_exceeds_discord_length_limit",
                    citation_id=citation.meeting_id,
                    citation_length=len(formatted),
                    max_length=DISCORD_MAX_MESSAGE_LENGTH
                )
                # Truncate citation if it exceeds limit (preserve basic format)
                workgroup_name = citation.workgroup_name or "unknown"
                basic_format = f"[{citation.meeting_id} | {citation.date} | {workgroup_name}]"
                if len(basic_format) <= DISCORD_MAX_MESSAGE_LENGTH:
                    return basic_format
                else:
                    # Last resort: truncate basic format
                    return basic_format[:DISCORD_MAX_MESSAGE_LENGTH - 3] + "..."
            
            return formatted
        except Exception as e:
            logger.debug("enhanced_citation_formatting_failed", error=str(e))
            # Fallback to basic format
            workgroup_name = citation.workgroup_name or "unknown"
            return f"[{citation.meeting_id} | {citation.date} | {workgroup_name}]"
    
    def format_citations_section(self, citations: List[Citation]) -> str:
        """
        Format citations into a section for Discord message.
        
        Args:
            citations: List of Citation models
            
        Returns:
            Formatted citations section text
        """
        if not citations:
            return ""
        
        # Phase 8: T068 - Validate citations section meets Discord message length limits
        from ..config import DISCORD_MAX_MESSAGE_LENGTH
        from ..utils.message_splitter import MAX_CHUNK_LENGTH
        
        citation_lines = ["**Citations:**"]
        for citation in citations:
            citation_str = self.format_citation(citation)
            citation_lines.append(citation_str)
        
        citations_text = "\n".join(citation_lines)
        
        # Check if citations section exceeds limit
        if len(citations_text) > MAX_CHUNK_LENGTH:
            logger.warning(
                "citations_section_exceeds_discord_length_limit",
                citations_count=len(citations),
                section_length=len(citations_text),
                max_length=MAX_CHUNK_LENGTH
            )
            # Truncate to fit (keep first N citations that fit)
            truncated_lines = ["**Citations:**"]
            current_length = len(truncated_lines[0])
            for citation_str in citation_lines[1:]:  # Skip header
                test_length = current_length + len("\n") + len(citation_str)
                if test_length <= MAX_CHUNK_LENGTH:
                    truncated_lines.append(citation_str)
                    current_length = test_length
                else:
                    truncated_lines.append(f"... ({len(citations) - len(truncated_lines) + 1} more citations)")
                    break
            citations_text = "\n".join(truncated_lines)
        
        return citations_text
    
    def format_meeting_citation(self, meeting, include_speaker: bool = False) -> str:
        """
        Format a Meeting entity into Discord citation format.
        
        Citation format: [meeting_id | date | identifier]
        - Default identifier: workgroup_name (provides meeting context)
        - Optional identifier: speaker/host name (if include_speaker=True)
        
        Args:
            meeting: Meeting entity with id, date, workgroup_id, host_id
            include_speaker: If True, use host/speaker name instead of workgroup name
            
        Returns:
            Formatted citation string: [meeting_id | date | identifier]
        """
        from src.services.entity_query import EntityQueryService
        from src.lib.config import ENTITIES_WORKGROUPS_DIR, ENTITIES_PEOPLE_DIR
        from src.models.workgroup import Workgroup
        from src.models.person import Person
        
        meeting_id = str(meeting.id)
        date_str = meeting.date.isoformat() if hasattr(meeting.date, 'isoformat') else str(meeting.date)
        
        # Determine identifier (speaker or workgroup)
        if include_speaker and meeting.host_id:
            # Try to get host/speaker name
            entity_service = EntityQueryService()
            host = entity_service.get_by_id(meeting.host_id, ENTITIES_PEOPLE_DIR, Person)
            if host:
                identifier = host.display_name
            else:
                # Fallback to workgroup if host not found
                workgroup_name = "unknown"
                if meeting.workgroup_id:
                    workgroup = entity_service.get_by_id(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                    if workgroup:
                        workgroup_name = workgroup.name
                identifier = workgroup_name
        else:
            # Default: use workgroup name (more useful for meeting context)
            workgroup_name = "unknown"
            if meeting.workgroup_id:
                entity_service = EntityQueryService()
                workgroup = entity_service.get_by_id(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                if workgroup:
                    workgroup_name = workgroup.name
            identifier = workgroup_name
        
        return f"[{meeting_id} | {date_str} | {identifier}]"
    
    def format_error_message(self, error_type: str, details: Optional[str] = None) -> str:
        """
        Format error message for Discord.
        
        Args:
            error_type: Type of error (e.g., "rate_limit", "rag_unavailable", "no_evidence", "timeout")
            details: Additional error details
            
        Returns:
            User-friendly error message with helpful context
        """
        error_messages = {
            "rate_limit": (
                "⏱️ **Rate limit exceeded**\n\n"
                "You've reached the limit of 10 queries per minute. "
                "Please wait {remaining_time} seconds before trying again.\n\n"
                "💡 *Tip: The rate limit resets after 60 seconds.*"
            ),
            "rag_unavailable": (
                "⚠️ **Service temporarily unavailable**\n\n"
                "The archive query service is temporarily unavailable. "
                "This could be due to:\n"
                "- The index file is being updated\n"
                "- Network connectivity issues\n"
                "- System maintenance\n\n"
                "Please try again in a few moments. If the problem persists, contact an admin."
            ),
            "no_evidence": (
                "🔍 **No relevant archive data found**\n\n"
                "Your query didn't match any content in the archive. "
                "Here are some suggestions:\n\n"
                "• **Try rephrasing your question** - Use different keywords or phrasing\n"
                "• **Be more specific** - Include workgroup names, dates, or topics\n"
                "• **Check spelling** - Ensure all terms are spelled correctly\n\n"
                "**Example queries:**\n"
                "- \"What decisions were made in the Archives Workgroup?\"\n"
                "- \"What meetings discussed budget allocation?\"\n"
            ),
            "citation_verification_failed": (
                "⚠️ **Citation verification failed**\n\n"
                "The query results could not be verified against meeting records with entity extraction. "
                "This means the information cannot be properly traced to specific meeting sources.\n\n"
                "**What this means:**\n"
                "- The results don't have proper citations to meeting records\n"
                "- Entity extraction metadata is missing\n"
                "- The information cannot be verified\n\n"
                "**What to do:**\n"
                "- Try rephrasing your question\n"
                "- Use more specific search terms\n"
                "- Contact an administrator if this persists"
            ),
            "permission_denied": (
                "🔒 **Permission denied**\n\n"
                "This command requires a **contributor** or **admin** role. "
                "You currently don't have access to this feature.\n\n"
                "💡 *Contact a server administrator if you need contributor access.*"
            ),
            "admin_only": (
                "🔒 **Admin access required**\n\n"
                "This command requires an **admin** role. "
                "You currently don't have access to this feature.\n\n"
                "💡 *Only administrators can access this command.*"
            ),
            "timeout": (
                "⏱️ **Query timeout**\n\n"
                "Your query took too long to process (exceeded {timeout}s). "
                "This could happen with:\n"
                "- Very complex queries\n"
                "- Large result sets\n"
                "- System load issues\n\n"
                "**Suggestions:**\n"
                "• Try a simpler or more specific query\n"
                "• Break complex questions into smaller parts\n"
                "• Wait a moment and try again\n\n"
                "If this persists, contact an admin."
            ),
            "generic": (
                "❌ **An error occurred**\n\n"
                "Something went wrong while processing your query. "
                "Please try again in a moment.\n\n"
                "If the problem continues, contact an admin with details about what you were trying to do."
            ),
        }
        
        message = error_messages.get(error_type, error_messages["generic"])
        
        # Replace placeholders
        if details:
            message = message.replace("{remaining_time}", str(int(details)))
            message = message.replace("{timeout}", str(int(details)))
        
        return message


def create_message_formatter() -> MessageFormatter:
    """
    Create a message formatter instance.
    
    Returns:
        MessageFormatter instance
    """
    return MessageFormatter()


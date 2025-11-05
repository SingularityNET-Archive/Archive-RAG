"""Message formatter service for formatting RAG results for Discord."""

from typing import List, Optional

from ...models.rag_query import RAGQuery, Citation
from ...lib.logging import get_logger

logger = get_logger(__name__)


class MessageFormatter:
    """
    Message formatter service for formatting RAG results for Discord.
    
    Formats RAGQuery results into Discord message format with citations.
    """
    
    def __init__(self):
        """Initialize message formatter."""
        pass
    
    def format_query_response(self, rag_query: RAGQuery, include_view_link: bool = True) -> tuple[str, List[str]]:
        """
        Format RAGQuery result for Discord message.
        
        Args:
            rag_query: RAGQuery model with query results
            include_view_link: Whether to include "View full meeting record" link
            
        Returns:
            Tuple of (answer_text, citation_strings)
            answer_text: Formatted answer text
            citation_strings: List of formatted citation strings
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
        
        return answer_text, citation_strings
    
    def format_citation(self, citation: Citation) -> str:
        """
        Format a citation into Discord message format.
        
        Args:
            citation: Citation model
            
        Returns:
            Formatted citation string: [meeting_id | date | workgroup_name]
        """
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
        
        citation_lines = ["**Citations:**"]
        for citation in citations:
            citation_str = self.format_citation(citation)
            citation_lines.append(citation_str)
        
        return "\n".join(citation_lines)
    
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
                "- \"Tell me about the tag taxonomy\""
            ),
            "permission_denied": (
                "🔒 **Permission denied**\n\n"
                "This command requires a **contributor** or **admin** role. "
                "You currently don't have access to this feature.\n\n"
                "💡 *Contact a server administrator if you need contributor access.*"
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


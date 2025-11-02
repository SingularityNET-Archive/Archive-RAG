"""Citation extraction service."""

from typing import List, Dict, Any
from datetime import datetime

from ..models.rag_query import Citation
from ..lib.citation import format_citation
from ..lib.logging import get_logger

logger = get_logger(__name__)


def extract_citations(retrieved_chunks: List[Dict[str, Any]]) -> List[Citation]:
    """
    Extract citations from retrieved chunks in format [meeting_id | date | speaker].
    
    Args:
        retrieved_chunks: List of retrieved chunk dictionaries with metadata
        
    Returns:
        List of Citation objects
    """
    citations = []
    
    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata", {})
        meeting_id = metadata.get("meeting_id", chunk.get("meeting_id", ""))
        date = metadata.get("date", "")
        participants = metadata.get("participants", [])
        
        # Extract speaker (use first participant or leave empty)
        speaker = participants[0] if participants else None
        
        # Extract excerpt (chunk text)
        excerpt = chunk.get("text", "")
        
        # Format date (extract date from ISO 8601 datetime if needed)
        if "T" in date:
            date = date.split("T")[0]
        
        # Create citation
        citation = Citation(
            meeting_id=meeting_id,
            date=date,
            speaker=speaker,
            excerpt=excerpt[:200] + "..." if len(excerpt) > 200 else excerpt  # Truncate long excerpts
        )
        
        citations.append(citation)
    
    logger.info("citations_extracted", count=len(citations))
    
    return citations


def format_citations_as_text(citations: List[Citation]) -> str:
    """
    Format citations as text output.
    
    Args:
        citations: List of Citation objects
        
    Returns:
        Formatted citation text
    """
    if not citations:
        return ""
    
    citation_lines = []
    for citation in citations:
        citation_str = format_citation(
            citation.meeting_id,
            citation.date,
            citation.speaker
        )
        citation_lines.append(f"- {citation_str}: {citation.excerpt}")
    
    return "\n".join(citation_lines)


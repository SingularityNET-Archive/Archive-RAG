"""Citation extraction service."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from ..models.rag_query import Citation
from ..lib.citation import format_citation
from ..lib.logging import get_logger
from ..lib.config import ENTITIES_MEETINGS_DIR, ENTITIES_WORKGROUPS_DIR
from ..services.entity_storage import load_entity
from ..models.meeting import Meeting
from ..models.workgroup import Workgroup

logger = get_logger(__name__)


def _get_workgroup_name_from_meeting(meeting_id: str) -> Optional[str]:
    """
    Get workgroup name from meeting ID.
    
    Args:
        meeting_id: Meeting identifier (UUID string)
        
    Returns:
        Workgroup name if found, None otherwise
    """
    if not meeting_id or meeting_id in ("entity-storage", "quantitative-analysis", "no-evidence"):
        return None
    
    try:
        meeting_uuid = UUID(meeting_id)
        meeting = load_entity(meeting_uuid, ENTITIES_MEETINGS_DIR, Meeting)
        if meeting and meeting.workgroup_id:
            workgroup = load_entity(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
            if workgroup:
                logger.debug("workgroup_name_found", meeting_id=meeting_id, workgroup_name=workgroup.name)
                return workgroup.name
            else:
                logger.debug("workgroup_not_found", meeting_id=meeting_id, workgroup_id=str(meeting.workgroup_id))
        else:
            logger.debug("meeting_or_workgroup_id_missing", meeting_id=meeting_id, has_meeting=meeting is not None)
    except ValueError as e:
        logger.debug("invalid_meeting_id_format", meeting_id=meeting_id, error=str(e))
    except (AttributeError, Exception) as e:
        logger.debug("workgroup_name_lookup_failed", meeting_id=meeting_id, error=str(e))
    return None


def extract_citations(retrieved_chunks: List[Dict[str, Any]]) -> List[Citation]:
    """
    Extract citations from retrieved chunks in format [meeting_id | date | workgroup_name].
    
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
        
        # Try to get workgroup name from metadata first (from FAISS index)
        workgroup_name = metadata.get("workgroup")
        
        # If not in metadata, try to look up from entity storage
        if not workgroup_name and meeting_id:
            workgroup_name = _get_workgroup_name_from_meeting(meeting_id)
        
        # Extract excerpt (chunk text)
        excerpt = chunk.get("text", "")
        
        # Format date (extract date from ISO 8601 datetime if needed)
        if "T" in date:
            date = date.split("T")[0]
        
        # Create citation
        citation = Citation(
            meeting_id=meeting_id,
            date=date,
            workgroup_name=workgroup_name,
            excerpt=excerpt[:200] + "..." if len(excerpt) > 200 else excerpt  # Truncate long excerpts
        )
        
        citations.append(citation)
    
    logger.info("citations_extracted", count=len(citations))
    
    return citations


def create_no_evidence_citation(index_name: str) -> Citation:
    """
    Create citation for "no evidence" cases.
    
    Args:
        index_name: Name of the index that was searched
        
    Returns:
        Citation explaining why no evidence was found
    """
    return Citation(
        meeting_id="no-evidence",
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        workgroup_name=None,
        excerpt=f"No evidence found in retrieved chunks. RAG query searched index '{index_name}' but found no relevant results above the similarity threshold."
    )


def format_citations_as_text(citations: List[Citation]) -> str:
    """
    Format citations as text output.
    
    Args:
        citations: List of Citation objects
        
    Returns:
        Formatted citation text (only citation format, no excerpt)
    """
    if not citations:
        return ""
    
    citation_lines = []
    for citation in citations:
        citation_str = format_citation(
            citation.meeting_id,
            citation.date,
            citation.workgroup_name
        )
        citation_lines.append(f"- {citation_str}")
    
    return "\n".join(citation_lines)


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


def extract_citations(
    retrieved_chunks: List[Dict[str, Any]],
    min_score: float = 0.0,
    filter_by_relevance: bool = True
) -> List[Citation]:
    """
    Extract citations from retrieved chunks in format [meeting_id | date | workgroup_name].
    
    Filters citations by relevance score to ensure only strictly relevant citations are returned.
    Ensures at least one citation per unique meeting is included.
    
    Args:
        retrieved_chunks: List of retrieved chunk dictionaries with metadata
        min_score: Minimum similarity score threshold for relevance filtering (default: 0.0)
                   Set to 0.3 or higher to filter out low-relevance citations
        filter_by_relevance: If True, only include citations with scores above min_score (default: True)
        
    Returns:
        List of Citation objects (filtered by relevance if filter_by_relevance=True)
        Ensures at least one citation per unique meeting is included
    """
    citations = []
    # Track unique meetings and their best chunks to ensure one citation per meeting
    meeting_best_chunks: Dict[str, Dict[str, Any]] = {}  # meeting_id -> best chunk
    
    # Calculate relevance threshold for filtering (if enabled)
    relevance_threshold = None
    max_score = None
    
    # Apply relevance filtering to ensure only strictly relevant citations are returned
    if filter_by_relevance and retrieved_chunks:
        # Calculate relative relevance threshold
        # Get all scores to determine a relative threshold
        scores = [chunk.get("score", 0.0) for chunk in retrieved_chunks]
        if scores:
            max_score = max(scores)
            min_score_actual = min(scores)
            
            # Use relative threshold: only include citations within 30% of the top score
            # This ensures we only show citations that are reasonably close to the most relevant result
            # For FAISS Inner Product, scores can vary widely, so we use a relative approach
            if max_score > min_score_actual:
                # Calculate threshold as percentage below max score
                score_range = max_score - min_score_actual
                # Include citations within 70% of the score range (top 30% most relevant)
                relevance_threshold = max_score - (score_range * 0.3)
            else:
                # All scores are the same, use absolute threshold
                relevance_threshold = min_score if min_score != 0.0 else max_score - 0.1
            
            logger.debug(
                "relevance_filtering_applied",
                max_score=max_score,
                min_score=min_score_actual,
                threshold=relevance_threshold,
                total_chunks=len(retrieved_chunks)
            )
        else:
            relevance_threshold = min_score
    
    # First pass: collect best chunk per meeting that passes relevance filter
    for chunk in retrieved_chunks:
        # Filter by relevance score if enabled
        if filter_by_relevance and relevance_threshold is not None:
            chunk_score = chunk.get("score", 0.0)
            
            # Apply threshold (either absolute or relative)
            if min_score != 0.0:
                # Use absolute threshold if provided
                if chunk_score <= min_score:
                    logger.debug(
                        "citation_filtered_by_absolute_threshold",
                        score=chunk_score,
                        min_score=min_score,
                        meeting_id=chunk.get("meeting_id", "unknown")
                    )
                    continue
            else:
                # Use relative threshold (within 30% of top score)
                if chunk_score < relevance_threshold:
                    logger.debug(
                        "citation_filtered_by_relative_threshold",
                        score=chunk_score,
                        threshold=relevance_threshold,
                        max_score=max_score,
                        meeting_id=chunk.get("meeting_id", "unknown")
                    )
                    continue
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
        
        # Extract semantic chunk metadata (Phase 7)
        chunk_type = metadata.get("chunk_type")
        chunk_entities = metadata.get("entities")
        chunk_relationships = metadata.get("relationships")
        
        # If semantic chunking metadata not available, try to infer from available metadata
        # This handles cases where index was built with token-based chunking instead of semantic chunking
        if not chunk_type:
            # Try to infer chunk type from content
            if metadata.get("decisions"):
                chunk_type = "decision_record"
            elif metadata.get("tags"):
                # If it has tags, it's likely a meeting summary
                chunk_type = "meeting_summary"
            else:
                # Default to meeting_summary for transcript chunks
                chunk_type = "meeting_summary"
        
        # If entities not available, try to extract from tags
        if not chunk_entities and metadata.get("tags"):
            tags = metadata.get("tags", {})
            topics_covered = tags.get("topicsCovered", "")
            if topics_covered:
                # Create simple entity entries from topics
                if isinstance(topics_covered, str):
                    topic_list = [t.strip() for t in topics_covered.split(",") if t.strip()]
                elif isinstance(topics_covered, list):
                    topic_list = [str(t).strip() for t in topics_covered if t]
                else:
                    topic_list = []
                
                if topic_list:
                    chunk_entities = [
                        {"normalized_name": topic, "entity_type": "TOPIC"}
                        for topic in topic_list[:5]  # Limit to 5 topics
                    ]
        
        # Track best chunk per meeting (highest score)
        chunk_score = chunk.get("score", 0.0)
        if meeting_id and meeting_id not in ("no-evidence", "entity-storage", "quantitative-analysis"):
            if meeting_id not in meeting_best_chunks:
                meeting_best_chunks[meeting_id] = chunk
            else:
                # Keep chunk with higher score
                existing_score = meeting_best_chunks[meeting_id].get("score", 0.0)
                if chunk_score > existing_score:
                    meeting_best_chunks[meeting_id] = chunk
    
    # Second pass: create one citation per unique meeting using best chunk
    for meeting_id, best_chunk in meeting_best_chunks.items():
        metadata = best_chunk.get("metadata", {})
        date = metadata.get("date", "")
        workgroup_name = metadata.get("workgroup")
        
        if not workgroup_name and meeting_id:
            workgroup_name = _get_workgroup_name_from_meeting(meeting_id)
        
        excerpt = best_chunk.get("text", "")
        
        if "T" in date:
            date = date.split("T")[0]
        
        # Extract semantic chunk metadata (Phase 7)
        chunk_type = metadata.get("chunk_type")
        chunk_entities = metadata.get("entities")
        chunk_relationships = metadata.get("relationships")
        
        # If semantic chunking metadata not available, try to infer from available metadata
        # This handles cases where index was built with token-based chunking instead of semantic chunking
        if not chunk_type:
            # Try to infer chunk type from content
            if metadata.get("decisions"):
                chunk_type = "decision_record"
            elif metadata.get("tags"):
                # If it has tags, it's likely a meeting summary
                chunk_type = "meeting_summary"
            else:
                # Default to meeting_summary for transcript chunks
                chunk_type = "meeting_summary"
        
        # If entities not available, try to extract from tags
        if not chunk_entities and metadata.get("tags"):
            tags = metadata.get("tags", {})
            topics_covered = tags.get("topicsCovered", "")
            if topics_covered:
                # Create simple entity entries from topics
                if isinstance(topics_covered, str):
                    topic_list = [t.strip() for t in topics_covered.split(",") if t.strip()]
                elif isinstance(topics_covered, list):
                    topic_list = [str(t).strip() for t in topics_covered if t]
                else:
                    topic_list = []
                
                if topic_list:
                    chunk_entities = [
                        {"normalized_name": topic, "entity_type": "TOPIC"}
                        for topic in topic_list[:5]  # Limit to 5 topics
                    ]
        
        # Create citation with chunk metadata
        citation = Citation(
            meeting_id=meeting_id,
            date=date,
            workgroup_name=workgroup_name,
            excerpt=excerpt[:200] + "..." if len(excerpt) > 200 else excerpt,  # Truncate long excerpts
            chunk_type=chunk_type,
            chunk_entities=chunk_entities if chunk_entities else None,
            chunk_relationships=chunk_relationships if chunk_relationships else None
        )
        
        citations.append(citation)
    
    logger.info("citations_extracted", count=len(citations), unique_meetings=len(meeting_best_chunks))
    
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


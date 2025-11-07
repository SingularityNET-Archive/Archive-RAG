"""Answer analyzer service for detecting negative responses and filtering citations."""

import re
from typing import List
from ..models.rag_query import Citation
from ..lib.logging import get_logger

logger = get_logger(__name__)


def is_negative_response(answer: str) -> bool:
    """
    Detect if the answer indicates no information was found.
    
    Checks for common negative response patterns that indicate the query
    didn't find relevant information, even if citations were retrieved.
    
    Args:
        answer: Generated answer text
        
    Returns:
        True if answer indicates no information found, False otherwise
    """
    if not answer:
        return True
    
    answer_lower = answer.lower()
    
    # Common negative response patterns
    negative_patterns = [
        r"no\s+specific\s+mention",
        r"not\s+mentioned",
        r"no\s+mention",
        r"not\s+found",
        r"no\s+information",
        r"could\s+not\s+find",
        r"does\s+not\s+appear",
        r"not\s+discussed",
        r"not\s+referenced",
        r"no\s+reference",
        r"not\s+present",
        r"no\s+evidence",
        r"no\s+relevant",
        r"nothing\s+about",
        r"no\s+details\s+about",
        r"not\s+included",
        r"not\s+covered",
    ]
    
    # Check if answer matches negative patterns
    for pattern in negative_patterns:
        if re.search(pattern, answer_lower):
            logger.info("negative_response_detected", pattern=pattern, answer_preview=answer[:100])
            return True
    
    # Check for explicit "no" at start of answer
    if re.match(r'^(no|there is no|there are no|there was no|there were no)', answer_lower):
        logger.info("negative_response_detected", pattern="explicit_no", answer_preview=answer[:100])
        return True
    
    return False


def filter_citations_for_negative_response(
    citations: List[Citation],
    answer: str
) -> List[Citation]:
    """
    Filter citations when answer indicates no information was found.
    
    If the answer is a negative response (e.g., "no specific mention"),
    return empty citations list to avoid showing citations that don't
    actually support the answer.
    
    However, preserve "no-evidence" citations as they explain why no
    information was found.
    
    Args:
        citations: List of Citation objects
        answer: Generated answer text
        
    Returns:
        Filtered list of citations (empty if negative response detected, but preserves no-evidence citations)
    """
    if is_negative_response(answer):
        # Preserve no-evidence citations as they explain the lack of results
        no_evidence_citations = [
            cit for cit in citations 
            if cit.meeting_id == "no-evidence" or cit.meeting_id == "entity-storage" or cit.meeting_id == "quantitative-analysis"
        ]
        
        if no_evidence_citations:
            logger.info(
                "citations_filtered_for_negative_response_preserved_no_evidence",
                original_count=len(citations),
                preserved_count=len(no_evidence_citations),
                answer_preview=answer[:100]
            )
            return no_evidence_citations
        else:
            logger.info(
                "citations_filtered_for_negative_response",
                original_count=len(citations),
                answer_preview=answer[:100]
            )
            return []
    
    return citations


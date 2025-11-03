"""Citation accuracy scorer (≥90% required per SC-001)."""

from typing import List, Dict, Any
from ..models.rag_query import Citation
from ..lib.citation import format_citation, validate_citation_format
from ..lib.logging import get_logger

logger = get_logger(__name__)


def score_citation_accuracy(
    actual_citations: List[Citation],
    expected_citations: List[Dict[str, Any]]
) -> float:
    """
    Score citation accuracy (≥90% required per SC-001).
    
    Args:
        actual_citations: List of actual Citation objects
        expected_citations: List of expected citation dictionaries
        
    Returns:
        Citation accuracy score (0.0 to 1.0)
    """
    if not expected_citations:
        # If no expected citations, check if actual citations are valid format
        if not actual_citations:
            return 1.0  # Both empty
        
        # Check format validity
        valid_count = sum(
            1 for citation in actual_citations
            if validate_citation_format(format_citation(
                citation.meeting_id,
                citation.date,
                citation.workgroup_name
            ))
        )
        return valid_count / len(actual_citations) if actual_citations else 0.0
    
    # Match actual citations to expected citations
    matched_count = 0
    
    for expected in expected_citations:
        expected_meeting_id = expected.get("meeting_id", "")
        expected_date = expected.get("date", "")
        expected_workgroup_name = expected.get("workgroup_name")
        
        # Find matching actual citation
        for actual in actual_citations:
            if (actual.meeting_id == expected_meeting_id and
                actual.date == expected_date and
                (not expected_workgroup_name or actual.workgroup_name == expected_workgroup_name)):
                matched_count += 1
                break
    
    accuracy = matched_count / len(expected_citations) if expected_citations else 0.0
    
    logger.info(
        "citation_accuracy_scored",
        matched=matched_count,
        expected=len(expected_citations),
        accuracy=accuracy
    )
    
    return accuracy


def validate_citation_accuracy_threshold(accuracy: float, threshold: float = 0.9) -> bool:
    """
    Validate citation accuracy meets threshold (≥90% per SC-001).
    
    Args:
        accuracy: Citation accuracy score (0.0 to 1.0)
        threshold: Minimum accuracy threshold (default: 0.9)
        
    Returns:
        True if accuracy meets threshold, False otherwise
    """
    return accuracy >= threshold


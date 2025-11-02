"""Evidence checking service for credible evidence detection (FR-008)."""

from typing import List, Dict, Any
from ..lib.logging import get_logger

logger = get_logger(__name__)


def check_evidence(retrieved_chunks: List[Dict[str, Any]], min_score: float = 0.5) -> bool:
    """
    Check if credible evidence was found in retrieved chunks.
    
    Args:
        retrieved_chunks: List of retrieved chunk dictionaries
        min_score: Minimum similarity score threshold (default: 0.5)
        
    Returns:
        True if credible evidence found, False otherwise
    """
    if not retrieved_chunks:
        logger.warning("no_chunks_retrieved")
        return False
    
    # Check if any chunk has score above threshold
    has_credible_evidence = any(
        chunk.get("score", 0.0) >= min_score
        for chunk in retrieved_chunks
    )
    
    # Also check if chunks have meaningful text content
    has_content = any(
        chunk.get("text", "").strip()
        for chunk in retrieved_chunks
    )
    
    evidence_found = has_credible_evidence and has_content
    
    logger.info(
        "evidence_checked",
        evidence_found=evidence_found,
        chunks_count=len(retrieved_chunks),
        max_score=max([chunk.get("score", 0.0) for chunk in retrieved_chunks], default=0.0)
    )
    
    return evidence_found


def get_no_evidence_message() -> str:
    """
    Get standard "No evidence found" message.
    
    Returns:
        "No evidence found" message string
    """
    return "No evidence found"


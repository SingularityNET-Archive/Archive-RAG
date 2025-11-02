"""Factuality scorer (hallucination count = 0 required per SC-002)."""

from typing import List, Dict, Any, Optional
import difflib

from ..lib.logging import get_logger

logger = get_logger(__name__)


def score_factuality(
    actual_output: str,
    ground_truth: str
) -> tuple[float, int]:
    """
    Score factuality and count hallucinations.
    
    Hallucination count = 0 required per SC-002.
    
    Args:
        actual_output: Actual generated output
        ground_truth: Expected ground truth output
        
    Returns:
        Tuple of (factuality_score, hallucination_count)
    """
    if not ground_truth:
        logger.warning("ground_truth_empty")
        return 0.0, 0
    
    # Simple similarity score using sequence matching
    similarity = difflib.SequenceMatcher(None, actual_output.lower(), ground_truth.lower()).ratio()
    
    # Detect hallucinations (content in output not in ground truth)
    # This is a simplified approach - production would use more sophisticated methods
    hallucination_count = _detect_hallucinations(actual_output, ground_truth)
    
    logger.info(
        "factuality_scored",
        similarity=similarity,
        hallucination_count=hallucination_count
    )
    
    return similarity, hallucination_count


def _detect_hallucinations(actual: str, ground_truth: str) -> int:
    """
    Detect hallucinations in actual output.
    
    This is a simplified heuristic. In production, you would use
    more sophisticated methods like semantic similarity, fact-checking, etc.
    
    Args:
        actual: Actual output text
        ground_truth: Ground truth text
        
    Returns:
        Estimated hallucination count
    """
    # Split into sentences
    actual_sentences = actual.split(". ")
    ground_truth_sentences = ground_truth.split(". ")
    
    # Count sentences in actual that don't match ground truth
    hallucination_count = 0
    
    for actual_sent in actual_sentences:
        if not actual_sent.strip():
            continue
        
        # Check if sentence matches any ground truth sentence
        matches = False
        for gt_sent in ground_truth_sentences:
            similarity = difflib.SequenceMatcher(None, actual_sent.lower(), gt_sent.lower()).ratio()
            if similarity > 0.7:  # Threshold for match
                matches = True
                break
        
        if not matches:
            hallucination_count += 1
    
    return hallucination_count


def validate_hallucination_count(hallucination_count: int) -> bool:
    """
    Validate hallucination count = 0 (required per SC-002).
    
    Args:
        hallucination_count: Number of hallucinations detected
        
    Returns:
        True if count is 0, False otherwise
    """
    return hallucination_count == 0


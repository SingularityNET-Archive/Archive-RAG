"""Citation verification service for ensuring queries are verified by specific citations with entity extraction."""

from typing import List, Tuple, Optional
from uuid import UUID

from ..models.rag_query import Citation
from ..lib.logging import get_logger

logger = get_logger(__name__)


class CitationVerificationResult:
    """Result of citation verification."""
    
    def __init__(
        self,
        is_verified: bool,
        error_message: Optional[str] = None,
        missing_citations: bool = False,
        invalid_citations: bool = False,
        missing_entity_extraction: bool = False,
        citation_count: int = 0,
        valid_citation_count: int = 0
    ):
        """
        Initialize citation verification result.
        
        Args:
            is_verified: True if citations are verified, False otherwise
            error_message: Human-readable error message explaining what's missing
            missing_citations: True if no citations were provided
            invalid_citations: True if citations have invalid meeting IDs
            missing_entity_extraction: True if citations lack entity extraction metadata
            citation_count: Total number of citations
            valid_citation_count: Number of valid citations with entity extraction
        """
        self.is_verified = is_verified
        self.error_message = error_message
        self.missing_citations = missing_citations
        self.invalid_citations = invalid_citations
        self.missing_entity_extraction = missing_entity_extraction
        self.citation_count = citation_count
        self.valid_citation_count = valid_citation_count


def verify_citations_with_entity_extraction(
    citations: List[Citation],
    require_entity_extraction: bool = True
) -> CitationVerificationResult:
    """
    Verify that citations exist and have entity extraction metadata.
    
    Ensures queries are only returned when they have specific citations
    verified by entity extraction. Returns informative error messages if
    verification fails.
    
    Args:
        citations: List of Citation objects to verify
        require_entity_extraction: If True, requires entity extraction metadata in citations
        
    Returns:
        CitationVerificationResult with verification status and error message
    """
    # Check if citations exist
    if not citations or len(citations) == 0:
        return CitationVerificationResult(
            is_verified=False,
            error_message=(
                "**No citations found.**\n\n"
                "The query did not retrieve any specific meeting records to support the answer. "
                "This could mean:\n"
                "- The query doesn't match any content in the archive\n"
                "- The search terms need to be adjusted\n"
                "- The relevant meetings may not be indexed yet\n\n"
                "Please try rephrasing your question or using more specific search terms."
            ),
            missing_citations=True,
            citation_count=0,
            valid_citation_count=0
        )
    
    # Filter out invalid citations (no-evidence, entity-storage, quantitative-analysis)
    invalid_meeting_ids = {"no-evidence", "entity-storage", "quantitative-analysis"}
    valid_citations = []
    invalid_citations = []
    
    for citation in citations:
        meeting_id = citation.meeting_id
        
        # Check if citation has invalid meeting ID
        if meeting_id in invalid_meeting_ids:
            invalid_citations.append(citation)
            continue
        
        # Check if meeting_id is a valid UUID format
        try:
            UUID(meeting_id)
            valid_citations.append(citation)
        except (ValueError, AttributeError):
            # Not a valid UUID - might be invalid
            invalid_citations.append(citation)
    
    # If all citations are invalid
    if len(valid_citations) == 0:
        return CitationVerificationResult(
            is_verified=False,
            error_message=(
                "**No valid citations found.**\n\n"
                "The query retrieved results, but they don't reference specific meeting records. "
                "This usually means:\n"
                "- The search didn't find matching content in archived meetings\n"
                "- The results are from system operations rather than meeting data\n\n"
                "Please try:\n"
                "- Using different search terms\n"
                "- Being more specific about what you're looking for\n"
                "- Checking if the relevant meetings have been indexed"
            ),
            invalid_citations=True,
            citation_count=len(citations),
            valid_citation_count=0
        )
    
    # If entity extraction is required, check for entity metadata
    if require_entity_extraction:
        citations_with_entities = []
        citations_without_entities = []
        
        for citation in valid_citations:
            # Check if citation has entity extraction metadata
            has_chunk_type = citation.chunk_type is not None and citation.chunk_type != ""
            has_chunk_entities = citation.chunk_entities is not None and len(citation.chunk_entities) > 0
            
            if has_chunk_type or has_chunk_entities:
                citations_with_entities.append(citation)
            else:
                citations_without_entities.append(citation)
        
        # If no citations have entity extraction
        if len(citations_with_entities) == 0:
            return CitationVerificationResult(
                is_verified=False,
                error_message=(
                    "**Citations lack entity extraction verification.**\n\n"
                    "The query found meeting records, but they don't have entity extraction metadata "
                    "to verify the information. This means:\n"
                    "- The citations cannot be verified against extracted entities\n"
                    "- Entity relationships and context are not available\n\n"
                    "This may occur if:\n"
                    "- The index was built without semantic chunking\n"
                    "- Entity extraction metadata is missing from the index\n\n"
                    "Please contact an administrator if this persists."
                ),
                missing_entity_extraction=True,
                citation_count=len(citations),
                valid_citation_count=len(valid_citations),
                invalid_citations=len(invalid_citations) > 0
            )
        
        # Log verification success
        logger.info(
            "citations_verified_with_entity_extraction",
            total_citations=len(citations),
            valid_citations=len(valid_citations),
            citations_with_entities=len(citations_with_entities),
            citations_without_entities=len(citations_without_entities)
        )
        
        return CitationVerificationResult(
            is_verified=True,
            citation_count=len(citations),
            valid_citation_count=len(citations_with_entities)
        )
    
    # Entity extraction not required - just check validity
    logger.info(
        "citations_verified",
        total_citations=len(citations),
        valid_citations=len(valid_citations),
        invalid_citations=len(invalid_citations)
    )
    
    return CitationVerificationResult(
        is_verified=True,
        citation_count=len(citations),
        valid_citation_count=len(valid_citations)
    )


def get_verification_error_message(
    verification_result: CitationVerificationResult,
    query_text: Optional[str] = None
) -> str:
    """
    Get a user-friendly error message for citation verification failure.
    
    Args:
        verification_result: CitationVerificationResult from verification
        query_text: Optional query text for context
        
    Returns:
        Formatted error message for Discord users
    """
    if verification_result.is_verified:
        return ""  # No error if verified
    
    # Use the error message from verification result if available
    if verification_result.error_message:
        return verification_result.error_message
    
    # Generate error message based on failure type
    if verification_result.missing_citations:
        return (
            "**No citations found for this query.**\n\n"
            "The system couldn't find any meeting records that match your question. "
            "Please try:\n"
            "- Rephrasing your question\n"
            "- Using more specific search terms\n"
            "- Checking if the relevant meetings have been archived"
        )
    
    if verification_result.invalid_citations:
        return (
            "**Invalid citations detected.**\n\n"
            "The query returned results, but they don't reference valid meeting records. "
            "This may indicate an issue with the search index. Please try rephrasing your question."
        )
    
    if verification_result.missing_entity_extraction:
        return (
            "**Entity extraction verification required.**\n\n"
            "The citations found don't have entity extraction metadata to verify the information. "
            "This may occur if the index was built without semantic chunking. "
            "Please contact an administrator."
        )
    
    # Generic error
    return (
        "**Citation verification failed.**\n\n"
        "The query results could not be verified against meeting records. "
        "Please try rephrasing your question or contact support if this persists."
    )



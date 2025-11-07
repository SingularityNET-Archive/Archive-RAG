"""Query filter service for filtering retrieved chunks based on whole-word matching, meeting ID, and date ranges."""

import re
from typing import List, Dict, Any, Optional
from uuid import UUID
from ..lib.logging import get_logger

logger = get_logger(__name__)


def extract_entity_names_from_query(query: str) -> List[str]:
    """
    Extract potential entity names from a query.
    
    Detects queries like "What was said about X?" or "Tell me about X"
    where X is likely an entity name.
    
    Args:
        query: User query text
        
    Returns:
        List of potential entity names extracted from query
    """
    entity_names = []
    
    # Pattern: "What was said about X?" - captures entity after "about"
    # Handles: "What was said about AGI ?" -> "AGI"
    # Supports both capitalized (Ben) and all-caps (AGI) entity names
    said_about_pattern = r'(?:what|tell\s+me)\s+(?:was\s+)?(?:said|mentioned|discussed|talked)\s+about\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\s*[?\.]?'
    matches = re.findall(said_about_pattern, query, re.IGNORECASE)
    entity_names.extend([m.strip() for m in matches if len(m.strip()) >= 2])
    
    # Pattern: "about X" or "about X?" - general pattern
    # Supports both capitalized and all-caps entity names
    about_pattern = r'(?:about|regarding|concerning|on)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\s*[?\.]?'
    matches = re.findall(about_pattern, query, re.IGNORECASE)
    entity_names.extend([m.strip() for m in matches if len(m.strip()) >= 2])
    
    # Special case: Extract entity name from quoted strings (e.g., "What was said about 'AGI'?")
    quoted_pattern = r'["\']([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)["\']'
    matches = re.findall(quoted_pattern, query)
    entity_names.extend([m.strip() for m in matches if len(m.strip()) >= 2])
    
    # Pattern: "X was" or "X is" (entity at start)
    start_pattern = r'^([A-Z][A-Za-z0-9]+)\s+(?:was|is|are)'
    match = re.search(start_pattern, query)
    if match:
        entity_names.append(match.group(1).strip())
    
    # Remove duplicates and filter out common words
    common_words = {'the', 'a', 'an', 'this', 'that', 'these', 'those', 'what', 'who', 'when', 'where', 'why', 'how'}
    entity_names = list(set([
        name for name in entity_names 
        if len(name) >= 2 and name.lower() not in common_words
    ]))
    
    return entity_names


def filter_chunks_by_whole_word_match(
    chunks: List[Dict[str, Any]],
    entity_names: List[str],
    query_text: str
) -> List[Dict[str, Any]]:
    """
    Filter chunks to only include those with whole-word matches for entity names.
    
    Ensures that "AGI" doesn't match "AGIX" by requiring whole-word boundaries.
    
    Args:
        chunks: List of retrieved chunk dictionaries
        entity_names: List of entity names to match (whole-word only)
        query_text: Original query text for context
        
    Returns:
        Filtered list of chunks that contain whole-word matches
    """
    if not entity_names:
        return chunks
    
    filtered_chunks = []
    
    for chunk in chunks:
        chunk_text = chunk.get("text", "").lower()
        chunk_metadata = chunk.get("metadata", {})
        
        # Check if any entity name appears as a whole word in the chunk
        has_match = False
        for entity_name in entity_names:
            # Create whole-word pattern: \b matches word boundaries
            # Escape special regex characters in entity name
            escaped_name = re.escape(entity_name)
            # Match whole word only (word boundaries on both sides)
            pattern = rf'\b{escaped_name}\b'
            
            if re.search(pattern, chunk_text, re.IGNORECASE):
                has_match = True
                logger.debug(
                    "whole_word_match_found",
                    entity_name=entity_name,
                    chunk_preview=chunk_text[:50]
                )
                break
        
        if has_match:
            filtered_chunks.append(chunk)
        else:
            logger.debug(
                "chunk_filtered_out_no_whole_word_match",
                entity_names=entity_names,
                chunk_preview=chunk_text[:50]
            )
    
    if len(filtered_chunks) < len(chunks):
        logger.info(
            "chunks_filtered_by_whole_word",
            original_count=len(chunks),
            filtered_count=len(filtered_chunks),
            entity_names=entity_names
        )
    
    return filtered_chunks


def extract_meeting_id_from_query(query: str) -> Optional[str]:
    """
    Extract meeting ID (UUID) from query text.
    
    Detects queries like "What did meeting f2c3238c-0bfd-f55b-37cb-6801709bd5b2 say about X?"
    and extracts the meeting ID.
    
    Args:
        query: User query text
        
    Returns:
        Meeting ID as string if found, None otherwise
    """
    # UUID pattern: 8-4-4-4-12 hex digits
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    matches = re.findall(uuid_pattern, query, re.IGNORECASE)
    
    if matches:
        # Validate it's a proper UUID
        try:
            meeting_id = matches[0]
            UUID(meeting_id)  # Validate format
            logger.info("meeting_id_extracted_from_query", meeting_id=meeting_id)
            return meeting_id
        except ValueError:
            logger.debug("invalid_uuid_in_query", uuid=matches[0])
            return None
    
    return None


def filter_chunks_by_meeting_id(
    chunks: List[Dict[str, Any]],
    meeting_id: str
) -> List[Dict[str, Any]]:
    """
    Filter chunks to only include those from a specific meeting.
    
    Args:
        chunks: List of retrieved chunk dictionaries
        meeting_id: Meeting ID (UUID string) to filter by
        
    Returns:
        Filtered list of chunks from the specified meeting only
    """
    filtered_chunks = []
    meeting_id_normalized = str(meeting_id).lower()
    
    for chunk in chunks:
        # Check meeting_id in chunk metadata or direct field
        chunk_meeting_id = None
        metadata = chunk.get("metadata", {})
        
        # Try to get meeting_id from various locations
        if "meeting_id" in chunk:
            chunk_meeting_id = chunk["meeting_id"]
        elif "meeting_id" in metadata:
            chunk_meeting_id = metadata["meeting_id"]
        
        if chunk_meeting_id:
            # Normalize both IDs for comparison
            chunk_meeting_id_str = str(chunk_meeting_id).lower()
            
            # Try exact match first
            if chunk_meeting_id_str == meeting_id_normalized:
                filtered_chunks.append(chunk)
                continue
            
            # Try UUID comparison (handles different string formats)
            try:
                chunk_uuid = UUID(chunk_meeting_id_str)
                query_uuid = UUID(meeting_id_normalized)
                if chunk_uuid == query_uuid:
                    filtered_chunks.append(chunk)
                    continue
            except (ValueError, AttributeError):
                pass
    
    if len(filtered_chunks) < len(chunks):
        logger.info(
            "chunks_filtered_by_meeting_id",
            meeting_id=meeting_id,
            original_count=len(chunks),
            filtered_count=len(filtered_chunks)
        )
    
    return filtered_chunks


def should_apply_whole_word_filtering(query: str) -> bool:
    """
    Determine if whole-word filtering should be applied to a query.
    
    Applies to queries that ask about specific entities by name.
    
    Args:
        query: User query text
        
    Returns:
        True if whole-word filtering should be applied
    """
    query_lower = query.lower()
    
    # Patterns that indicate entity name queries
    entity_query_patterns = [
        r'what\s+was\s+said\s+about',
        r'tell\s+me\s+about',
        r'what\s+about',
        r'mentioned\s+about',
        r'discussed\s+about',
        r'talked\s+about',
    ]
    
    for pattern in entity_query_patterns:
        if re.search(pattern, query_lower):
            return True
    
    return False


def extract_date_from_query(query: str) -> tuple[Optional[int], Optional[int]]:
    """
    Extract year and month from natural language query.
    
    Examples:
        "March 2025" -> (2025, 3)
        "2025" -> (2025, None)
        "meetings in March" -> (None, 3)
    
    Args:
        query: Natural language query text
        
    Returns:
        Tuple of (year, month) or (None, None) if not found
    """
    query_lower = query.lower()
    
    # Month names mapping
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    year = None
    month = None
    
    # Find year (4-digit number)
    year_match = re.search(r'\b(19|20)\d{2}\b', query)
    if year_match:
        year = int(year_match.group())
    
    # Find month name
    for month_name, month_num in months.items():
        if month_name in query_lower:
            month = month_num
            break
    
    return year, month


def filter_chunks_by_date_range(
    chunks: List[Dict[str, Any]],
    year: Optional[int] = None,
    month: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Filter chunks to only include those from meetings within a specific date range.
    
    Args:
        chunks: List of retrieved chunk dictionaries
        year: Year to filter by (e.g., 2025)
        month: Month to filter by (1-12, e.g., 3 for March)
        
    Returns:
        Filtered list of chunks from meetings within the specified date range
    """
    if year is None and month is None:
        return chunks
    
    from datetime import date
    from uuid import UUID
    
    # Calculate date range
    if year is not None:
        if month is not None:
            # Specific month/year
            start_date = date(year, month, 1)
            # Get first day of next month (exclusive end)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
        else:
            # Entire year
            start_date = date(year, 1, 1)
            end_date = date(year + 1, 1, 1)
    else:
        # Only month specified (use current year as default)
        from datetime import datetime
        current_year = datetime.now().year
        start_date = date(current_year, month, 1)
        if month == 12:
            end_date = date(current_year + 1, 1, 1)
        else:
            end_date = date(current_year, month + 1, 1)
    
    filtered_chunks = []
    chunks_without_date = 0
    chunks_filtered_out = 0
    chunks_included = 0
    
    for chunk in chunks:
        # Get meeting_id from chunk
        metadata = chunk.get("metadata", {})
        meeting_id = metadata.get("meeting_id", chunk.get("meeting_id", ""))
        
        if not meeting_id:
            # Include chunks without meeting_id (can't filter them, so include them)
            filtered_chunks.append(chunk)
            chunks_without_date += 1
            continue
        
        # Try to get date from chunk metadata first
        chunk_date_str = metadata.get("date", "")
        
        # If date not in metadata, load from meeting entity
        if not chunk_date_str:
            try:
                from ..services.entity_storage import load_entity
                from ..models.meeting import Meeting
                from ..lib.config import ENTITIES_MEETINGS_DIR
                
                meeting_uuid = UUID(str(meeting_id))
                meeting = load_entity(meeting_uuid, ENTITIES_MEETINGS_DIR, Meeting)
                
                if meeting and meeting.date:
                    # Format date from meeting entity
                    if hasattr(meeting.date, 'isoformat'):
                        chunk_date_str = meeting.date.isoformat()
                    elif hasattr(meeting.date, 'strftime'):
                        chunk_date_str = meeting.date.strftime('%Y-%m-%d')
                    else:
                        chunk_date_str = str(meeting.date)
            except (ValueError, AttributeError, Exception) as e:
                logger.debug("chunk_date_lookup_failed", meeting_id=str(meeting_id), error=str(e))
                # If we can't determine the date, include the chunk (err on side of inclusion)
                filtered_chunks.append(chunk)
                chunks_without_date += 1
                continue
        
        # If we still don't have a date string, include the chunk
        if not chunk_date_str:
            filtered_chunks.append(chunk)
            chunks_without_date += 1
            continue
        
        # Parse date string
        try:
            # Extract date part if it's a datetime string
            if 'T' in chunk_date_str:
                chunk_date_str = chunk_date_str.split('T')[0]
            
            # Parse date
            chunk_date = date.fromisoformat(chunk_date_str)
            
            # Check if date is within range
            if start_date <= chunk_date < end_date:
                filtered_chunks.append(chunk)
                chunks_included += 1
            else:
                chunks_filtered_out += 1
                logger.debug(
                    "chunk_filtered_by_date",
                    meeting_id=str(meeting_id),
                    chunk_date=str(chunk_date),
                    start_date=str(start_date),
                    end_date=str(end_date)
                )
        except (ValueError, AttributeError) as e:
            # If date parsing fails, include the chunk (err on side of inclusion)
            logger.debug("chunk_date_parse_failed", meeting_id=str(meeting_id), date_str=chunk_date_str, error=str(e))
            filtered_chunks.append(chunk)
            chunks_without_date += 1
    
    if len(filtered_chunks) < len(chunks) or chunks_filtered_out > 0:
        logger.info(
            "chunks_filtered_by_date_range",
            year=year,
            month=month,
            original_count=len(chunks),
            filtered_count=len(filtered_chunks),
            chunks_included=chunks_included,
            chunks_filtered_out=chunks_filtered_out,
            chunks_without_date=chunks_without_date,
            start_date=str(start_date),
            end_date=str(end_date)
        )
    
    # Warn if all chunks were filtered out
    if len(filtered_chunks) == 0 and len(chunks) > 0:
        logger.warning(
            "all_chunks_filtered_by_date",
            year=year,
            month=month,
            original_count=len(chunks),
            start_date=str(start_date),
            end_date=str(end_date),
            message="All chunks were filtered out by date range. This may indicate no meetings in the specified period, or date format issues."
        )
    
    return filtered_chunks


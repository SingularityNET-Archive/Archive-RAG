"""Message splitter utility for Discord message length limits."""

from typing import List

from ..config import DISCORD_MAX_MESSAGE_LENGTH, DISCORD_MESSAGE_SAFETY_MARGIN

# Maximum length per chunk (with safety margin)
MAX_CHUNK_LENGTH = DISCORD_MAX_MESSAGE_LENGTH - DISCORD_MESSAGE_SAFETY_MARGIN


def split_text(text: str, max_length: int = MAX_CHUNK_LENGTH) -> List[str]:
    """
    Split text into chunks that fit within Discord message limits.
    
    Splits at word boundaries to preserve readability.
    
    Args:
        text: Text to split
        max_length: Maximum length per chunk (default: 1900 chars)
        
    Returns:
        List of text chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks: List[str] = []
    current_chunk = ""
    
    # Split by words (preserve whitespace)
    words = text.split()
    
    for word in words:
        # Check if adding this word would exceed the limit
        test_chunk = current_chunk + (" " if current_chunk else "") + word
        
        if len(test_chunk) <= max_length:
            current_chunk = test_chunk
        else:
            # Save current chunk and start new one
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = word
            else:
                # Word itself is too long, split it
                if len(word) > max_length:
                    # Split word by characters
                    remaining = word
                    while len(remaining) > max_length:
                        chunks.append(remaining[:max_length])
                        remaining = remaining[max_length:]
                    current_chunk = remaining
                else:
                    current_chunk = word
    
    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def split_answer_and_citations(answer: str, citations: List[str], max_length: int = MAX_CHUNK_LENGTH) -> tuple[List[str], List[str]]:
    """
    Split answer and citations into separate message chunks.
    
    Returns answer chunks first, then citation chunks.
    This follows FR-012: "answer first, then citations in follow-up messages"
    
    Args:
        answer: Answer text
        citations: List of citation strings
        max_length: Maximum length per chunk (default: 1900 chars)
        
    Returns:
        Tuple of (answer_chunks, citation_chunks)
    """
    answer_chunks = split_text(answer, max_length)
    
    # Format citations
    citations_text = "\n".join(citations) if citations else ""
    citation_chunks = split_text(citations_text, max_length) if citations_text else []
    
    return answer_chunks, citation_chunks


def format_citation(citation_dict: dict) -> str:
    """
    Format a citation dictionary into Discord message format.
    
    Args:
        citation_dict: Citation dictionary with meeting_id, date, workgroup_name, excerpt
        
    Returns:
        Formatted citation string: [meeting_id | date | speaker]
    """
    meeting_id = citation_dict.get("meeting_id", "unknown")
    date = citation_dict.get("date", "unknown")
    workgroup_name = citation_dict.get("workgroup_name") or citation_dict.get("speaker", "unknown")
    
    return f"[{meeting_id} | {date} | {workgroup_name}]"


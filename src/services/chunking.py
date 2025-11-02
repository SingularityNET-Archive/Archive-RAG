"""Document chunking service for transcript splitting."""

from typing import List, Dict, Any
from ..models.meeting_record import MeetingRecord
from ..lib.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from ..lib.logging import get_logger

logger = get_logger(__name__)


class DocumentChunk:
    """Represents a chunk of document text with metadata."""
    
    def __init__(
        self,
        text: str,
        chunk_index: int,
        meeting_id: str,
        start_idx: int,
        end_idx: int,
        metadata: Dict[str, Any]
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.meeting_id = meeting_id
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "chunk_index": self.chunk_index,
            "meeting_id": self.meeting_id,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "metadata": self.metadata
        }


def chunk_transcript(
    meeting_record: MeetingRecord,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[DocumentChunk]:
    """
    Chunk transcript text with overlap and metadata preservation.
    
    Args:
        meeting_record: MeetingRecord to chunk
        chunk_size: Size of each chunk (default: 512)
        chunk_overlap: Overlap between chunks (default: 50)
        
    Returns:
        List of DocumentChunk objects
    """
    transcript = meeting_record.transcript
    chunks = []
    
    # Metadata to preserve in each chunk
    metadata = {
        "meeting_id": meeting_record.id,
        "date": meeting_record.date,
        "participants": meeting_record.participants,
        "decisions": meeting_record.decisions,
        "tags": meeting_record.tags
    }
    
    # Chunk transcript with overlap
    start_idx = 0
    chunk_index = 0
    
    while start_idx < len(transcript):
        end_idx = min(start_idx + chunk_size, len(transcript))
        chunk_text = transcript[start_idx:end_idx]
        
        # Create chunk
        chunk = DocumentChunk(
            text=chunk_text,
            chunk_index=chunk_index,
            meeting_id=meeting_record.id,
            start_idx=start_idx,
            end_idx=end_idx,
            metadata=metadata.copy()
        )
        
        chunks.append(chunk)
        
        # Move start position with overlap
        start_idx = end_idx - chunk_overlap
        chunk_index += 1
        
        # Prevent infinite loop
        if start_idx <= 0:
            break
    
    logger.info(
        "transcript_chunked",
        meeting_id=meeting_record.id,
        total_chunks=len(chunks),
        chunk_size=chunk_size,
        overlap=chunk_overlap
    )
    
    return chunks


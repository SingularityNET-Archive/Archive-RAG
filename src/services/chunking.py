"""Document chunking service for transcript splitting."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from ..models.meeting_record import MeetingRecord
from ..lib.config import (
    DEFAULT_CHUNK_SIZE, 
    DEFAULT_CHUNK_OVERLAP,
    ENTITIES_DECISION_ITEMS_DIR,
    ENTITIES_MEETINGS_DIR,
    ENTITIES_PEOPLE_DIR,
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_DOCUMENTS_DIR,
    ENTITIES_ACTION_ITEMS_DIR,
    ENTITIES_AGENDA_ITEMS_DIR,
)
from ..lib.logging import get_logger
from ..services.entity_query import EntityQueryService
from ..services.semantic_chunking import SemanticChunkingService
from ..services.relationship_triple_generator import RelationshipTripleGenerator
from ..services.entity_storage import load_entity
from ..models.meeting import Meeting
from ..models.person import Person
from ..models.workgroup import Workgroup
from ..models.document import Document
from ..models.action_item import ActionItem
from ..models.decision_item import DecisionItem
from ..models.agenda_item import AgendaItem
from ..models.chunk_metadata import ChunkMetadata

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
    
    # Handle meetings with no transcript
    if not transcript or not transcript.strip():
        logger.warning(
            "no_transcript_skipping",
            meeting_id=meeting_record.id,
            reason="Empty or missing transcript"
        )
        return []
    
    chunks = []
    
    # Metadata to preserve in each chunk
    metadata = {
        "meeting_id": meeting_record.id,
        "date": meeting_record.date,
        "participants": meeting_record.participants,
        "decisions": meeting_record.decisions,
        "tags": meeting_record.tags,
        "workgroup": getattr(meeting_record, "workgroup", None),
        "workgroup_id": getattr(meeting_record, "workgroup_id", None)
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
        new_start_idx = end_idx - chunk_overlap
        
        # Prevent infinite loop - check if we'd get stuck or go backwards
        if new_start_idx <= start_idx or new_start_idx >= end_idx:
            break
        
        start_idx = new_start_idx
        chunk_index += 1
        
        # Safety check for very small texts
        if chunk_index > 10000:  # Sanity check
            break
    
    # Log chunking result (non-blocking)
    try:
        logger.debug(
            "transcript_chunked",
            meeting_id=meeting_record.id,
            total_chunks=len(chunks),
            chunk_size=chunk_size,
            overlap=chunk_overlap
        )
    except Exception:
        # Don't let logging block chunking
        pass
    
    return chunks


def extract_decision_text_for_rag(meeting_id: UUID) -> str:
    """
    Extract transcript content from DecisionItem entities for RAG embedding.
    
    This function reads decision text from DecisionItem entity JSON files
    instead of MeetingRecord.transcript, as per FR-020.
    
    Args:
        meeting_id: UUID of the meeting to extract decision text from
        
    Returns:
        Combined decision text string for RAG embedding
        
    Raises:
        ValueError: If meeting_id is invalid
    """
    logger.info("extracting_decision_text_for_rag_start", meeting_id=str(meeting_id))
    
    try:
        # Get all decision items for this meeting
        query_service = EntityQueryService()
        decision_items = query_service.get_decision_items_by_meeting(meeting_id)
        
        # Extract decision text from each decision item
        decision_texts = []
        for decision_item in decision_items:
            if decision_item.decision and decision_item.decision.strip():
                decision_texts.append(decision_item.decision.strip())
        
        # Combine all decision text with spaces
        combined_text = " ".join(decision_texts)
        
        logger.info(
            "extracting_decision_text_for_rag_success",
            meeting_id=str(meeting_id),
            decision_count=len(decision_items),
            text_length=len(combined_text)
        )
        
        return combined_text
        
    except Exception as e:
        logger.error(
            "extracting_decision_text_for_rag_failed",
            meeting_id=str(meeting_id),
            error=str(e)
        )
        raise


def chunk_by_semantic_unit(
    meeting_record: MeetingRecord,
    meeting_id: Optional[UUID] = None,
) -> List[ChunkMetadata]:
    """
    Chunk meeting content by semantic units with entity metadata.
    
    Creates chunks aligned with semantic boundaries (meeting summary, action item,
    decision record, attendance, resource) rather than arbitrary token counts.
    Each chunk includes embedded entity metadata and relationships.
    
    Args:
        meeting_record: MeetingRecord to chunk
        meeting_id: Optional UUID of the meeting (if not provided, will be derived or loaded)
        
    Returns:
        List of ChunkMetadata objects with embedded entities and relationships
    """
    logger.info("semantic_chunking_start", meeting_id=str(meeting_id) if meeting_id else "unknown")
    
    # Determine meeting_id if not provided
    if not meeting_id:
        # Try to get meeting_id from meeting_record
        if hasattr(meeting_record, 'id') and meeting_record.id:
            try:
                meeting_id = UUID(meeting_record.id) if isinstance(meeting_record.id, str) else meeting_record.id
            except (ValueError, AttributeError):
                logger.warning("semantic_chunking_no_meeting_id", meeting_record_id=meeting_record.id)
                # Try to load meeting by workgroup_id and date
                if hasattr(meeting_record, 'workgroup_id') and hasattr(meeting_record, 'date'):
                    query_service = EntityQueryService()
                    # This is a fallback - we'll try to find the meeting
                    # For now, we'll proceed without meeting_id if we can't determine it
                    pass
    
    if not meeting_id:
        logger.warning("semantic_chunking_cannot_determine_meeting_id")
        # Create a temporary UUID for chunking purposes
        import uuid
        meeting_id = uuid.uuid4()
    
    # Load all entities for this meeting
    entities = _load_meeting_entities(meeting_id)
    
    # Generate relationship triples for this meeting
    relationship_triples = []
    try:
        relationship_generator = RelationshipTripleGenerator()
        relationship_triples = relationship_generator.generate_triples(entities, meeting_id)
        logger.debug(
            "relationship_triples_generated",
            meeting_id=str(meeting_id),
            count=len(relationship_triples),
        )
    except Exception as e:
        logger.warning("relationship_triples_generation_failed", meeting_id=str(meeting_id), error=str(e))
    
    # Create semantic chunks using SemanticChunkingService
    semantic_service = SemanticChunkingService()
    chunks = semantic_service.chunk_by_semantic_unit(
        meeting_record=meeting_record,
        entities=entities,
        meeting_id=meeting_id,
        relationship_triples=relationship_triples,
    )
    
    logger.info(
        "semantic_chunking_complete",
        meeting_id=str(meeting_id),
        chunk_count=len(chunks),
        entity_count=len(entities),
    )
    
    return chunks


def _load_meeting_entities(meeting_id: UUID) -> List:
    """
    Load all entities related to a meeting.
    
    Args:
        meeting_id: UUID of the meeting
        
    Returns:
        List of entity objects (Person, Workgroup, Meeting, Document, ActionItem, DecisionItem, AgendaItem)
    """
    entities = []
    
    try:
        # Load meeting entity
        meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
        if meeting:
            entities.append(meeting)
            
            # Load workgroup
            if meeting.workgroup_id:
                workgroup = load_entity(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                if workgroup:
                    entities.append(workgroup)
            
            # Load people who attended the meeting
            query_service = EntityQueryService()
            people = query_service.get_people_by_meeting(meeting_id)
            entities.extend(people)
            
            # Load documents for this meeting
            documents = query_service.get_documents_by_meeting(meeting_id)
            entities.extend(documents)
            
            # Load agenda items, action items, and decision items
            agenda_items = []
            for agenda_item_file in ENTITIES_AGENDA_ITEMS_DIR.glob("*.json"):
                try:
                    agenda_item_id = UUID(agenda_item_file.stem)
                    agenda_item = load_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
                    if agenda_item and agenda_item.meeting_id == meeting_id:
                        agenda_items.append(agenda_item)
                        entities.append(agenda_item)
                except (ValueError, AttributeError):
                    continue
            
            # Load action items for each agenda item
            for agenda_item in agenda_items:
                for action_item_file in ENTITIES_ACTION_ITEMS_DIR.glob("*.json"):
                    try:
                        action_item_id = UUID(action_item_file.stem)
                        action_item = load_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, ActionItem)
                        if action_item and action_item.agenda_item_id == agenda_item.id:
                            entities.append(action_item)
                    except (ValueError, AttributeError):
                        continue
            
            # Load decision items for each agenda item
            for agenda_item in agenda_items:
                for decision_item_file in ENTITIES_DECISION_ITEMS_DIR.glob("*.json"):
                    try:
                        decision_item_id = UUID(decision_item_file.stem)
                        decision_item = load_entity(decision_item_id, ENTITIES_DECISION_ITEMS_DIR, DecisionItem)
                        if decision_item and decision_item.agenda_item_id == agenda_item.id:
                            entities.append(decision_item)
                    except (ValueError, AttributeError):
                        continue
        
    except Exception as e:
        logger.warning("load_meeting_entities_failed", meeting_id=str(meeting_id), error=str(e))
    
    logger.debug(
        "meeting_entities_loaded",
        meeting_id=str(meeting_id),
        entity_count=len(entities),
    )
    
    return entities


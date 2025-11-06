"""Service for formatting structured entity extraction outputs."""

from typing import List, Dict, Any, Optional
from uuid import UUID

from src.lib.logging import get_logger
from src.models.relationship_triple import RelationshipTriple
from src.models.chunk_metadata import ChunkMetadata
from src.services.entity_storage import load_entity
from src.lib.config import (
    ENTITIES_PEOPLE_DIR,
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_MEETINGS_DIR,
    ENTITIES_DOCUMENTS_DIR,
    ENTITIES_AGENDA_ITEMS_DIR,
    ENTITIES_DECISION_ITEMS_DIR,
    ENTITIES_ACTION_ITEMS_DIR,
)
from src.models.person import Person
from src.models.workgroup import Workgroup
from src.models.meeting import Meeting
from src.models.document import Document
from src.models.agenda_item import AgendaItem
from src.models.decision_item import DecisionItem
from src.models.action_item import ActionItem

logger = get_logger(__name__)


class EntityExtractionOutput:
    """Structured output from entity extraction process."""
    
    def __init__(
        self,
        structured_entity_list: List[Dict[str, Any]],
        normalized_cluster_labels: Dict[str, Dict[str, Any]],
        relationship_triples: List[Dict[str, Any]],
        chunks_for_embedding: List[Dict[str, Any]],
    ):
        self.structured_entity_list = structured_entity_list
        self.normalized_cluster_labels = normalized_cluster_labels
        self.relationship_triples = relationship_triples
        self.chunks_for_embedding = chunks_for_embedding
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "structured_entity_list": self.structured_entity_list,
            "normalized_cluster_labels": self.normalized_cluster_labels,
            "relationship_triples": self.relationship_triples,
            "chunks_for_embedding": self.chunks_for_embedding,
        }


class EntityOutputFormatter:
    """
    Service for formatting structured entity extraction outputs.
    
    Formats:
    - Structured entity list (all extracted entities)
    - Normalized cluster labels (canonical names/tags)
    - Relationship triples (Subject -> Relationship -> Object)
    - Chunks for embedding (with entity metadata)
    """
    
    def __init__(self):
        """Initialize entity output formatter."""
        logger.info("entity_output_formatter_initialized")
    
    def format_structured_entity_list(
        self,
        meeting_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Generate structured entity list for a meeting.
        
        Args:
            meeting_id: UUID of the meeting
            
        Returns:
            List of entity dictionaries with id, type, canonical_name, variations, source_meetings
        """
        entities = []
        
        try:
            # Load meeting
            meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
            if not meeting:
                return entities
            
            # Load workgroup
            if meeting.workgroup_id:
                workgroup = load_entity(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                if workgroup:
                    entities.append({
                        "entity_id": str(workgroup.id),
                        "entity_type": "Workgroup",
                        "canonical_name": workgroup.name,
                        "normalized_variations": [workgroup.name],
                        "source_meetings": [str(meeting_id)],
                    })
            
            # Load people who attended
            from src.services.entity_query import EntityQueryService
            query_service = EntityQueryService()
            people = query_service.get_people_by_meeting(meeting_id)
            for person in people:
                entities.append({
                    "entity_id": str(person.id),
                    "entity_type": "Person",
                    "canonical_name": person.display_name,
                    "normalized_variations": [person.display_name] + (person.alias if person.alias else []),
                    "source_meetings": [str(meeting_id)],
                })
            
            # Load documents
            documents = query_service.get_documents_by_meeting(meeting_id)
            for document in documents:
                entities.append({
                    "entity_id": str(document.id),
                    "entity_type": "Document",
                    "canonical_name": document.title,
                    "normalized_variations": [document.title],
                    "source_meetings": [str(meeting_id)],
                })
            
            # Load agenda items
            agenda_items = []
            for agenda_item_file in ENTITIES_AGENDA_ITEMS_DIR.glob("*.json"):
                try:
                    agenda_item_id = UUID(agenda_item_file.stem)
                    agenda_item = load_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
                    if agenda_item and agenda_item.meeting_id == meeting_id:
                        agenda_items.append(agenda_item)
                except (ValueError, AttributeError):
                    continue
            
            # Load decision items
            for agenda_item in agenda_items:
                for decision_item_file in ENTITIES_DECISION_ITEMS_DIR.glob("*.json"):
                    try:
                        decision_item_id = UUID(decision_item_file.stem)
                        decision_item = load_entity(decision_item_id, ENTITIES_DECISION_ITEMS_DIR, DecisionItem)
                        if decision_item and decision_item.agenda_item_id == agenda_item.id:
                            decision_text = decision_item.decision[:50] + "..." if len(decision_item.decision) > 50 else decision_item.decision
                            entities.append({
                                "entity_id": str(decision_item.id),
                                "entity_type": "Decision",
                                "canonical_name": decision_text,
                                "normalized_variations": [decision_text],
                                "source_meetings": [str(meeting_id)],
                            })
                    except (ValueError, AttributeError):
                        continue
            
            # Load action items
            for agenda_item in agenda_items:
                for action_item_file in ENTITIES_ACTION_ITEMS_DIR.glob("*.json"):
                    try:
                        action_item_id = UUID(action_item_file.stem)
                        action_item = load_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, ActionItem)
                        if action_item and action_item.agenda_item_id == agenda_item.id:
                            action_text = action_item.text[:50] + "..." if len(action_item.text) > 50 else action_item.text
                            entities.append({
                                "entity_id": str(action_item.id),
                                "entity_type": "ActionItem",
                                "canonical_name": action_text,
                                "normalized_variations": [action_text],
                                "source_meetings": [str(meeting_id)],
                            })
                    except (ValueError, AttributeError):
                        continue
            
            # Add meeting itself
            meeting_purpose = meeting.purpose[:50] + "..." if meeting.purpose and len(meeting.purpose) > 50 else (meeting.purpose or f"Meeting {meeting.date}")
            entities.append({
                "entity_id": str(meeting.id),
                "entity_type": "Meeting",
                "canonical_name": meeting_purpose,
                "normalized_variations": [meeting_purpose],
                "source_meetings": [str(meeting_id)],
            })
            
        except Exception as e:
            logger.warning("format_structured_entity_list_failed", meeting_id=str(meeting_id), error=str(e))
        
        return entities
    
    def format_normalized_cluster_labels(
        self,
        meeting_id: UUID,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate normalized cluster labels for entities in a meeting.
        
        Args:
            meeting_id: UUID of the meeting
            
        Returns:
            Dictionary mapping entity_id to cluster label info (canonical_name, variations, cluster_id)
        """
        cluster_labels = {}
        
        try:
            # Get structured entity list
            entities = self.format_structured_entity_list(meeting_id)
            
            for entity in entities:
                entity_id = entity["entity_id"]
                cluster_labels[entity_id] = {
                    "canonical_name": entity["canonical_name"],
                    "variations": entity["normalized_variations"],
                    "cluster_id": entity_id,  # Use entity_id as cluster_id (canonical entity)
                }
            
        except Exception as e:
            logger.warning("format_normalized_cluster_labels_failed", meeting_id=str(meeting_id), error=str(e))
        
        return cluster_labels
    
    def format_relationship_triples(
        self,
        relationship_triples: List[RelationshipTriple],
    ) -> List[Dict[str, Any]]:
        """
        Format relationship triples for output.
        
        Args:
            relationship_triples: List of RelationshipTriple objects
            
        Returns:
            List of relationship triple dictionaries
        """
        formatted_triples = []
        
        for triple in relationship_triples:
            formatted_triples.append({
                "subject_id": str(triple.subject_id),
                "subject_type": triple.subject_type,
                "subject_name": triple.subject_name,
                "relationship": triple.relationship,
                "object_id": str(triple.object_id),
                "object_type": triple.object_type,
                "object_name": triple.object_name,
                "source_meeting_id": str(triple.source_meeting_id),
                "source_field": triple.source_field or "",
            })
        
        return formatted_triples
    
    def format_chunks_for_embedding(
        self,
        chunks: List[ChunkMetadata],
    ) -> List[Dict[str, Any]]:
        """
        Format chunks with entity metadata for embedding.
        
        Args:
            chunks: List of ChunkMetadata objects
            
        Returns:
            List of chunk dictionaries with text, entities, and metadata
        """
        formatted_chunks = []
        
        for chunk in chunks:
            formatted_chunk = {
                "text": chunk.text,
                "entities": [
                    {
                        "entity_id": str(e.entity_id),
                        "entity_type": e.entity_type,
                        "normalized_name": e.normalized_name,
                        "mentions": e.mentions,
                    }
                    for e in chunk.entities
                ],
                "metadata": {
                    "meeting_id": str(chunk.metadata.meeting_id),
                    "chunk_type": chunk.metadata.chunk_type,
                    "source_field": chunk.metadata.source_field,
                    "relationships": [
                        {
                            "subject": r.subject,
                            "relationship": r.relationship,
                            "object": r.object,
                        }
                        for r in chunk.metadata.relationships
                    ],
                    "chunk_index": chunk.metadata.chunk_index,
                    "total_chunks": chunk.metadata.total_chunks,
                },
            }
            formatted_chunks.append(formatted_chunk)
        
        return formatted_chunks
    
    def generate_complete_output(
        self,
        meeting_id: UUID,
        relationship_triples: List[RelationshipTriple],
        chunks: List[ChunkMetadata],
    ) -> EntityExtractionOutput:
        """
        Generate complete structured output for entity extraction.
        
        Args:
            meeting_id: UUID of the meeting
            relationship_triples: List of RelationshipTriple objects
            chunks: List of ChunkMetadata objects
            
        Returns:
            EntityExtractionOutput with all formatted outputs
        """
        structured_entity_list = self.format_structured_entity_list(meeting_id)
        normalized_cluster_labels = self.format_normalized_cluster_labels(meeting_id)
        formatted_triples = self.format_relationship_triples(relationship_triples)
        formatted_chunks = self.format_chunks_for_embedding(chunks)
        
        logger.info(
            "entity_extraction_output_generated",
            meeting_id=str(meeting_id),
            entity_count=len(structured_entity_list),
            triple_count=len(formatted_triples),
            chunk_count=len(formatted_chunks),
        )
        
        return EntityExtractionOutput(
            structured_entity_list=structured_entity_list,
            normalized_cluster_labels=normalized_cluster_labels,
            relationship_triples=formatted_triples,
            chunks_for_embedding=formatted_chunks,
        )


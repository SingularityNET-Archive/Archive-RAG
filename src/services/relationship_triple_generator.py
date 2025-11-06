"""Relationship triple generator service."""

from typing import List, Optional
from uuid import UUID

from src.lib.logging import get_logger
from src.models.relationship_triple import RelationshipTriple
from src.models.meeting import Meeting
from src.models.workgroup import Workgroup
from src.models.person import Person
from src.models.action_item import ActionItem
from src.models.decision_item import DecisionItem
from src.models.document import Document
from src.models.agenda_item import AgendaItem
from src.services.entity_storage import load_entity
from src.lib.config import (
    ENTITIES_MEETINGS_DIR,
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_PEOPLE_DIR,
    ENTITIES_ACTION_ITEMS_DIR,
    ENTITIES_DECISION_ITEMS_DIR,
    ENTITIES_DOCUMENTS_DIR,
    ENTITIES_AGENDA_ITEMS_DIR,
)

logger = get_logger(__name__)


class RelationshipTripleGenerator:
    """
    Service for generating relationship triples from entities.
    
    Relationship triples are in format: "Subject -> Relationship -> Object"
    Example: "Person -> attended -> Meeting"
    """
    
    def __init__(self):
        """Initialize relationship triple generator."""
        logger.info("relationship_triple_generator_initialized")
    
    def generate_triples(
        self,
        entities: List,
        meeting_id: UUID,
    ) -> List[RelationshipTriple]:
        """
        Generate relationship triples from entities.
        
        Args:
            entities: List of entity objects (Meeting, Person, etc.)
            meeting_id: Source meeting ID for traceability
            
        Returns:
            List of RelationshipTriple objects
        """
        triples = []
        
        # Load all related entities for the meeting if not already provided
        # This ensures we can generate Workgroup -> Decision/Action relationships
        entities_to_process = entities.copy()
        
        # Find Meeting entity in the list
        meeting_entity = None
        for entity in entities:
            if isinstance(entity, Meeting) and entity.id == meeting_id:
                meeting_entity = entity
                break
        
        # If we have a meeting, load all its action items and decision items
        if meeting_entity:
            # Load agenda items for this meeting
            agenda_items = []
            for agenda_item_file in ENTITIES_AGENDA_ITEMS_DIR.glob("*.json"):
                try:
                    agenda_item_id = UUID(agenda_item_file.stem)
                    agenda_item = load_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
                    if agenda_item and agenda_item.meeting_id == meeting_id:
                        agenda_items.append(agenda_item)
                except (ValueError, AttributeError):
                    continue
            
            # Load action items for each agenda item
            for agenda_item in agenda_items:
                for action_item_file in ENTITIES_ACTION_ITEMS_DIR.glob("*.json"):
                    try:
                        action_item_id = UUID(action_item_file.stem)
                        action_item = load_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, ActionItem)
                        if action_item and action_item.agenda_item_id == agenda_item.id:
                            entities_to_process.append(action_item)
                    except (ValueError, AttributeError):
                        continue
                
                # Load decision items for each agenda item
                for decision_item_file in ENTITIES_DECISION_ITEMS_DIR.glob("*.json"):
                    try:
                        decision_item_id = UUID(decision_item_file.stem)
                        decision_item = load_entity(decision_item_id, ENTITIES_DECISION_ITEMS_DIR, DecisionItem)
                        if decision_item and decision_item.agenda_item_id == agenda_item.id:
                            entities_to_process.append(decision_item)
                    except (ValueError, AttributeError):
                        continue
        
        # Generate triples from each entity
        for entity in entities_to_process:
            if isinstance(entity, Meeting):
                # Workgroup -> held -> Meeting
                if entity.workgroup_id:
                    workgroup = load_entity(entity.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                    if workgroup:
                        triples.append(RelationshipTriple(
                            subject_id=workgroup.id,
                            subject_type="Workgroup",
                            subject_name=workgroup.name,
                            relationship="held",
                            object_id=entity.id,
                            object_type="Meeting",
                            object_name=f"Meeting {entity.date}",
                            source_meeting_id=meeting_id,
                            source_field="meetingInfo.workgroup_id",
                        ))
                
                # Meeting -> has_document -> Document (if documents exist)
                # Meeting -> has_agenda_item -> AgendaItem (if agenda items exist)
                # These would be added when processing documents and agenda items
                
            elif isinstance(entity, ActionItem):
                # ActionItem -> assigned_to -> Person
                if entity.assignee_id:
                    person = load_entity(entity.assignee_id, ENTITIES_PEOPLE_DIR, Person)
                    if person:
                        triples.append(RelationshipTriple(
                            subject_id=entity.id,
                            subject_type="ActionItem",
                            subject_name=entity.text[:50] + "..." if len(entity.text) > 50 else entity.text,
                            relationship="assigned_to",
                            object_id=person.id,
                            object_type="Person",
                            object_name=person.display_name,
                            source_meeting_id=meeting_id,
                            source_field="agendaItems[].actionItems[].assignee_id",
                        ))
                
                # Meeting -> has -> ActionItem (via agenda item)
                agenda_item = load_entity(entity.agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
                if agenda_item:
                    triples.append(RelationshipTriple(
                        subject_id=meeting_id,
                        subject_type="Meeting",
                        subject_name=f"Meeting {meeting_id}",
                        relationship="has",
                        object_id=entity.id,
                        object_type="ActionItem",
                        object_name=entity.text[:50] + "..." if len(entity.text) > 50 else entity.text,
                        source_meeting_id=meeting_id,
                        source_field="agendaItems[].actionItems[]",
                    ))
                    
                    # Workgroup -> made -> ActionItem (trace back through meeting)
                    action_meeting = load_entity(agenda_item.meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                    if action_meeting and action_meeting.workgroup_id:
                        workgroup = load_entity(action_meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                        if workgroup:
                            triples.append(RelationshipTriple(
                                subject_id=workgroup.id,
                                subject_type="Workgroup",
                                subject_name=workgroup.name,
                                relationship="made",
                                object_id=entity.id,
                                object_type="ActionItem",
                                object_name=entity.text[:50] + "..." if len(entity.text) > 50 else entity.text,
                                source_meeting_id=meeting_id,
                                source_field="agendaItems[].actionItems[]",
                            ))
                
            elif isinstance(entity, DecisionItem):
                # Decision -> has_effect -> Effect
                if entity.effect:
                    triples.append(RelationshipTriple(
                        subject_id=entity.id,
                        subject_type="Decision",
                        subject_name=entity.decision[:50] + "..." if len(entity.decision) > 50 else entity.decision,
                        relationship="has_effect",
                        object_id=UUID(int=0),  # Effect is an enum, not an entity
                        object_type="Effect",
                        object_name=str(entity.effect),
                        source_meeting_id=meeting_id,
                        source_field="agendaItems[].decisionItems[].effect",
                    ))
                
                # Meeting -> produced -> Decision
                agenda_item = load_entity(entity.agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
                if agenda_item:
                    triples.append(RelationshipTriple(
                        subject_id=meeting_id,
                        subject_type="Meeting",
                        subject_name=f"Meeting {meeting_id}",
                        relationship="produced",
                        object_id=entity.id,
                        object_type="Decision",
                        object_name=entity.decision[:50] + "..." if len(entity.decision) > 50 else entity.decision,
                        source_meeting_id=meeting_id,
                        source_field="agendaItems[].decisionItems[]",
                    ))
                    
                    # Workgroup -> made -> Decision (trace back through meeting)
                    decision_meeting = load_entity(agenda_item.meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                    if decision_meeting and decision_meeting.workgroup_id:
                        workgroup = load_entity(decision_meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                        if workgroup:
                            triples.append(RelationshipTriple(
                                subject_id=workgroup.id,
                                subject_type="Workgroup",
                                subject_name=workgroup.name,
                                relationship="made",
                                object_id=entity.id,
                                object_type="Decision",
                                object_name=entity.decision[:50] + "..." if len(entity.decision) > 50 else entity.decision,
                                source_meeting_id=meeting_id,
                                source_field="agendaItems[].decisionItems[]",
                            ))
        
        logger.info(
            "relationship_triples_generated",
            meeting_id=str(meeting_id),
            triple_count=len(triples),
        )
        
        return triples
    
    def get_triples_for_entity(
        self,
        entity_id: UUID,
        entity_type: str,
    ) -> List[RelationshipTriple]:
        """
        Get all relationship triples involving an entity.
        
        Args:
            entity_id: Entity ID to find triples for
            entity_type: Entity type (e.g., "Person", "Meeting")
            
        Returns:
            List of RelationshipTriple objects where entity appears as subject or object
        """
        # This would need to scan all relationship triples or maintain an index
        # For now, return empty list - full implementation would query stored triples
        logger.debug(
            "get_triples_for_entity",
            entity_id=str(entity_id),
            entity_type=entity_type,
        )
        return []


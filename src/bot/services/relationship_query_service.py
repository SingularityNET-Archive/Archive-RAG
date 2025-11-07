"""Relationship query service for entity relationship queries."""

from typing import List, Optional
from uuid import UUID

from ...services.relationship_triple_generator import RelationshipTripleGenerator
from ...services.entity_normalization import EntityNormalizationService
from ...services.entity_query import EntityQueryService
from ...models.relationship_triple import RelationshipTriple
from ...lib.config import (
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_PEOPLE_DIR,
    ENTITIES_MEETINGS_DIR,
    ENTITIES_DECISION_ITEMS_DIR,
    ENTITIES_ACTION_ITEMS_DIR,
)
from ...models.workgroup import Workgroup
from ...models.person import Person
from ...models.meeting import Meeting
from ...models.decision_item import DecisionItem
from ...models.action_item import ActionItem
from ...lib.logging import get_logger

logger = get_logger(__name__)


class RelationshipQueryService:
    """
    Service for querying entity relationships.
    
    Provides methods to:
    - Get relationships for a specific entity
    - Normalize entity names before querying
    - Handle normalization failures gracefully
    - Suggest similar entities for non-existent entities
    """
    
    def __init__(
        self,
        relationship_generator: Optional[RelationshipTripleGenerator] = None,
        normalization_service: Optional[EntityNormalizationService] = None,
        entity_query_service: Optional[EntityQueryService] = None,
    ):
        """
        Initialize relationship query service.
        
        Args:
            relationship_generator: Optional RelationshipTripleGenerator instance
            normalization_service: Optional EntityNormalizationService instance
            entity_query_service: Optional EntityQueryService instance
        """
        self.relationship_generator = relationship_generator or RelationshipTripleGenerator()
        self.normalization_service = normalization_service or EntityNormalizationService()
        self.entity_query_service = entity_query_service or EntityQueryService()
        
        logger.info("relationship_query_service_initialized")
    
    def get_relationships_for_workgroup(
        self,
        workgroup_name: str,
    ) -> tuple[List[RelationshipTriple], Optional[str], Optional[str]]:
        """
        Get relationships for a workgroup entity.
        
        Args:
            workgroup_name: Workgroup name (may be a variation)
            
        Returns:
            Tuple of (relationship_triples, canonical_name, error_message)
            - If entity not found: error_message contains helpful suggestions
            - If normalization fails: error_message contains suggestions
        """
        # Normalize workgroup name
        try:
            normalized_id, canonical_name = self.normalization_service.normalize_entity_name(
                workgroup_name,
                existing_entities=None,
                context={}
            )
            
            # If normalization returned placeholder UUID, try to find exact match
            if normalized_id.int == 0:
                # Try exact match search
                workgroup = self._find_workgroup_by_name(workgroup_name)
                if not workgroup:
                    # Try fuzzy search for suggestions
                    suggestions = self._suggest_workgroups(workgroup_name)
                    error_msg = f"Workgroup '{workgroup_name}' not found."
                    if suggestions:
                        error_msg += f"\n\nDid you mean: {', '.join(suggestions[:3])}?"
                    return [], None, error_msg
                
                workgroup_id = workgroup.id
                canonical_name = workgroup.name
            else:
                workgroup_id = normalized_id
        except Exception as e:
            logger.debug("workgroup_normalization_failed", error=str(e), name=workgroup_name)
            # Try exact match
            workgroup = self._find_workgroup_by_name(workgroup_name)
            if not workgroup:
                suggestions = self._suggest_workgroups(workgroup_name)
                error_msg = f"Workgroup '{workgroup_name}' not found."
                if suggestions:
                    error_msg += f"\n\nDid you mean: {', '.join(suggestions[:3])}?"
                return [], None, error_msg
            
            workgroup_id = workgroup.id
            canonical_name = workgroup.name
        
        # Load workgroup and generate relationships
        workgroup = self.entity_query_service.get_by_id(
            workgroup_id,
            ENTITIES_WORKGROUPS_DIR,
            Workgroup
        )
        
        if not workgroup:
            return [], None, f"Workgroup '{workgroup_name}' not found."
        
        # Load all meetings for this workgroup to generate relationships
        from ...services.entity_storage import load_entity
        entities = [workgroup]
        
        # Load meetings for this workgroup
        for meeting_file in ENTITIES_MEETINGS_DIR.glob("*.json"):
            try:
                meeting_id = UUID(meeting_file.stem)
                meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                if meeting and meeting.workgroup_id == workgroup_id:
                    entities.append(meeting)
            except (ValueError, AttributeError):
                continue
        
        # Generate relationship triples
        triples = []
        for meeting in entities:
            if isinstance(meeting, Meeting):
                meeting_triples = self.relationship_generator.generate_triples(entities, meeting.id)
                triples.extend(meeting_triples)
        
        # Filter to only triples involving this workgroup
        workgroup_triples = [
            t for t in triples
            if (t.subject_id == workgroup_id and t.subject_type == "Workgroup") or
               (t.object_id == workgroup_id and t.object_type == "Workgroup")
        ]
        
        return workgroup_triples, canonical_name, None
    
    def get_relationships_for_person(
        self,
        person_name: str,
    ) -> tuple[List[RelationshipTriple], Optional[str], Optional[str]]:
        """
        Get relationships for a person entity.
        
        Args:
            person_name: Person name (may be a variation)
            
        Returns:
            Tuple of (relationship_triples, canonical_name, error_message)
        """
        # Normalize person name
        try:
            normalized_id, canonical_name = self.normalization_service.normalize_entity_name(
                person_name,
                existing_entities=None,
                context={}
            )
            
            # If normalization returned placeholder UUID, try to find exact match
            if normalized_id.int == 0:
                person = self._find_person_by_name(person_name)
                if not person:
                    suggestions = self._suggest_people(person_name)
                    error_msg = f"Person '{person_name}' not found."
                    if suggestions:
                        error_msg += f"\n\nDid you mean: {', '.join(suggestions[:3])}?"
                    return [], None, error_msg
                
                person_id = person.id
                canonical_name = person.display_name
            else:
                person_id = normalized_id
        except Exception as e:
            logger.debug("person_normalization_failed", error=str(e), name=person_name)
            # Try exact match
            person = self._find_person_by_name(person_name)
            if not person:
                suggestions = self._suggest_people(person_name)
                error_msg = f"Person '{person_name}' not found."
                if suggestions:
                    error_msg += f"\n\nDid you mean: {', '.join(suggestions[:3])}?"
                return [], None, error_msg
            
            person_id = person.id
            canonical_name = person.display_name
        
        # Load person
        person = self.entity_query_service.get_by_id(
            person_id,
            ENTITIES_PEOPLE_DIR,
            Person
        )
        
        if not person:
            return [], None, f"Person '{person_name}' not found."
        
        # Load all entities and generate relationships
        from ...services.entity_storage import load_entity
        entities = [person]
        
        # Load all meetings and find ones with this person
        person_meetings = []
        for meeting_file in ENTITIES_MEETINGS_DIR.glob("*.json"):
            try:
                meeting_id = UUID(meeting_file.stem)
                meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                if meeting:
                    # Check if person is host, documenter, or participant
                    # This is simplified - actual implementation would check participant lists
                    if meeting.host_id == person_id or meeting.documenter_id == person_id:
                        person_meetings.append(meeting)
                        entities.append(meeting)
            except (ValueError, AttributeError):
                continue
        
        # Generate relationship triples for each meeting
        all_triples = []
        for meeting in person_meetings:
            meeting_entities = entities + self._load_meeting_related_entities(meeting.id)
            triples = self.relationship_generator.generate_triples(meeting_entities, meeting.id)
            all_triples.extend(triples)
        
        # Filter to only triples involving this person
        person_triples = [
            t for t in all_triples
            if (t.subject_id == person_id and t.subject_type == "Person") or
               (t.object_id == person_id and t.object_type == "Person")
        ]
        
        return person_triples, canonical_name, None
    
    def get_relationships_for_meeting(
        self,
        meeting_id: UUID,
    ) -> tuple[List[RelationshipTriple], Optional[str]]:
        """
        Get relationships for a meeting entity.
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            Tuple of (relationship_triples, error_message)
        """
        # Load meeting
        meeting = self.entity_query_service.get_by_id(
            meeting_id,
            ENTITIES_MEETINGS_DIR,
            Meeting
        )
        
        if not meeting:
            return [], f"Meeting '{meeting_id}' not found."
        
        # Load all entities for this meeting
        entities = self._load_meeting_related_entities(meeting_id)
        entities.append(meeting)
        
        # Generate relationship triples
        triples = self.relationship_generator.generate_triples(entities, meeting_id)
        
        # Filter to only triples involving this meeting
        meeting_triples = [
            t for t in triples
            if t.subject_id == meeting_id or t.object_id == meeting_id
        ]
        
        return meeting_triples, None
    
    def _find_workgroup_by_name(self, name: str) -> Optional[Workgroup]:
        """Find workgroup by exact name match."""
        from ...services.entity_storage import load_entity
        for workgroup_file in ENTITIES_WORKGROUPS_DIR.glob("*.json"):
            try:
                workgroup_id = UUID(workgroup_file.stem)
                workgroup = load_entity(workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                if workgroup and workgroup.name.lower() == name.lower():
                    return workgroup
            except (ValueError, AttributeError):
                continue
        return None
    
    def _find_person_by_name(self, name: str) -> Optional[Person]:
        """Find person by exact name match."""
        from ...services.entity_storage import load_entity
        for person_file in ENTITIES_PEOPLE_DIR.glob("*.json"):
            try:
                person_id = UUID(person_file.stem)
                person = load_entity(person_id, ENTITIES_PEOPLE_DIR, Person)
                if person and person.display_name.lower() == name.lower():
                    return person
            except (ValueError, AttributeError):
                continue
        return None
    
    def _suggest_workgroups(self, name: str, limit: int = 3) -> List[str]:
        """Suggest similar workgroup names."""
        from rapidfuzz import fuzz
        from ...services.entity_storage import load_entity
        
        suggestions = []
        for workgroup_file in ENTITIES_WORKGROUPS_DIR.glob("*.json"):
            try:
                workgroup_id = UUID(workgroup_file.stem)
                workgroup = load_entity(workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                if workgroup:
                    similarity = fuzz.ratio(name.lower(), workgroup.name.lower())
                    if similarity >= 70:  # 70% similarity threshold
                        suggestions.append((workgroup.name, similarity))
            except (ValueError, AttributeError):
                continue
        
        # Sort by similarity and return top matches
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in suggestions[:limit]]
    
    def _suggest_people(self, name: str, limit: int = 3) -> List[str]:
        """Suggest similar person names."""
        from rapidfuzz import fuzz
        from ...services.entity_storage import load_entity
        
        suggestions = []
        for person_file in ENTITIES_PEOPLE_DIR.glob("*.json"):
            try:
                person_id = UUID(person_file.stem)
                person = load_entity(person_id, ENTITIES_PEOPLE_DIR, Person)
                if person:
                    similarity = fuzz.ratio(name.lower(), person.display_name.lower())
                    if similarity >= 70:  # 70% similarity threshold
                        suggestions.append((person.display_name, similarity))
            except (ValueError, AttributeError):
                continue
        
        # Sort by similarity and return top matches
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in suggestions[:limit]]
    
    def _load_meeting_related_entities(self, meeting_id: UUID) -> List:
        """Load all entities related to a meeting."""
        from ...services.entity_storage import load_entity
        
        entities = []
        
        # Load agenda items
        from ...lib.config import ENTITIES_AGENDA_ITEMS_DIR
        from ...models.agenda_item import AgendaItem
        for agenda_item_file in ENTITIES_AGENDA_ITEMS_DIR.glob("*.json"):
            try:
                agenda_item_id = UUID(agenda_item_file.stem)
                agenda_item = load_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
                if agenda_item and agenda_item.meeting_id == meeting_id:
                    entities.append(agenda_item)
            except (ValueError, AttributeError):
                continue
        
        # Load action items and decision items via agenda items
        for entity in entities[:]:  # Copy list to avoid modification during iteration
            if hasattr(entity, 'id'):
                agenda_item_id = entity.id
                # Load action items
                for action_file in ENTITIES_ACTION_ITEMS_DIR.glob("*.json"):
                    try:
                        action_id = UUID(action_file.stem)
                        action = load_entity(action_id, ENTITIES_ACTION_ITEMS_DIR, ActionItem)
                        if action and action.agenda_item_id == agenda_item_id:
                            entities.append(action)
                    except (ValueError, AttributeError):
                        continue
                
                # Load decision items
                for decision_file in ENTITIES_DECISION_ITEMS_DIR.glob("*.json"):
                    try:
                        decision_id = UUID(decision_file.stem)
                        decision = load_entity(decision_id, ENTITIES_DECISION_ITEMS_DIR, DecisionItem)
                        if decision and decision.agenda_item_id == agenda_item_id:
                            entities.append(decision)
                    except (ValueError, AttributeError):
                        continue
        
        return entities


def create_relationship_query_service() -> RelationshipQueryService:
    """
    Create a relationship query service instance.
    
    Returns:
        RelationshipQueryService instance
    """
    return RelationshipQueryService()


"""Entity query service for querying entities and relationships."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar
from uuid import UUID

from src.lib.config import (
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_MEETINGS_DIR,
    ENTITIES_PEOPLE_DIR,
    ENTITIES_DOCUMENTS_DIR,
    ENTITIES_AGENDA_ITEMS_DIR,
    ENTITIES_ACTION_ITEMS_DIR,
    ENTITIES_DECISION_ITEMS_DIR,
    ENTITIES_TAGS_DIR,
)
from src.lib.logging import get_logger
from src.services.entity_storage import load_entity, load_index
from src.models.meeting import Meeting
from src.models.workgroup import Workgroup
from src.models.person import Person
from src.models.action_item import ActionItem

logger = get_logger(__name__)

T = TypeVar("T")


class EntityQueryService:
    """
    Query service for entity relationships and lookups.
    
    Provides methods for querying entities by ID, name, and relationships
    using index files and directory scanning.
    """
    
    def get_by_id(
        self, 
        entity_id: UUID, 
        entity_dir: Path, 
        entity_class: type[T]
    ) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            entity_id: UUID of entity
            entity_dir: Directory path for entity type
            entity_class: Pydantic model class for entity
        
        Returns:
            Entity instance if found, None otherwise
        """
        return load_entity(entity_id, entity_dir, entity_class)
    
    def find_by_name(
        self,
        name: str,
        entity_dir: Path,
        entity_class: type[T],
        name_field: str = "name"
    ) -> Optional[T]:
        """
        Find entity by name field.
        
        Args:
            name: Name to search for
            entity_dir: Directory path for entity type
            entity_class: Pydantic model class for entity
            name_field: Field name to search (default: "name")
        
        Returns:
            Entity instance if found, None otherwise
        """
        # Scan directory for entity files
        for entity_file in entity_dir.glob("*.json"):
            try:
                entity_id = UUID(entity_file.stem)
                entity = load_entity(entity_id, entity_dir, entity_class)
                if entity and getattr(entity, name_field, None) == name:
                    return entity
            except (ValueError, AttributeError):
                continue
        
        return None
    
    def find_all(
        self,
        entity_dir: Path,
        entity_class: type[T],
        filter_func: Optional[Callable[[T], bool]] = None
    ) -> List[T]:
        """
        Find all entities matching optional filter function.
        
        Args:
            entity_dir: Directory path for entity type
            entity_class: Pydantic model class for entity
            filter_func: Optional filter function (entity) -> bool
        
        Returns:
            List of entity instances
        """
        entities = []
        
        for entity_file in entity_dir.glob("*.json"):
            try:
                entity_id = UUID(entity_file.stem)
                entity = load_entity(entity_id, entity_dir, entity_class)
                if entity:
                    if filter_func is None or filter_func(entity):
                        entities.append(entity)
            except (ValueError, AttributeError):
                continue
        
        return entities
    
    def get_meetings_by_workgroup(self, workgroup_id: UUID) -> List[Meeting]:
        """
        Get all meetings for a specific workgroup using index file.
        
        Args:
            workgroup_id: UUID of workgroup
        
        Returns:
            List of Meeting entities for the workgroup
        
        Raises:
            ValueError: If index data is invalid
        """
        logger.info("query_workgroup_start", workgroup_id=str(workgroup_id))
        
        try:
            index_data = load_index("meetings_by_workgroup")
            workgroup_id_str = str(workgroup_id)
            
            # Get meeting IDs from index
            meeting_ids_str = index_data.get(workgroup_id_str, [])
            logger.debug("query_workgroup_index_loaded", workgroup_id=str(workgroup_id), meeting_count=len(meeting_ids_str))
            
            # Load meeting entities
            meetings = []
            for meeting_id_str in meeting_ids_str:
                try:
                    meeting_id = UUID(meeting_id_str)
                    meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                    if meeting:
                        meetings.append(meeting)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_workgroup_meeting_load_failed", meeting_id=meeting_id_str, error=str(e))
                    continue
            
            logger.info("query_workgroup_success", workgroup_id=str(workgroup_id), meeting_count=len(meetings))
            return meetings
            
        except Exception as e:
            logger.error("query_workgroup_failed", workgroup_id=str(workgroup_id), error=str(e))
            raise
    
    def get_action_items_by_person(self, person_id: UUID) -> List[ActionItem]:
        """
        Get all action items assigned to a specific person.
        
        Args:
            person_id: UUID of person
        
        Returns:
            List of ActionItem entities assigned to the person
        
        Raises:
            ValueError: If entity loading fails
        """
        logger.info("query_action_items_by_person_start", person_id=str(person_id))
        
        try:
            # Scan action_items directory for items with matching assignee_id
            action_items = []
            
            for action_item_file in ENTITIES_ACTION_ITEMS_DIR.glob("*.json"):
                try:
                    action_item_id = UUID(action_item_file.stem)
                    action_item = load_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, ActionItem)
                    if action_item and action_item.assignee_id == person_id:
                        action_items.append(action_item)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_action_items_loading_failed", action_item_id=action_item_file.stem, error=str(e))
                    continue
            
            logger.info("query_action_items_by_person_success", person_id=str(person_id), action_item_count=len(action_items))
            return action_items
            
        except Exception as e:
            logger.error("query_action_items_by_person_failed", person_id=str(person_id), error=str(e))
            raise


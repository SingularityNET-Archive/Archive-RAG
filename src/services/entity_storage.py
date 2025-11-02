"""Entity storage service for JSON file-based entity operations."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, Generic
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
    ENTITIES_INDEX_DIR,
    ENTITIES_RELATIONS_DIR,
    init_entity_storage,
)
from src.lib.validation import validate_foreign_key
from src.models.base import BaseEntity
from src.models.workgroup import Workgroup
from src.models.meeting import Meeting
from src.models.person import Person
from src.models.agenda_item import AgendaItem
from src.models.action_item import ActionItem
from src.models.document import Document

T = TypeVar("T", bound=BaseEntity)


def init_entity_storage_directories() -> None:
    """
    Initialize entity storage directory structure.
    
    Creates all required directories for entity storage:
    - entities/workgroups/
    - entities/meetings/
    - entities/people/
    - entities/documents/
    - entities/agenda_items/
    - entities/action_items/
    - entities/decision_items/
    - entities/tags/
    - entities/_index/
    - entities/_relations/
    """
    init_entity_storage()


def save_entity(entity: BaseEntity, entity_dir: Path) -> None:
    """
    Save entity to JSON file using atomic write pattern (temp file + rename).
    
    Args:
        entity: Entity instance to save
        entity_dir: Directory path for entity type (e.g., ENTITIES_WORKGROUPS_DIR)
    
    Raises:
        IOError: If file write fails
    """
    entity_dir.mkdir(parents=True, exist_ok=True)
    entity_file = entity_dir / f"{entity.id}.json"
    temp_file = entity_dir / f"{entity.id}.json.tmp"
    
    try:
        # Write to temporary file first
        entity_dict = entity.model_dump(mode="json")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(entity_dict, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_file.replace(entity_file)
    except Exception as e:
        # Clean up temp file on error
        if temp_file.exists():
            temp_file.unlink()
        raise IOError(f"Failed to save entity {entity.id}: {e}") from e


def load_entity(entity_id: UUID, entity_dir: Path, entity_class: type[T]) -> Optional[T]:
    """
    Load entity from JSON file.
    
    Args:
        entity_id: UUID of entity to load
        entity_dir: Directory path for entity type
        entity_class: Pydantic model class for entity
    
    Returns:
        Entity instance if found, None otherwise
    
    Raises:
        ValueError: If entity data is invalid
    """
    entity_file = entity_dir / f"{entity_id}.json"
    
    if not entity_file.exists():
        return None
    
    try:
        with open(entity_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return entity_class(**data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in entity file {entity_file}: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load entity {entity_id}: {e}") from e


def delete_entity(entity_id: UUID, entity_dir: Path, backup_dir: Optional[Path] = None) -> bool:
    """
    Delete entity JSON file with backup/restore pattern for atomic deletion.
    
    Args:
        entity_id: UUID of entity to delete
        entity_dir: Directory path for entity type
        backup_dir: Optional backup directory for restore capability
    
    Returns:
        True if entity was deleted, False if entity not found
    
    Raises:
        IOError: If deletion fails
    """
    entity_file = entity_dir / f"{entity_id}.json"
    
    if not entity_file.exists():
        return False
    
    # Create backup if backup_dir provided
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"{entity_id}.json.bak"
        try:
            shutil.copy2(entity_file, backup_file)
        except Exception as e:
            raise IOError(f"Failed to create backup for entity {entity_id}: {e}") from e
    
    try:
        entity_file.unlink()
        return True
    except Exception as e:
        # Restore from backup if deletion fails
        if backup_dir:
            backup_file = backup_dir / f"{entity_id}.json.bak"
            if backup_file.exists():
                try:
                    shutil.copy2(backup_file, entity_file)
                except Exception:
                    pass  # Best effort restore
        raise IOError(f"Failed to delete entity {entity_id}: {e}") from e


def save_index(index_name: str, index_data: Dict[str, Any]) -> None:
    """
    Save index JSON file using atomic write pattern.
    
    Args:
        index_name: Name of index file (e.g., "meetings_by_workgroup")
        index_data: Dictionary containing index data
    
    Raises:
        IOError: If file write fails
    """
    index_file = ENTITIES_INDEX_DIR / f"{index_name}.json"
    temp_file = ENTITIES_INDEX_DIR / f"{index_name}.json.tmp"
    
    ENTITIES_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Write to temporary file first
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_file.replace(index_file)
    except Exception as e:
        # Clean up temp file on error
        if temp_file.exists():
            temp_file.unlink()
        raise IOError(f"Failed to save index {index_name}: {e}") from e


def load_index(index_name: str) -> Dict[str, Any]:
    """
    Load index JSON file.
    
    Args:
        index_name: Name of index file (e.g., "meetings_by_workgroup")
    
    Returns:
        Dictionary containing index data, empty dict if file doesn't exist
    
    Raises:
        ValueError: If index data is invalid JSON
    """
    index_file = ENTITIES_INDEX_DIR / f"{index_name}.json"
    
    if not index_file.exists():
        return {}
    
    try:
        with open(index_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Convert string keys to UUIDs for UUID-indexed indexes if needed
            return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in index file {index_file}: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load index {index_name}: {e}") from e


def save_workgroup(workgroup: Workgroup) -> None:
    """
    Save workgroup entity to JSON file.
    
    Args:
        workgroup: Workgroup entity instance
    
    Raises:
        ValueError: If workgroup validation fails
        IOError: If file write fails
    """
    save_entity(workgroup, ENTITIES_WORKGROUPS_DIR)


def save_meeting(meeting: Meeting) -> None:
    """
    Save meeting entity to JSON file and update meetings_by_workgroup index.
    
    Args:
        meeting: Meeting entity instance
    
    Raises:
        ValueError: If meeting validation fails or workgroup doesn't exist
        IOError: If file write fails
    """
    # Validate workgroup_id foreign key exists
    validate_foreign_key(
        meeting.workgroup_id,
        ENTITIES_WORKGROUPS_DIR,
        Workgroup,
        foreign_key_name="workgroup_id"
    )
    
    # Save meeting entity
    save_entity(meeting, ENTITIES_MEETINGS_DIR)
    
    # Update meetings_by_workgroup index
    index_name = "meetings_by_workgroup"
    index_data = load_index(index_name)
    
    # Get workgroup_id as string for JSON compatibility
    workgroup_id_str = str(meeting.workgroup_id)
    meeting_id_str = str(meeting.id)
    
    # Initialize workgroup entry if not exists
    if workgroup_id_str not in index_data:
        index_data[workgroup_id_str] = []
    
    # Add meeting_id if not already in list
    if meeting_id_str not in index_data[workgroup_id_str]:
        index_data[workgroup_id_str].append(meeting_id_str)
    
    # Save updated index
    save_index(index_name, index_data)


def save_person(person: Person) -> None:
    """
    Save person entity to JSON file.
    
    Args:
        person: Person entity instance
    
    Raises:
        ValueError: If person validation fails
        IOError: If file write fails
    """
    save_entity(person, ENTITIES_PEOPLE_DIR)


def save_agenda_item(agenda_item: AgendaItem) -> None:
    """
    Save agenda item entity to JSON file.
    
    Args:
        agenda_item: AgendaItem entity instance
    
    Raises:
        ValueError: If agenda item validation fails or meeting doesn't exist
        IOError: If file write fails
    """
    # Validate meeting_id foreign key exists
    validate_foreign_key(
        agenda_item.meeting_id,
        ENTITIES_MEETINGS_DIR,
        Meeting,
        foreign_key_name="meeting_id"
    )
    
    # Save agenda item entity
    save_entity(agenda_item, ENTITIES_AGENDA_ITEMS_DIR)


def save_action_item(action_item: ActionItem) -> None:
    """
    Save action item entity to JSON file.
    
    Args:
        action_item: ActionItem entity instance
    
    Raises:
        ValueError: If action item validation fails or foreign keys don't exist
        IOError: If file write fails
    """
    # Validate agenda_item_id foreign key exists
    validate_foreign_key(
        action_item.agenda_item_id,
        ENTITIES_AGENDA_ITEMS_DIR,
        AgendaItem,
        foreign_key_name="agenda_item_id"
    )
    
    # Validate assignee_id foreign key exists (if provided)
    if action_item.assignee_id:
        validate_foreign_key(
            action_item.assignee_id,
            ENTITIES_PEOPLE_DIR,
            Person,
            foreign_key_name="assignee_id"
        )
    
    # Save action item entity
    save_entity(action_item, ENTITIES_ACTION_ITEMS_DIR)


def save_document(document: Document) -> None:
    """
    Save document entity to JSON file.
    
    Args:
        document: Document entity instance
    
    Raises:
        ValueError: If document validation fails or meeting doesn't exist
        IOError: If file write fails
    """
    # Validate meeting_id foreign key exists
    validate_foreign_key(
        document.meeting_id,
        ENTITIES_MEETINGS_DIR,
        Meeting,
        foreign_key_name="meeting_id"
    )
    
    # Save document entity
    save_entity(document, ENTITIES_DOCUMENTS_DIR)


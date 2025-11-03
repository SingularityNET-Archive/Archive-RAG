"""Entity storage service for JSON file-based entity operations."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic
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
from src.lib.compliance import ConstitutionViolation
from src.lib.logging import get_logger
from src.models.base import BaseEntity

logger = get_logger(__name__)

from src.models.workgroup import Workgroup
from src.models.meeting import Meeting
from src.models.person import Person
from src.models.agenda_item import AgendaItem
from src.models.action_item import ActionItem
from src.models.document import Document
from src.models.decision_item import DecisionItem
from src.models.tag import Tag
from src.models.meeting_person import MeetingPerson

T = TypeVar("T", bound=BaseEntity)

def _get_compliance_checker():
    """Get singleton compliance checker instance."""
    from src.services.compliance_checker import get_compliance_checker
    return get_compliance_checker()


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
        ConstitutionViolation: If compliance violation detected
    """
    # Check compliance before saving
    checker = _get_compliance_checker()
    violations = checker.check_entity_operations()
    if violations:
        # Fail-fast on first violation
        raise violations[0]
    
    # Verify Python-only requirement (T037 - US2)
    # Check that entity operations use only Python standard library
    import sys
    module_names = [name for name in sys.modules.keys() if name.startswith(('json', 'pathlib', 'os'))]
    python_only_violations = checker.verify_python_standard_library_only(module_names)
    if python_only_violations:
        raise python_only_violations[0]
    
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
        
        # Check compliance after saving
        violations = checker.check_entity_operations()
        if violations:
            raise violations[0]
    except ConstitutionViolation:
        raise
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


def save_decision_item(decision_item: DecisionItem) -> None:
    """
    Save decision item entity to JSON file.
    
    Args:
        decision_item: DecisionItem entity instance
    
    Raises:
        ValueError: If decision item validation fails or agenda item doesn't exist
        IOError: If file write fails
    """
    # Validate agenda_item_id foreign key exists
    validate_foreign_key(
        decision_item.agenda_item_id,
        ENTITIES_AGENDA_ITEMS_DIR,
        AgendaItem,
        foreign_key_name="agenda_item_id"
    )
    
    # Save decision item entity
    save_entity(decision_item, ENTITIES_DECISION_ITEMS_DIR)


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


def save_tag(tag: Tag) -> None:
    """
    Save tag entity to JSON file.
    
    Args:
        tag: Tag entity instance
    
    Raises:
        ValueError: If tag validation fails or meeting doesn't exist
        IOError: If file write fails
    """
    # Validate meeting_id foreign key exists
    validate_foreign_key(
        tag.meeting_id,
        ENTITIES_MEETINGS_DIR,
        Meeting,
        foreign_key_name="meeting_id"
    )
    
    # Save tag entity
    save_entity(tag, ENTITIES_TAGS_DIR)


def save_meeting_person(meeting_person: MeetingPerson) -> None:
    """
    Save MeetingPerson junction record to relations file.
    
    Saves to entities/_relations/meeting_person.json as an array.
    Updates both index files: meeting_person_by_meeting and meeting_person_by_person.
    
    Args:
        meeting_person: MeetingPerson junction entity instance
    
    Raises:
        ValueError: If validation fails or meeting/person doesn't exist
        IOError: If file write fails
    """
    # Validate foreign keys exist
    validate_foreign_key(
        meeting_person.meeting_id,
        ENTITIES_MEETINGS_DIR,
        Meeting,
        foreign_key_name="meeting_id"
    )
    validate_foreign_key(
        meeting_person.person_id,
        ENTITIES_PEOPLE_DIR,
        Person,
        foreign_key_name="person_id"
    )
    
    # Load existing relations file
    relations_file = ENTITIES_RELATIONS_DIR / "meeting_person.json"
    ENTITIES_RELATIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load existing records
    existing_records = []
    if relations_file.exists():
        try:
            with open(relations_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    existing_records = existing_data
        except (json.JSONDecodeError, Exception):
            # If file is corrupted, start fresh
            existing_records = []
    
    # Check if this record already exists (same meeting_id + person_id)
    meeting_id_str = str(meeting_person.meeting_id)
    person_id_str = str(meeting_person.person_id)
    
    # Remove existing record with same meeting_id + person_id if present
    existing_records = [
        r for r in existing_records
        if not (r.get("meeting_id") == meeting_id_str and r.get("person_id") == person_id_str)
    ]
    
    # Add new record
    record_data = {
        "id": str(meeting_person.id),
        "meeting_id": meeting_id_str,
        "person_id": person_id_str,
        "role": meeting_person.role,
        "created_at": meeting_person.created_at.isoformat(),
        "updated_at": meeting_person.updated_at.isoformat()
    }
    existing_records.append(record_data)
    
    # Write to temporary file first (atomic write)
    temp_file = ENTITIES_RELATIONS_DIR / "meeting_person.json.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(existing_records, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_file.replace(relations_file)
    except Exception as e:
        # Clean up temp file on error
        if temp_file.exists():
            temp_file.unlink()
        raise IOError(f"Failed to save meeting_person relation: {e}") from e
    
    # Update index files
    _update_meeting_person_indexes(meeting_person.meeting_id, meeting_person.person_id, add=True)


def load_meeting_person(meeting_id: Optional[UUID] = None, person_id: Optional[UUID] = None) -> List[MeetingPerson]:
    """
    Load MeetingPerson junction records from relations file.
    
    Args:
        meeting_id: Optional filter by meeting_id
        person_id: Optional filter by person_id
    
    Returns:
        List of MeetingPerson entities matching filters
    
    Raises:
        ValueError: If relations file is invalid
    """
    relations_file = ENTITIES_RELATIONS_DIR / "meeting_person.json"
    
    if not relations_file.exists():
        return []
    
    try:
        with open(relations_file, "r", encoding="utf-8") as f:
            records_data = json.load(f)
        
        if not isinstance(records_data, list):
            return []
        
        # Convert to MeetingPerson entities
        meeting_persons = []
        for record_data in records_data:
            try:
                meeting_person = MeetingPerson(
                    id=UUID(record_data["id"]),
                    meeting_id=UUID(record_data["meeting_id"]),
                    person_id=UUID(record_data["person_id"]),
                    role=record_data.get("role"),
                    created_at=datetime.fromisoformat(record_data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(record_data["updated_at"].replace("Z", "+00:00"))
                )
                
                # Apply filters if provided
                if meeting_id and meeting_person.meeting_id != meeting_id:
                    continue
                if person_id and meeting_person.person_id != person_id:
                    continue
                
                meeting_persons.append(meeting_person)
            except (KeyError, ValueError, TypeError) as e:
                # Skip invalid records
                continue
        
        return meeting_persons
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in meeting_person relations file: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load meeting_person relations: {e}") from e


def _update_meeting_person_indexes(meeting_id: UUID, person_id: UUID, add: bool = True) -> None:
    """
    Update meeting-person index files.
    
    Args:
        meeting_id: Meeting UUID
        person_id: Person UUID
        add: If True, add to index; if False, remove from index
    """
    meeting_id_str = str(meeting_id)
    person_id_str = str(person_id)
    
    # Update meeting_person_by_meeting index
    index_by_meeting = load_index("meeting_person_by_meeting")
    if meeting_id_str not in index_by_meeting:
        index_by_meeting[meeting_id_str] = []
    
    if add:
        if person_id_str not in index_by_meeting[meeting_id_str]:
            index_by_meeting[meeting_id_str].append(person_id_str)
    else:
        if person_id_str in index_by_meeting[meeting_id_str]:
            index_by_meeting[meeting_id_str].remove(person_id_str)
        # Remove empty lists
        if not index_by_meeting[meeting_id_str]:
            del index_by_meeting[meeting_id_str]
    
    save_index("meeting_person_by_meeting", index_by_meeting)
    
    # Update meeting_person_by_person index
    index_by_person = load_index("meeting_person_by_person")
    if person_id_str not in index_by_person:
        index_by_person[person_id_str] = []
    
    if add:
        if meeting_id_str not in index_by_person[person_id_str]:
            index_by_person[person_id_str].append(meeting_id_str)
    else:
        if meeting_id_str in index_by_person[person_id_str]:
            index_by_person[person_id_str].remove(meeting_id_str)
        # Remove empty lists
        if not index_by_person[person_id_str]:
            del index_by_person[person_id_str]
    
    save_index("meeting_person_by_person", index_by_person)


def delete_person(person_id: UUID) -> None:
    """
    Delete person entity with cascade delete for associated action items.
    
    Cascade behavior: Deletes all action items assigned to this person.
    
    Args:
        person_id: UUID of person to delete
    
    Raises:
        IOError: If deletion fails
    """
    logger.info("delete_person_start", person_id=str(person_id))
    
    # Create backup directory
    backup_dir = ENTITIES_PEOPLE_DIR.parent / "_backup" / "people"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Find all action items assigned to this person
        action_items = []
        for action_item_file in ENTITIES_ACTION_ITEMS_DIR.glob("*.json"):
            try:
                action_item_id = UUID(action_item_file.stem)
                action_item = load_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, ActionItem)
                if action_item and action_item.assignee_id == person_id:
                    action_items.append(action_item_id)
            except (ValueError, AttributeError):
                continue
        
        # Cascade delete: Delete all action items first
        for action_item_id in action_items:
            delete_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, backup_dir)
            logger.debug("cascade_delete_action_item", person_id=str(person_id), action_item_id=str(action_item_id))
        
        # Delete person entity
        delete_entity(person_id, ENTITIES_PEOPLE_DIR, backup_dir)
        
        # Remove from meeting_person relations
        meeting_persons = load_meeting_person(person_id=person_id)
        for mp in meeting_persons:
            _update_meeting_person_indexes(mp.meeting_id, mp.person_id, add=False)
        
        # Remove from relations file
        relations_file = ENTITIES_RELATIONS_DIR / "meeting_person.json"
        if relations_file.exists():
            try:
                with open(relations_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
                records = [r for r in records if r.get("person_id") != str(person_id)]
                with open(relations_file, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, ensure_ascii=False)
            except Exception:
                pass  # Best effort cleanup
        
        logger.info("delete_person_success", person_id=str(person_id), action_items_deleted=len(action_items))
        
    except Exception as e:
        logger.error("delete_person_failed", person_id=str(person_id), error=str(e))
        raise


def delete_workgroup(workgroup_id: UUID) -> None:
    """
    Delete workgroup entity with cascade delete for all related entities.
    
    Cascade behavior: Deletes all meetings and their related entities:
    - Documents
    - AgendaItems
    - ActionItems
    - DecisionItems
    - Tags
    - MeetingPerson records
    
    Args:
        workgroup_id: UUID of workgroup to delete
    
    Raises:
        IOError: If deletion fails
    """
    from src.services.entity_query import EntityQueryService
    
    logger.info("delete_workgroup_start", workgroup_id=str(workgroup_id))
    
    # Create backup directory
    backup_dir = ENTITIES_WORKGROUPS_DIR.parent / "_backup" / "workgroups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Get all meetings for this workgroup
        query_service = EntityQueryService()
        meetings = query_service.get_meetings_by_workgroup(workgroup_id)
        
        # Cascade delete: Delete all meetings (which will cascade to their related entities)
        for meeting in meetings:
            delete_meeting(meeting.id)
        
        # Delete workgroup entity
        delete_entity(workgroup_id, ENTITIES_WORKGROUPS_DIR, backup_dir)
        
        logger.info("delete_workgroup_success", workgroup_id=str(workgroup_id), meetings_deleted=len(meetings))
        
    except Exception as e:
        logger.error("delete_workgroup_failed", workgroup_id=str(workgroup_id), error=str(e))
        raise


def delete_meeting(meeting_id: UUID) -> None:
    """
    Delete meeting entity with cascade delete for all related entities.
    
    Cascade behavior: Deletes all:
    - Documents
    - AgendaItems (which cascade to ActionItems and DecisionItems)
    - Tags
    - MeetingPerson records
    
    Args:
        meeting_id: UUID of meeting to delete
    
    Raises:
        IOError: If deletion fails
    """
    from src.services.entity_query import EntityQueryService
    
    logger.info("delete_meeting_start", meeting_id=str(meeting_id))
    
    # Create backup directory
    backup_dir = ENTITIES_MEETINGS_DIR.parent / "_backup" / "meetings"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        query_service = EntityQueryService()
        
        # Cascade delete: Delete all documents
        documents = query_service.get_documents_by_meeting(meeting_id)
        for document in documents:
            delete_entity(document.id, ENTITIES_DOCUMENTS_DIR, backup_dir)
        
        # Cascade delete: Delete all agenda items (which will cascade to action/decision items)
        agenda_items = []
        for agenda_item_file in ENTITIES_AGENDA_ITEMS_DIR.glob("*.json"):
            try:
                agenda_item_id = UUID(agenda_item_file.stem)
                agenda_item = load_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
                if agenda_item and agenda_item.meeting_id == meeting_id:
                    agenda_items.append(agenda_item_id)
            except (ValueError, AttributeError):
                continue
        
        for agenda_item_id in agenda_items:
            delete_agenda_item(agenda_item_id)
        
        # Cascade delete: Delete all tags
        tags = []
        for tag_file in ENTITIES_TAGS_DIR.glob("*.json"):
            try:
                tag_id = UUID(tag_file.stem)
                tag = load_entity(tag_id, ENTITIES_TAGS_DIR, Tag)
                if tag and tag.meeting_id == meeting_id:
                    tags.append(tag_id)
            except (ValueError, AttributeError):
                continue
        
        for tag_id in tags:
            delete_entity(tag_id, ENTITIES_TAGS_DIR, backup_dir)
        
        # Cascade delete: Delete all MeetingPerson records
        meeting_persons = load_meeting_person(meeting_id=meeting_id)
        for mp in meeting_persons:
            _update_meeting_person_indexes(mp.meeting_id, mp.person_id, add=False)
        
        # Remove from relations file
        relations_file = ENTITIES_RELATIONS_DIR / "meeting_person.json"
        if relations_file.exists():
            try:
                with open(relations_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
                records = [r for r in records if r.get("meeting_id") != str(meeting_id)]
                with open(relations_file, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, ensure_ascii=False)
            except Exception:
                pass  # Best effort cleanup
        
        # Update workgroup index
        meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
        if meeting:
            index_name = "meetings_by_workgroup"
            index_data = load_index(index_name)
            workgroup_id_str = str(meeting.workgroup_id)
            if workgroup_id_str in index_data:
                meeting_ids = index_data[workgroup_id_str]
                if str(meeting_id) in meeting_ids:
                    meeting_ids.remove(str(meeting_id))
                if not meeting_ids:
                    del index_data[workgroup_id_str]
                save_index(index_name, index_data)
        
        # Delete meeting entity
        delete_entity(meeting_id, ENTITIES_MEETINGS_DIR, backup_dir)
        
        logger.info("delete_meeting_success", meeting_id=str(meeting_id), 
                   documents_deleted=len(documents), agenda_items_deleted=len(agenda_items),
                   tags_deleted=len(tags), meeting_persons_deleted=len(meeting_persons))
        
    except Exception as e:
        logger.error("delete_meeting_failed", meeting_id=str(meeting_id), error=str(e))
        raise


def delete_agenda_item(agenda_item_id: UUID) -> None:
    """
    Delete agenda item entity with cascade delete for related items.
    
    Cascade behavior: Deletes all:
    - ActionItems
    - DecisionItems
    
    Args:
        agenda_item_id: UUID of agenda item to delete
    
    Raises:
        IOError: If deletion fails
    """
    logger.info("delete_agenda_item_start", agenda_item_id=str(agenda_item_id))
    
    # Create backup directory
    backup_dir = ENTITIES_AGENDA_ITEMS_DIR.parent / "_backup" / "agenda_items"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Cascade delete: Delete all action items
        action_items = []
        for action_item_file in ENTITIES_ACTION_ITEMS_DIR.glob("*.json"):
            try:
                action_item_id = UUID(action_item_file.stem)
                action_item = load_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, ActionItem)
                if action_item and action_item.agenda_item_id == agenda_item_id:
                    action_items.append(action_item_id)
            except (ValueError, AttributeError):
                continue
        
        for action_item_id in action_items:
            delete_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, backup_dir)
        
        # Cascade delete: Delete all decision items
        decision_items = []
        for decision_item_file in ENTITIES_DECISION_ITEMS_DIR.glob("*.json"):
            try:
                decision_item_id = UUID(decision_item_file.stem)
                decision_item = load_entity(decision_item_id, ENTITIES_DECISION_ITEMS_DIR, DecisionItem)
                if decision_item and decision_item.agenda_item_id == agenda_item_id:
                    decision_items.append(decision_item_id)
            except (ValueError, AttributeError):
                continue
        
        for decision_item_id in decision_items:
            delete_entity(decision_item_id, ENTITIES_DECISION_ITEMS_DIR, backup_dir)
        
        # Delete agenda item entity
        delete_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, backup_dir)
        
        logger.info("delete_agenda_item_success", agenda_item_id=str(agenda_item_id),
                   action_items_deleted=len(action_items), decision_items_deleted=len(decision_items))
        
    except Exception as e:
        logger.error("delete_agenda_item_failed", agenda_item_id=str(agenda_item_id), error=str(e))
        raise


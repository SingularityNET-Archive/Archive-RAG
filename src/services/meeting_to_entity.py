"""Service for converting MeetingRecord to entity models and saving to entity storage."""

from datetime import datetime, date as date_type
from typing import Optional, Dict, Any
from uuid import UUID

from src.models.meeting_record import MeetingRecord
from src.models.meeting import Meeting, MeetingType
from src.models.workgroup import Workgroup
from src.models.person import Person
from src.models.agenda_item import AgendaItem, AgendaItemStatus
from src.models.decision_item import DecisionItem, DecisionEffect
from src.models.action_item import ActionItem, ActionItemStatus
from src.models.document import Document
from src.services.entity_storage import (
    save_meeting,
    save_workgroup,
    save_person,
    save_agenda_item,
    save_decision_item,
    save_action_item,
    save_document,
    load_entity,
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_PEOPLE_DIR
)
from src.lib.logging import get_logger

logger = get_logger(__name__)


def convert_and_save_meeting_record(meeting_record: MeetingRecord) -> Meeting:
    """
    Convert MeetingRecord to Meeting entity and save to entity storage.
    
    This function also creates/updates related entities:
    - Workgroup (from workgroup_id and workgroup name)
    - Person entities (from host, documenter, participants)
    
    Args:
        meeting_record: MeetingRecord from ingestion
        
    Returns:
        Saved Meeting entity
        
    Raises:
        ValueError: If conversion fails
    """
    logger.info("converting_meeting_record_to_entity", 
               meeting_id=meeting_record.id,
               workgroup_id=meeting_record.workgroup_id)
    
    # Step 1: Ensure Workgroup entity exists
    if meeting_record.workgroup_id:
        workgroup_id = UUID(meeting_record.workgroup_id)
        workgroup = load_entity(workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
        
        if not workgroup:
            # Create workgroup if it doesn't exist
            workgroup = Workgroup(
                id=workgroup_id,
                name=meeting_record.workgroup or f"Workgroup {workgroup_id}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            save_workgroup(workgroup)
            logger.info("workgroup_created", workgroup_id=str(workgroup_id), name=workgroup.name)
        else:
            # Update workgroup name if provided and different
            if meeting_record.workgroup and workgroup.name != meeting_record.workgroup:
                workgroup.name = meeting_record.workgroup
                workgroup.updated_at = datetime.utcnow()
                save_workgroup(workgroup)
                logger.debug("workgroup_updated", workgroup_id=str(workgroup_id), name=workgroup.name)
    else:
        raise ValueError("MeetingRecord must have workgroup_id to convert to entity")
    
    # Step 2: Parse meeting date
    meeting_date: date_type
    if meeting_record.date:
        if isinstance(meeting_record.date, str):
            # Parse ISO 8601 date string
            try:
                meeting_date = datetime.fromisoformat(meeting_record.date.replace("Z", "+00:00")).date()
            except ValueError:
                # Try YYYY-MM-DD format
                meeting_date = datetime.strptime(meeting_record.date[:10], "%Y-%m-%d").date()
        else:
            meeting_date = meeting_record.date if isinstance(meeting_record.date, date_type) else date_type.today()
    else:
        raise ValueError("MeetingRecord must have a date to convert to entity")
    
    # Step 3: Parse meeting type
    meeting_type: Optional[MeetingType] = None
    if meeting_record.type:
        try:
            meeting_type = MeetingType(meeting_record.type)
        except ValueError:
            # Try case-insensitive match
            type_lower = meeting_record.type.lower()
            for mt in MeetingType:
                if mt.value.lower() == type_lower:
                    meeting_type = mt
                    break
    
    # Also check meetingInfo.typeOfMeeting
    if not meeting_type and meeting_record.meetingInfo and meeting_record.meetingInfo.typeOfMeeting:
        type_str = meeting_record.meetingInfo.typeOfMeeting
        try:
            meeting_type = MeetingType(type_str)
        except ValueError:
            type_lower = type_str.lower()
            for mt in MeetingType:
                if mt.value.lower() == type_lower:
                    meeting_type = mt
                    break
    
    # Step 4: Handle host and documenter (Person entities)
    host_id: Optional[UUID] = None
    documenter_id: Optional[UUID] = None
    
    if meeting_record.meetingInfo:
        # Get host name
        host_name = meeting_record.meetingInfo.host
        if host_name:
            host_id = get_or_create_person(host_name)
        
        # Get documenter name
        documenter_name = meeting_record.meetingInfo.documenter
        if documenter_name:
            documenter_id = get_or_create_person(documenter_name)
        
        # Process participants (peoplePresent is a comma-separated string)
        if meeting_record.meetingInfo.peoplePresent:
            participants = [p.strip() for p in meeting_record.meetingInfo.peoplePresent.split(",")]
            for participant_name in participants:
                if participant_name:  # Skip empty names
                    get_or_create_person(participant_name)
    
    # Step 5: Parse video link
    video_link: Optional[str] = None
    if meeting_record.meetingInfo and meeting_record.meetingInfo.meetingVideoLink:
        video_link = meeting_record.meetingInfo.meetingVideoLink
    
    # Step 6: Parse purpose
    purpose: Optional[str] = None
    if meeting_record.meetingInfo and meeting_record.meetingInfo.purpose:
        purpose = meeting_record.meetingInfo.purpose
    
    # Step 7: Handle timestamped video
    timestamped_video: Optional[Dict[str, Any]] = None
    if meeting_record.meetingInfo and meeting_record.meetingInfo.timestampedVideo:
        timestamped_video = meeting_record.meetingInfo.timestampedVideo
    
    # Step 8: Create Meeting entity
    # Generate meeting ID: Always use workgroup_id + date to ensure uniqueness
    # Even if record.id exists, it may be the same as workgroup_id (causing duplicates)
    import hashlib
    combined = f"{meeting_record.workgroup_id}_{meeting_date.isoformat()}"
    hash_bytes = hashlib.md5(combined.encode()).digest()[:16]
    meeting_id = UUID(bytes=hash_bytes)
    
    # Check if meeting already exists
    from src.lib.config import ENTITIES_MEETINGS_DIR
    existing_meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
    
    meeting = Meeting(
        id=meeting_id,
        workgroup_id=workgroup_id,
        meeting_type=meeting_type,
        date=meeting_date,
        host_id=host_id,
        documenter_id=documenter_id,
        purpose=purpose,
        video_link=video_link,
        timestamped_video=timestamped_video,
        no_summary_given=meeting_record.noSummaryGiven or False,
        canceled_summary=meeting_record.canceledSummary or False,
        created_at=existing_meeting.created_at if existing_meeting else datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Step 9: Save meeting entity (only if not already exists or if different)
    if not existing_meeting or existing_meeting.date != meeting_date:
        save_meeting(meeting)
        logger.info("meeting_entity_saved", meeting_id=str(meeting_id), workgroup_id=str(workgroup_id))
    else:
        logger.debug("meeting_entity_exists", meeting_id=str(meeting_id))
    
    # Step 10: Extract and save documents (workingDocs)
    if meeting_record.meetingInfo and meeting_record.meetingInfo.workingDocs:
        extract_documents(meeting_id, meeting_record.meetingInfo.workingDocs)
    
    # Step 11: Extract and save agenda items, decision items, and action items
    if meeting_record.agendaItems:
        extract_agenda_items_and_decisions(meeting_id, meeting_record.agendaItems)
    
    return meeting


def extract_documents(meeting_id: UUID, working_docs_data: list) -> None:
    """
    Extract document entities from meeting workingDocs.
    
    Args:
        meeting_id: UUID of the meeting
        working_docs_data: List of working document dictionaries
    """
    logger.info("extracting_documents_start", meeting_id=str(meeting_id), count=len(working_docs_data))
    
    import hashlib
    
    for doc_index, doc_data in enumerate(working_docs_data):
        if not isinstance(doc_data, dict):
            continue
        
        # Extract title and link
        title = doc_data.get("title", "")
        link = doc_data.get("link", "")
        
        if not title or not link:
            logger.warning("document_missing_fields", meeting_id=str(meeting_id), index=doc_index, title=title, has_link=bool(link))
            continue
        
        # Create document ID (deterministic from meeting_id + document index)
        doc_hash = hashlib.md5(f"{meeting_id}_{doc_index}_{link}".encode()).digest()[:16]
        document_id = UUID(bytes=doc_hash)
        
        # Create and save document entity
        try:
            document = Document(
                id=document_id,
                meeting_id=meeting_id,
                title=title.strip(),
                link=link.strip(),  # HttpUrl field will validate URL format
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            save_document(document)
            logger.debug("document_saved", document_id=str(document_id), meeting_id=str(meeting_id), title=title[:50])
        except Exception as e:
            logger.warning("document_save_failed", document_id=str(document_id), meeting_id=str(meeting_id), error=str(e))
            continue


def extract_agenda_items_and_decisions(meeting_id: UUID, agenda_items_data: list) -> None:
    """
    Extract agenda items, decision items, and action items from meeting record.
    
    Args:
        meeting_id: UUID of the meeting
        agenda_items_data: List of agenda item objects from MeetingRecord (Pydantic models or dicts)
    """
    logger.info("extracting_agenda_items_start", meeting_id=str(meeting_id), count=len(agenda_items_data))
    
    import hashlib
    
    for agenda_index, agenda_data in enumerate(agenda_items_data):
        # Handle both Pydantic models and dictionaries
        if hasattr(agenda_data, 'status'):
            # Pydantic model - access as attributes
            status_str = agenda_data.status or ""
            narrative = getattr(agenda_data, 'narrative', "") or ""
            decision_items_data = agenda_data.decisionItems or []
            action_items_data = agenda_data.actionItems or []
        elif isinstance(agenda_data, dict):
            # Dictionary - access as keys
            status_str = agenda_data.get("status", "")
            narrative = agenda_data.get("narrative", "")
            decision_items_data = agenda_data.get("decisionItems", [])
            action_items_data = agenda_data.get("actionItems", [])
        else:
            logger.warning("agenda_item_unexpected_type", type=type(agenda_data))
            continue
        
        # Create agenda item ID (deterministic from meeting_id + index)
        agenda_hash = hashlib.md5(f"{meeting_id}_{agenda_index}".encode()).digest()[:16]
        agenda_item_id = UUID(bytes=agenda_hash)
        
        # Parse status
        status = None
        if status_str:
            status_str = str(status_str).lower()
            try:
                status = AgendaItemStatus(status_str)
            except ValueError:
                # Try to match partial
                for s in AgendaItemStatus:
                    if s.value.lower() == status_str or status_str in s.value.lower():
                        status = s
                        break
        
        # Create and save agenda item
        agenda_item = AgendaItem(
            id=agenda_item_id,
            meeting_id=meeting_id,
            status=status,
            narrative=str(narrative) if narrative else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            save_agenda_item(agenda_item)
            logger.debug("agenda_item_saved", agenda_item_id=str(agenda_item_id), meeting_id=str(meeting_id))
        except Exception as e:
            logger.warning("agenda_item_save_failed", agenda_item_id=str(agenda_item_id), error=str(e))
            continue
        
        # Extract decision items
        if decision_items_data:
            extract_decision_items(agenda_item_id, decision_items_data)
        
        # Extract action items
        if action_items_data:
            extract_action_items(agenda_item_id, action_items_data)


def extract_decision_items(agenda_item_id: UUID, decision_items_data: list) -> None:
    """
    Extract decision items from agenda item data.
    
    Args:
        agenda_item_id: UUID of the parent agenda item
        decision_items_data: List of decision item dictionaries
    """
    import hashlib
    
    for decision_index, decision_data in enumerate(decision_items_data):
        if not isinstance(decision_data, dict):
            continue
        
        # Create decision item ID (deterministic from agenda_item_id + index)
        decision_hash = hashlib.md5(f"{agenda_item_id}_{decision_index}".encode()).digest()[:16]
        decision_item_id = UUID(bytes=decision_hash)
        
        # Extract decision text (required)
        decision_text = decision_data.get("decision", "")
        if not decision_text or not decision_text.strip():
            logger.warning("decision_item_missing_text", agenda_item_id=str(agenda_item_id), index=decision_index)
            continue
        
        # Extract rationale
        rationale = decision_data.get("rationale", "")
        
        # Extract effect
        effect_str = decision_data.get("effect", "")
        effect = None
        if effect_str:
            try:
                effect = DecisionEffect(effect_str)
            except ValueError:
                # Try to match partial
                for e in DecisionEffect:
                    if e.value.lower() == effect_str.lower() or effect_str.lower() in e.value.lower():
                        effect = e
                        break
        
        # Create and save decision item
        decision_item = DecisionItem(
            id=decision_item_id,
            agenda_item_id=agenda_item_id,
            decision=decision_text.strip(),
            rationale=rationale if rationale else None,
            effect=effect,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            save_decision_item(decision_item)
            logger.debug("decision_item_saved", decision_item_id=str(decision_item_id), agenda_item_id=str(agenda_item_id))
        except Exception as e:
            logger.warning("decision_item_save_failed", decision_item_id=str(decision_item_id), error=str(e))
            continue


def extract_action_items(agenda_item_id: UUID, action_items_data: list) -> None:
    """
    Extract action items from agenda item data.
    
    Args:
        agenda_item_id: UUID of the parent agenda item
        action_items_data: List of action item dictionaries
    """
    import hashlib
    
    for action_index, action_data in enumerate(action_items_data):
        if not isinstance(action_data, dict):
            continue
        
        # Create action item ID (deterministic from agenda_item_id + index)
        action_hash = hashlib.md5(f"{agenda_item_id}_{action_index}".encode()).digest()[:16]
        action_item_id = UUID(bytes=action_hash)
        
        # Extract text (required)
        text = action_data.get("text", "")
        if not text or not text.strip():
            logger.warning("action_item_missing_text", agenda_item_id=str(agenda_item_id), index=action_index)
            continue
        
        # Extract assignee
        assignee_name = action_data.get("assignee", "")
        assignee_id = None
        if assignee_name:
            try:
                assignee_id = get_or_create_person(assignee_name)
            except Exception as e:
                logger.warning("action_item_assignee_creation_failed", assignee=assignee_name, error=str(e))
        
        # Extract due date
        due_date_str = action_data.get("dueDate", "")
        due_date = None
        if due_date_str:
            # Try multiple date formats
            date_formats = [
                "%Y-%m-%d",  # ISO format
                "%d %B %Y",  # "15 January 2025"
                "%B %d, %Y",  # "January 15, 2025"
                "%d/%m/%Y",  # "15/01/2025"
                "%m/%d/%Y",  # "01/15/2025"
            ]
            for date_format in date_formats:
                try:
                    due_date = datetime.strptime(due_date_str, date_format).date()
                    break
                except ValueError:
                    continue
            if not due_date:
                logger.warning("action_item_due_date_parse_failed", due_date=due_date_str)
        
        # Extract status
        status_str = action_data.get("status", "").lower()
        status = None
        if status_str:
            try:
                status = ActionItemStatus(status_str)
            except ValueError:
                for s in ActionItemStatus:
                    if s.value.lower() == status_str or status_str in s.value.lower():
                        status = s
                        break
        
        # Create and save action item
        action_item = ActionItem(
            id=action_item_id,
            agenda_item_id=agenda_item_id,
            text=text.strip(),
            assignee_id=assignee_id,
            due_date=due_date,
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            save_action_item(action_item)
            logger.debug("action_item_saved", action_item_id=str(action_item_id), agenda_item_id=str(agenda_item_id))
        except Exception as e:
            logger.warning("action_item_save_failed", action_item_id=str(action_item_id), error=str(e))
            continue


def get_or_create_person(display_name: str) -> UUID:
    """
    Get or create Person entity by display name.
    
    Args:
        display_name: Person's display name
        
    Returns:
        Person UUID
    """
    from src.services.entity_query import EntityQueryService
    from src.lib.config import ENTITIES_PEOPLE_DIR
    
    # Clean display name
    display_name = display_name.strip()
    if not display_name:
        raise ValueError("Display name cannot be empty")
    
    entity_query = EntityQueryService()
    
    # Try to find existing person by name
    persons = entity_query.find_all(
        ENTITIES_PEOPLE_DIR,
        Person,
        filter_func=lambda p: p.display_name == display_name
    )
    
    if persons:
        return persons[0].id
    
    # Create new person with deterministic UUID from name
    import hashlib
    name_hash = hashlib.md5(display_name.encode()).digest()[:16]
    person_id = UUID(bytes=name_hash)
    
    # Check if UUID already exists with different name (collision)
    existing = load_entity(person_id, ENTITIES_PEOPLE_DIR, Person)
    if existing:
        # Use existing person
        logger.debug("person_uuid_collision_resolved", person_id=str(person_id), name=display_name)
        return existing.id
    
    person = Person(
        id=person_id,
        display_name=display_name,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    save_person(person)
    logger.debug("person_created", person_id=str(person_id), name=display_name)
    
    return person.id


def ingest_meetings_to_entities(source_url: str) -> int:
    """
    Ingest all meetings from source URL and save to entity storage.
    
    Args:
        source_url: URL to source JSON file
        
    Returns:
        Number of meetings successfully ingested
    """
    from src.services.ingestion import ingest_meeting_url
    
    logger.info("ingesting_meetings_to_entities_start", url=source_url)
    
    # Ingest meeting records
    meeting_records = ingest_meeting_url(source_url)
    
    successful = 0
    failed = 0
    
    for meeting_record, file_hash in meeting_records:
        try:
            convert_and_save_meeting_record(meeting_record)
            successful += 1
            if successful % 10 == 0:
                logger.info("ingestion_progress", successful=successful, total=len(meeting_records))
        except Exception as e:
            failed += 1
            logger.error("meeting_entity_conversion_failed",
                        meeting_id=meeting_record.id,
                        error=str(e))
            continue
    
    logger.info("ingesting_meetings_to_entities_complete",
               url=source_url,
               successful=successful,
               failed=failed,
               total=len(meeting_records))
    
    return successful


"""Service for converting MeetingRecord to entity models and saving to entity storage."""

from datetime import datetime, date as date_type
from typing import Optional, Dict, Any
from uuid import UUID

from src.models.meeting_record import MeetingRecord
from src.models.meeting import Meeting, MeetingType
from src.models.workgroup import Workgroup
from src.models.person import Person
from src.services.entity_storage import (
    save_meeting,
    save_workgroup,
    save_person,
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
    
    return meeting


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


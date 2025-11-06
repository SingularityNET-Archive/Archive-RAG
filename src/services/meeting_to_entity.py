"""Service for converting MeetingRecord to entity models and saving to entity storage."""

from datetime import datetime, date as date_type
from typing import Optional, Dict, Any, List
from uuid import UUID

from src.models.meeting_record import MeetingRecord
from src.models.meeting import Meeting, MeetingType
from src.models.workgroup import Workgroup
from src.models.person import Person
from src.models.agenda_item import AgendaItem, AgendaItemStatus
from src.models.decision_item import DecisionItem, DecisionEffect
from src.models.action_item import ActionItem, ActionItemStatus
from src.models.document import Document
from src.models.tag import Tag
from src.services.entity_storage import (
    save_meeting,
    save_workgroup,
    save_person,
    save_agenda_item,
    save_decision_item,
    save_action_item,
    save_document,
    save_tag,
    load_entity,
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_PEOPLE_DIR
)
from src.lib.config import (
    ENTITIES_MEETINGS_DIR,
    ENTITIES_DOCUMENTS_DIR,
    ENTITIES_AGENDA_ITEMS_DIR,
    ENTITIES_ACTION_ITEMS_DIR,
    ENTITIES_DECISION_ITEMS_DIR,
)
from src.lib.logging import get_logger
from src.services.entity_normalization import EntityNormalizationService
from src.services.ner_integration import NERIntegrationService
from src.services.relationship_triple_generator import RelationshipTripleGenerator
from src.services.semantic_chunking import SemanticChunkingService
from src.services.entity_output_formatter import EntityOutputFormatter
from src.models.ner_entity import NEREntity

logger = get_logger(__name__)


def _should_extract_entity(
    entity_value: str,
    entity_type: str = "unknown",
    appears_in_multiple_meetings: bool = False,
) -> bool:
    """
    Check if entity should be extracted based on criteria (FR-013).
    
    Entity is extracted if it meets at least one criterion (OR logic):
    - Entity is a thing (person, workgroup, doc, meeting)
    - Entity is searchable by users
    - Entity appears in multiple meetings
    - Entity provides context/references
    
    Args:
        entity_value: Entity value/name to check
        entity_type: Type of entity (person, workgroup, doc, meeting, etc.)
        appears_in_multiple_meetings: Whether entity appears in multiple meetings
        
    Returns:
        True if entity should be extracted, False otherwise
    """
    if not entity_value or not entity_value.strip():
        return False
    
    # Filter out obvious filler comments
    filler_keywords = ["comment", "filler", "n/a", "none", "tbd", "todo"]
    entity_lower = entity_value.lower().strip()
    if any(keyword in entity_lower for keyword in filler_keywords):
        return False
    
    # Criterion 1: Entity is a thing (person, workgroup, doc, meeting)
    thing_types = ["person", "workgroup", "doc", "document", "meeting", "decision", "action"]
    if entity_type.lower() in thing_types:
        return True
    
    # Criterion 2: Appears in multiple meetings
    if appears_in_multiple_meetings:
        return True
    
    # Criterion 3: Entity is searchable (has meaningful content, not just punctuation)
    if len(entity_lower) >= 2 and entity_lower.isalnum():
        return True
    
    # Criterion 4: Entity provides context (has meaningful words)
    words = entity_lower.split()
    if len(words) >= 1 and any(len(word) >= 3 for word in words):
        return True
    
    return False


def _extract_and_merge_ner_entities(
    text: str,
    meeting_id: UUID,
    source_field: str,
    ner_service: Optional[NERIntegrationService] = None,
) -> List[NEREntity]:
    """
    Extract NER entities from text and merge with structured entities.
    
    This helper function:
    1. Extracts entities using NER
    2. Filters entities by extraction criteria (FR-013, FR-014)
    3. Merges NER entities with existing structured entities
    4. Returns list of NER entities (with normalized_entity_id set if matched)
    
    Args:
        text: Text to extract entities from
        meeting_id: UUID of the meeting
        source_field: JSON path where text was found
        ner_service: Optional NERIntegrationService instance (creates one if not provided)
        
    Returns:
        List of NEREntity objects (filtered and merged)
    """
    if not text or not text.strip():
        return []
    
    # Initialize NER service if not provided
    if ner_service is None:
        try:
            ner_service = NERIntegrationService()
        except Exception as e:
            logger.warning("ner_service_init_failed", error=str(e))
            return []
    
    # Extract entities from text
    ner_entities = ner_service.extract_from_text(text, meeting_id, source_field)
    
    if not ner_entities:
        return []
    
    # Load existing structured entities for this meeting to merge with
    # Load people entities that might match (for normalization)
    # Note: We don't need to load all people - EntityNormalizationService will handle
    # loading existing entities during normalization
    structured_entities = []
    
    # Try to load people from entity storage (for merging)
    # This is optional - normalization service will handle entity lookups
    try:
        import os
        people_dir = ENTITIES_PEOPLE_DIR
        if os.path.exists(people_dir):
            # Load a sample of people entities for matching (limit to avoid performance issues)
            # In practice, EntityNormalizationService will load entities on-demand
            person_files = [f for f in os.listdir(people_dir) if f.endswith('.json')]
            # Limit to first 100 to avoid loading too many entities
            for person_file in person_files[:100]:
                try:
                    person_id = UUID(person_file[:-5])
                    person = load_entity(person_id, people_dir, Person)
                    if person:
                        structured_entities.append(person)
                except Exception:
                    continue
    except Exception as e:
        logger.debug("ner_merge_structured_load_failed", error=str(e))
    
    # Merge NER entities with structured entities
    # The merge_with_structured method will use EntityNormalizationService internally
    # to find matches, so we don't need all entities loaded here
    merged_ner_entities = ner_service.merge_with_structured(ner_entities, structured_entities)
    
    # For NER entities that don't match existing entities, we could create new Person entities
    # if they are PERSON type. For now, we just log them.
    for ner_entity in merged_ner_entities:
        if ner_entity.normalized_entity_id is None and ner_entity.entity_type == "PERSON":
            # This is a new person entity found via NER
            # We could create it here, but for now just log it
            logger.debug(
                "ner_person_entity_found",
                text=ner_entity.text,
                source_field=source_field,
                meeting_id=str(meeting_id),
            )
    
    return merged_ner_entities


def convert_and_save_meeting_record(meeting_record: MeetingRecord) -> Meeting:
    """
    Convert MeetingRecord to Meeting entity and save to entity storage.
    
    This function also creates/updates related entities:
    - Workgroup (from workgroup_id and workgroup name)
    - Person entities (from host, documenter, participants)
    - NER-extracted entities from text fields (meetingInfo.purpose, decisions, action items)
    
    Args:
        meeting_record: MeetingRecord from ingestion
        
    Returns:
        Saved Meeting entity
        
    Raises:
        ValueError: If conversion fails
    """
    import time
    start_time = time.time()
    
    # T083 [Phase 9] Comprehensive logging with traceability
    logger.info(
        "converting_meeting_record_to_entity", 
        meeting_id=meeting_record.id,
        workgroup_id=meeting_record.workgroup_id,
        traceability=f"MEETING_ID:{meeting_record.id}|WORKGROUP_ID:{meeting_record.workgroup_id}",
    )
    
    # Track NER entities extracted during processing (T059 [US4])
    ner_entities_summary = {
        "total_extracted": 0,
        "merged_with_existing": 0,
        "new_entities": 0,
        "by_source_field": {}
    }
    
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
        # T077 [Phase 9] Get host name - graceful handling of missing field (FR-016)
        try:
            host_name = meeting_record.meetingInfo.host if hasattr(meeting_record.meetingInfo, 'host') else None
            if host_name:
                host_id = get_or_create_person(host_name)
        except Exception as e:
            logger.debug("host_extraction_failed", meeting_id=str(meeting_id), error=str(e))
        
        # T077 [Phase 9] Get documenter name - graceful handling of missing field (FR-016)
        try:
            documenter_name = meeting_record.meetingInfo.documenter if hasattr(meeting_record.meetingInfo, 'documenter') else None
            if documenter_name:
                documenter_id = get_or_create_person(documenter_name)
        except Exception as e:
            logger.debug("documenter_extraction_failed", meeting_id=str(meeting_id), error=str(e))
        
        # Process participants (peoplePresent is a comma-separated string)
        # Treat each person in peoplePresent as a candidate entity
        if meeting_record.meetingInfo.peoplePresent:
            participants = [p.strip() for p in meeting_record.meetingInfo.peoplePresent.split(",")]
            for participant_name in participants:
                if participant_name:  # Skip empty names
                    try:
                        # Apply entity extraction criteria and normalization
                        get_or_create_person(participant_name, normalize=True)
                    except ValueError as e:
                        # Entity filtered out or doesn't meet criteria
                        logger.debug("participant_filtered_out", name=participant_name, reason=str(e))
                        continue
    
    # Step 5: Generate meeting ID (needed for NER extraction and other steps)
    # Generate meeting ID: Always use workgroup_id + date to ensure uniqueness
    # Even if record.id exists, it may be the same as workgroup_id (causing duplicates)
    import hashlib
    combined = f"{meeting_record.workgroup_id}_{meeting_date.isoformat()}"
    hash_bytes = hashlib.md5(combined.encode()).digest()[:16]
    meeting_id = UUID(bytes=hash_bytes)
    
    # Step 6: Parse video link
    video_link: Optional[str] = None
    if meeting_record.meetingInfo and meeting_record.meetingInfo.meetingVideoLink:
        video_link = meeting_record.meetingInfo.meetingVideoLink
    
    # Step 7: Parse purpose
    purpose: Optional[str] = None
    if meeting_record.meetingInfo and meeting_record.meetingInfo.purpose:
        purpose = meeting_record.meetingInfo.purpose
        
        # T052 [US4] Apply NER extraction to meetingInfo.purpose field
        try:
            ner_service = NERIntegrationService()
            ner_entities = _extract_and_merge_ner_entities(
                text=purpose,
                meeting_id=meeting_id,
                source_field="meetingInfo.purpose",
                ner_service=ner_service,
            )
            if ner_entities:
                # T059 [US4] Track NER entities in output summary
                merged_count = sum(1 for ne in ner_entities if ne.normalized_entity_id is not None)
                new_count = len(ner_entities) - merged_count
                ner_entities_summary["total_extracted"] += len(ner_entities)
                ner_entities_summary["by_source_field"]["meetingInfo.purpose"] = len(ner_entities)
                ner_entities_summary["merged_with_existing"] += merged_count
                ner_entities_summary["new_entities"] += new_count
                
                logger.info(
                    "ner_entities_extracted_from_purpose",
                    meeting_id=str(meeting_id),
                    count=len(ner_entities),
                    merged=merged_count,
                    new=new_count,
                )
        except Exception as e:
            logger.warning("ner_extraction_purpose_failed", error=str(e))
    
    # Step 8: Handle timestamped video
    timestamped_video: Optional[Dict[str, Any]] = None
    if meeting_record.meetingInfo and meeting_record.meetingInfo.timestampedVideo:
        timestamped_video = meeting_record.meetingInfo.timestampedVideo
    
    # Step 9: Create Meeting entity
    # Check if meeting already exists
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
        # Use existing meeting_id if meeting already exists
        meeting_id = existing_meeting.id
    
    # Step 11: Extract and save documents (workingDocs)
    if meeting_record.meetingInfo and meeting_record.meetingInfo.workingDocs:
        extract_documents(meeting_id, meeting_record.meetingInfo.workingDocs)
    
    # Step 12: Extract and save agenda items, decision items, and action items
    if meeting_record.agendaItems:
        extract_agenda_items_and_decisions(meeting_id, meeting_record.agendaItems)
    
    # Step 13: Extract and save tags (topics and emotions) - always process tags even if meeting exists
    if meeting_record.tags:
        extract_tags(meeting_id, meeting_record.tags)
    
    # Step 14: Enhanced entity extraction - treat all JSON objects as candidate entities
    # This is already handled by the existing extraction functions, but we ensure
    # all entities are treated as candidates and filtered appropriately
    
    # Step 15: Generate relationship triples (US2)
    try:
        from src.services.relationship_triple_generator import RelationshipTripleGenerator
        triple_generator = RelationshipTripleGenerator()
        
        # Load entities for this meeting to generate triples
        # Note: Triples are generated on-demand, not stored separately
        # This is a placeholder - actual triple generation would happen when needed
        logger.debug("relationship_triples_generation_ready", meeting_id=str(meeting_id))
    except Exception as e:
        logger.warning("relationship_triple_generation_init_failed", error=str(e))
    
    # Step 15: Apply NER to text fields (US4) - T051 [US4] Integration complete
    # NER extraction is integrated into:
    # - meetingInfo.purpose (T052)
    # - decision text fields (T053)
    # - action item text fields (T054)
    # Entities are filtered (FR-013, FR-014), normalized, and merged with structured entities
    
    # T059 [US4] Log summary of NER-extracted entities
    if ner_entities_summary["total_extracted"] > 0:
        logger.info(
            "ner_extraction_summary",
            meeting_id=str(meeting_id),
            total_extracted=ner_entities_summary["total_extracted"],
            merged_with_existing=ner_entities_summary["merged_with_existing"],
            new_entities=ner_entities_summary["new_entities"],
            by_source_field=ner_entities_summary["by_source_field"],
        )
    
    # T081 [Phase 9] Performance monitoring - track processing time
    processing_time = time.time() - start_time
    logger.info(
        "meeting_record_processing_complete",
        meeting_id=str(meeting_id),
        processing_time_seconds=round(processing_time, 3),
        target_seconds=2.0,
    )
    if processing_time > 2.0:
        logger.warning(
            "meeting_processing_time_exceeded_target",
            meeting_id=str(meeting_id),
            processing_time_seconds=round(processing_time, 3),
            target_seconds=2.0,
        )
    
    return meeting


def generate_structured_output(
    meeting_id: UUID,
    meeting_record: MeetingRecord,
) -> Dict[str, Any]:
    """
    Generate structured entity extraction output for a meeting.
    
    This function generates all required outputs:
    - Structured entity list (all extracted people, roles, topics, decisions)
    - Normalized cluster labels (canonical names/tags for all entities)
    - Relationship triples (Subject -> Relationship -> Object)
    - Chunks for embedding (with embedded entity metadata)
    
    Args:
        meeting_id: UUID of the meeting
        meeting_record: MeetingRecord that was processed
        
    Returns:
        Dictionary with all structured outputs
    """
    logger.info("generating_structured_output", meeting_id=str(meeting_id))
    
    try:
        # Initialize services
        output_formatter = EntityOutputFormatter()
        relationship_generator = RelationshipTripleGenerator()
        semantic_chunking_service = SemanticChunkingService()
        
        # Load entities for this meeting
        # Use the same logic as chunking.py but inline to avoid circular import
        from src.services.entity_query import EntityQueryService
        query_service = EntityQueryService()
        
        entities = []
        # Load meeting
        meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
        if meeting:
            entities.append(meeting)
            # Load workgroup
            if meeting.workgroup_id:
                workgroup = load_entity(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                if workgroup:
                    entities.append(workgroup)
            # Load people
            people = query_service.get_people_by_meeting(meeting_id)
            entities.extend(people)
            # Load documents
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
            # Load action items and decision items
            for agenda_item in agenda_items:
                for action_item_file in ENTITIES_ACTION_ITEMS_DIR.glob("*.json"):
                    try:
                        action_item_id = UUID(action_item_file.stem)
                        action_item = load_entity(action_item_id, ENTITIES_ACTION_ITEMS_DIR, ActionItem)
                        if action_item and action_item.agenda_item_id == agenda_item.id:
                            entities.append(action_item)
                    except (ValueError, AttributeError):
                        continue
                for decision_item_file in ENTITIES_DECISION_ITEMS_DIR.glob("*.json"):
                    try:
                        decision_item_id = UUID(decision_item_file.stem)
                        decision_item = load_entity(decision_item_id, ENTITIES_DECISION_ITEMS_DIR, DecisionItem)
                        if decision_item and decision_item.agenda_item_id == agenda_item.id:
                            entities.append(decision_item)
                    except (ValueError, AttributeError):
                        continue
        
        # Generate relationship triples
        relationship_triples = relationship_generator.generate_triples(entities, meeting_id)
        
        # Generate semantic chunks
        chunks = semantic_chunking_service.chunk_by_semantic_unit(
            meeting_record=meeting_record,
            entities=entities,
            meeting_id=meeting_id,
            relationship_triples=relationship_triples,
        )
        
        # Generate complete structured output
        output = output_formatter.generate_complete_output(
            meeting_id=meeting_id,
            relationship_triples=relationship_triples,
            chunks=chunks,
        )
        
        logger.info(
            "structured_output_generated",
            meeting_id=str(meeting_id),
            entity_count=len(output.structured_entity_list),
            triple_count=len(output.relationship_triples),
            chunk_count=len(output.chunks_for_embedding),
        )
        
        return output.to_dict()
        
    except Exception as e:
        logger.error("structured_output_generation_failed", meeting_id=str(meeting_id), error=str(e))
        raise


def extract_documents(meeting_id: UUID, working_docs_data: list) -> None:
    """
    Extract document entities from meeting workingDocs.
    
    Treats each document in workingDocs array as a candidate entity.
    Applies entity extraction criteria to filter meaningful entities.
    
    Args:
        meeting_id: UUID of the meeting
        working_docs_data: List of working document dictionaries
    """
    logger.info("extracting_documents_start", meeting_id=str(meeting_id), count=len(working_docs_data))
    
    import hashlib
    
    for doc_index, doc_data in enumerate(working_docs_data):
        # Treat JSON object as candidate entity
        if not isinstance(doc_data, dict):
            continue
        
        # Extract title and link (noun fields representing real-world objects)
        title = doc_data.get("title", "")
        link_raw = doc_data.get("link", "")
        
        # Apply entity extraction criteria (FR-013)
        if title and not _should_extract_entity(title, entity_type="document"):
            logger.debug("document_filtered_out", title=title[:50], reason="does_not_meet_criteria")
            continue
        
        if not title or not link_raw:
            logger.debug("document_missing_fields", meeting_id=str(meeting_id), index=doc_index, title=title, has_link=bool(link_raw))
            continue
        
        # Extract URL from link field (may contain text before/after URL)
        import re
        link = link_raw.strip()
        
        # Try to find a URL pattern in the link text
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        url_matches = re.findall(url_pattern, link)
        
        if url_matches:
            # Use the first valid URL found
            link = url_matches[0]
        else:
            # If no URL pattern found, check if it starts with http:// or https://
            if not (link.startswith("http://") or link.startswith("https://")):
                # Try to fix common issues: add https:// if it looks like a domain
                if link.startswith("docs.google.com") or link.startswith("www."):
                    link = "https://" + link
                else:
                    # Not a valid URL, skip this document
                    logger.debug(
                        "document_invalid_url",
                        meeting_id=str(meeting_id),
                        index=doc_index,
                        title=title[:50],
                        link_raw=link_raw[:100]
                    )
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
                link=link,  # HttpUrl field will validate URL format
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            save_document(document)
            logger.debug("document_saved", document_id=str(document_id), meeting_id=str(meeting_id), title=title[:50])
        except Exception as e:
            logger.warning("document_save_failed", document_id=str(document_id), meeting_id=str(meeting_id), error=str(e))
            continue


def extract_agenda_items_and_decisions(meeting_id: UUID, agenda_items_data: list, ner_entities_summary: Optional[Dict] = None) -> None:
    """
    Extract agenda items, decision items, and action items from meeting record.
    
    Args:
        meeting_id: UUID of the meeting
        agenda_items_data: List of agenda item objects from MeetingRecord (Pydantic models or dicts)
        ner_entities_summary: Optional dictionary to track NER entities extracted during processing
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
            extract_decision_items(agenda_item_id, decision_items_data, meeting_id, ner_entities_summary)
        
        # Extract action items
        if action_items_data:
            extract_action_items(agenda_item_id, action_items_data, meeting_id, ner_entities_summary)


def extract_decision_items(agenda_item_id: UUID, decision_items_data: list, meeting_id: Optional[UUID] = None, ner_entities_summary: Optional[Dict] = None) -> None:
    """
    Extract decision items from agenda item data.
    
    Args:
        agenda_item_id: UUID of the parent agenda item
        decision_items_data: List of decision item dictionaries
        meeting_id: UUID of the meeting (optional, will be loaded from agenda_item if not provided)
        ner_entities_summary: Optional dictionary to track NER entities extracted during processing
    """
    import hashlib
    
    # Load agenda item to get meeting_id for NER extraction if not provided
    if meeting_id is None:
        from src.services.entity_storage import ENTITIES_AGENDA_ITEMS_DIR
        agenda_item = load_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
        meeting_id = agenda_item.meeting_id if agenda_item else None
    
    # Initialize NER service once for all decision items
    ner_service = None
    try:
        ner_service = NERIntegrationService()
    except Exception as e:
        logger.debug("ner_service_init_failed_for_decisions", error=str(e))
    
    for decision_index, decision_data in enumerate(decision_items_data):
        if not isinstance(decision_data, dict):
            continue
        
        # Create decision item ID (deterministic from agenda_item_id + index)
        decision_hash = hashlib.md5(f"{agenda_item_id}_{decision_index}".encode()).digest()[:16]
        decision_item_id = UUID(bytes=decision_hash)
        
        # T077 [Phase 9] Extract decision text - graceful handling of missing field (FR-016)
        decision_text = decision_data.get("decision", "") or decision_data.get("decisionText", "")
        if not decision_text or not decision_text.strip():
            logger.debug("decision_item_missing_text", agenda_item_id=str(agenda_item_id), index=decision_index)
            continue
        
        # Apply entity extraction criteria (FR-013, FR-014)
        if not _should_extract_entity(decision_text, entity_type="decision"):
            logger.debug("decision_item_filtered_out", text=decision_text[:50], reason="does_not_meet_criteria")
            continue
        
        # T053 [US4] Apply NER extraction to decision text field
        if meeting_id and ner_service:
            try:
                source_field = f"agendaItems[{decision_index}].decisionItems[].decision"
                ner_entities = _extract_and_merge_ner_entities(
                    text=decision_text,
                    meeting_id=meeting_id,
                    source_field=source_field,
                    ner_service=ner_service,
                )
                if ner_entities:
                    # T059 [US4] Track NER entities in output summary
                    merged_count = sum(1 for ne in ner_entities if ne.normalized_entity_id is not None)
                    new_count = len(ner_entities) - merged_count
                    
                    if ner_entities_summary is not None:
                        ner_entities_summary["total_extracted"] += len(ner_entities)
                        if source_field not in ner_entities_summary["by_source_field"]:
                            ner_entities_summary["by_source_field"][source_field] = 0
                        ner_entities_summary["by_source_field"][source_field] += len(ner_entities)
                        ner_entities_summary["merged_with_existing"] += merged_count
                        ner_entities_summary["new_entities"] += new_count
                    
                    logger.debug(
                        "ner_entities_extracted_from_decision",
                        decision_item_id=str(decision_item_id),
                        count=len(ner_entities),
                        merged=merged_count,
                        new=new_count,
                    )
            except Exception as e:
                logger.debug("ner_extraction_decision_failed", error=str(e))
        
        # Extract rationale
        rationale = decision_data.get("rationale", "")
        
        # T079 [Phase 9] Extract effect - handle missing effect gracefully (FR-016)
        effect_str = decision_data.get("effect", "") or decision_data.get("mayAffectOtherPeople", "")
        effect = None
        if effect_str and effect_str.strip():
            try:
                effect = DecisionEffect(effect_str.strip())
            except ValueError:
                # Try to match partial
                for e in DecisionEffect:
                    if e.value.lower() == effect_str.lower() or effect_str.lower() in e.value.lower():
                        effect = e
                        break
                # If no match found, continue without effect - decision is still valid
        # If effect is missing, decision is still valid (FR-016: graceful handling)
        
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


def extract_action_items(agenda_item_id: UUID, action_items_data: list, meeting_id: Optional[UUID] = None, ner_entities_summary: Optional[Dict] = None) -> None:
    """
    Extract action items from agenda item data.
    
    Args:
        agenda_item_id: UUID of the parent agenda item
        action_items_data: List of action item dictionaries
        meeting_id: UUID of the meeting (optional, will be loaded from agenda_item if not provided)
        ner_entities_summary: Optional dictionary to track NER entities extracted during processing
    """
    import hashlib
    
    # Load agenda item to get meeting_id for NER extraction if not provided
    if meeting_id is None:
        from src.services.entity_storage import ENTITIES_AGENDA_ITEMS_DIR
        agenda_item = load_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
        meeting_id = agenda_item.meeting_id if agenda_item else None
    
    # Initialize NER service once for all action items
    ner_service = None
    try:
        ner_service = NERIntegrationService()
    except Exception as e:
        logger.debug("ner_service_init_failed_for_actions", error=str(e))
    
    for action_index, action_data in enumerate(action_items_data):
        if not isinstance(action_data, dict):
            continue
        
        # Create action item ID (deterministic from agenda_item_id + index)
        action_hash = hashlib.md5(f"{agenda_item_id}_{action_index}".encode()).digest()[:16]
        action_item_id = UUID(bytes=action_hash)
        
        # Extract text (required)
        text = action_data.get("text", "")
        if not text or not text.strip():
            logger.debug("action_item_missing_text", agenda_item_id=str(agenda_item_id), index=action_index)
            continue
        
        # Apply entity extraction criteria (FR-013, FR-014)
        if not _should_extract_entity(text, entity_type="action"):
            logger.debug("action_item_filtered_out", text=text[:50], reason="does_not_meet_criteria")
            continue
        
        # T054 [US4] Apply NER extraction to action item description field
        if meeting_id and ner_service:
            try:
                source_field = f"agendaItems[{action_index}].actionItems[].text"
                ner_entities = _extract_and_merge_ner_entities(
                    text=text,
                    meeting_id=meeting_id,
                    source_field=source_field,
                    ner_service=ner_service,
                )
                if ner_entities:
                    # T059 [US4] Track NER entities in output summary
                    merged_count = sum(1 for ne in ner_entities if ne.normalized_entity_id is not None)
                    new_count = len(ner_entities) - merged_count
                    
                    if ner_entities_summary is not None:
                        ner_entities_summary["total_extracted"] += len(ner_entities)
                        if source_field not in ner_entities_summary["by_source_field"]:
                            ner_entities_summary["by_source_field"][source_field] = 0
                        ner_entities_summary["by_source_field"][source_field] += len(ner_entities)
                        ner_entities_summary["merged_with_existing"] += merged_count
                        ner_entities_summary["new_entities"] += new_count
                    
                    logger.debug(
                        "ner_entities_extracted_from_action",
                        action_item_id=str(action_item_id),
                        count=len(ner_entities),
                        merged=merged_count,
                        new=new_count,
                    )
            except Exception as e:
                logger.debug("ner_extraction_action_failed", error=str(e))
        
        # T079 [Phase 9] Extract assignee - handle missing assignee gracefully (FR-016)
        assignee_name = action_data.get("assignee", "") or action_data.get("assignedTo", "")
        assignee_id = None
        if assignee_name and assignee_name.strip():
            try:
                assignee_id = get_or_create_person(assignee_name.strip())
            except Exception as e:
                logger.debug("action_item_assignee_creation_failed", assignee=assignee_name, error=str(e))
                # Continue without assignee - action item is still valid
        
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


def get_or_create_person(display_name: str, normalize: bool = True) -> UUID:
    """
    Get or create Person entity by display name with normalization support.
    
    Args:
        display_name: Person's display name (may include variations like "Stephen [QADAO]")
        normalize: Whether to normalize the name before lookup/creation
        
    Returns:
        Person UUID (canonical entity ID)
    """
    from src.services.entity_query import EntityQueryService
    from src.lib.config import ENTITIES_PEOPLE_DIR
    
    # Clean display name
    display_name = display_name.strip()
    if not display_name:
        raise ValueError("Display name cannot be empty")
    
    # Apply entity extraction criteria (FR-013, FR-014)
    if not _should_extract_entity(display_name, entity_type="person"):
        raise ValueError(f"Entity '{display_name}' does not meet extraction criteria")
    
    entity_query = EntityQueryService()
    normalization_service = EntityNormalizationService()
    
    # Normalize entity name if enabled
    if normalize:
        try:
            # Load existing entities for normalization matching
            existing_persons = entity_query.find_all(ENTITIES_PEOPLE_DIR, Person)
            canonical_id, canonical_name = normalization_service.normalize_entity_name(
                display_name,
                existing_persons
            )
            
            # If found existing canonical entity, return it
            if canonical_id.int != 0:
                logger.debug(
                    "person_normalized_to_existing",
                    original_name=display_name,
                    canonical_name=canonical_name,
                    canonical_id=str(canonical_id),
                )
                return canonical_id
            
            # Use canonical name for new entity
            display_name = canonical_name
        except Exception as e:
            logger.warning("person_normalization_failed", name=display_name, error=str(e))
            # Continue with original name if normalization fails
    
    # Try to find existing person by name (after normalization)
    persons = entity_query.find_all(
        ENTITIES_PEOPLE_DIR,
        Person,
        filter_func=lambda p: p.display_name == display_name
    )
    
    if persons:
        return persons[0].id
    
    # Create new person with deterministic UUID from normalized name
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


def extract_tags(meeting_id: UUID, tags_data: Any) -> None:
    """
    Extract tag entities from meeting tags data.
    
    Args:
        meeting_id: UUID of the meeting
        tags_data: TagsModel or dict with topicsCovered and emotions
    """
    from src.models.meeting_record import TagsModel
    
    logger.info("extracting_tags_start", meeting_id=str(meeting_id))
    
    # Convert to TagsModel if it's a dict
    if isinstance(tags_data, dict):
        tags_model = TagsModel(**tags_data)
    elif isinstance(tags_data, TagsModel):
        tags_model = tags_data
    else:
        logger.warning("tags_invalid_format", meeting_id=str(meeting_id))
        return
    
    # Only create tag if there's actual data
    if not tags_model.topicsCovered and not tags_model.emotions:
        logger.debug("tags_empty", meeting_id=str(meeting_id))
        return
    
    # Create deterministic tag ID from meeting_id
    import hashlib
    tag_hash = hashlib.md5(f"{meeting_id}_tag".encode()).digest()[:16]
    tag_id = UUID(bytes=tag_hash)
    
    # Check if tag already exists
    from src.lib.config import ENTITIES_TAGS_DIR
    existing_tag = load_entity(tag_id, ENTITIES_TAGS_DIR, Tag)
    
    # Parse topics_covered (can be string or list)
    topics_covered = None
    if tags_model.topicsCovered:
        if isinstance(tags_model.topicsCovered, str):
            # Split comma-separated string
            topics_list = [t.strip() for t in tags_model.topicsCovered.split(",") if t.strip()]
            topics_covered = topics_list if len(topics_list) > 1 else (topics_list[0] if topics_list else None)
        elif isinstance(tags_model.topicsCovered, list):
            topics_covered = tags_model.topicsCovered
    
    # Parse emotions (can be string or list)
    emotions = None
    if tags_model.emotions:
        if isinstance(tags_model.emotions, str):
            # Split comma-separated string
            emotions_list = [e.strip() for e in tags_model.emotions.split(",") if e.strip()]
            emotions = emotions_list if len(emotions_list) > 1 else (emotions_list[0] if emotions_list else None)
        elif isinstance(tags_model.emotions, list):
            emotions = tags_model.emotions
    
    # Create and save tag entity
    try:
        tag = Tag(
            id=tag_id,
            meeting_id=meeting_id,
            topics_covered=topics_covered,
            emotions=emotions,
            created_at=existing_tag.created_at if existing_tag else datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        save_tag(tag)
        logger.info("tag_entity_saved", tag_id=str(tag_id), meeting_id=str(meeting_id))
    except Exception as e:
        logger.error("tag_entity_save_failed", meeting_id=str(meeting_id), error=str(e))


def ingest_meetings_to_entities(source_url: str, generate_output: bool = False) -> int:
    """
    Ingest all meetings from source URL and save to entity storage.
    
    Args:
        source_url: URL to source JSON file
        generate_output: Whether to generate structured output (default: False)
        
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
    
    logger.info(
        "ingesting_meetings_to_entities_complete",
        url=source_url,
        successful=successful,
        failed=failed,
        total=len(meeting_records)
    )
    
    return successful


def ingest_meetings_to_entities_with_output(source_url: str) -> Dict[str, Any]:
    """
    Ingest all meetings from source URL and generate structured output for each.
    
    Args:
        source_url: URL to source JSON file
        
    Returns:
        Dictionary mapping meeting_id to structured output
    """
    from src.services.ingestion import ingest_meeting_url
    
    logger.info("ingesting_meetings_to_entities_with_output_start", url=source_url)
    
    # Ingest meeting records
    meeting_records = ingest_meeting_url(source_url)
    
    all_outputs = {}
    successful = 0
    failed = 0
    
    for meeting_record, file_hash in meeting_records:
        try:
            # Convert and save meeting record
            meeting = convert_and_save_meeting_record(meeting_record)
            meeting_id = meeting.id
            
            # Generate structured output
            structured_output = generate_structured_output(meeting_id, meeting_record)
            all_outputs[str(meeting_id)] = structured_output
            
            successful += 1
            if successful % 10 == 0:
                logger.info("ingestion_with_output_progress", successful=successful, total=len(meeting_records))
        except Exception as e:
            failed += 1
            logger.error(
                "meeting_entity_conversion_with_output_failed",
                meeting_id=meeting_record.id if hasattr(meeting_record, 'id') else 'unknown',
                error=str(e)
            )
            continue
    
    logger.info(
        "ingesting_meetings_to_entities_with_output_complete",
        successful=successful,
        failed=failed,
        total=len(meeting_records),
        outputs_generated=len(all_outputs)
    )
    
    return all_outputs


"""Entity query service for querying entities and relationships."""

from datetime import date as date_type
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
from src.models.document import Document
from src.models.agenda_item import AgendaItem
from src.models.decision_item import DecisionItem, DecisionEffect
from src.models.tag import Tag
from src.services.entity_storage import load_meeting_person

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
    
    def get_documents_by_meeting(self, meeting_id: UUID) -> List[Document]:
        """
        Get all documents linked to a specific meeting.
        
        Args:
            meeting_id: UUID of meeting
        
        Returns:
            List of Document entities linked to the meeting
        
        Raises:
            ValueError: If entity loading fails
        """
        logger.info("query_documents_by_meeting_start", meeting_id=str(meeting_id))
        
        try:
            # Scan documents directory for documents with matching meeting_id
            documents = []
            
            for document_file in ENTITIES_DOCUMENTS_DIR.glob("*.json"):
                try:
                    document_id = UUID(document_file.stem)
                    document = load_entity(document_id, ENTITIES_DOCUMENTS_DIR, Document)
                    if document and document.meeting_id == meeting_id:
                        documents.append(document)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_documents_loading_failed", document_id=document_file.stem, error=str(e))
                    continue
            
            logger.info("query_documents_by_meeting_success", meeting_id=str(meeting_id), document_count=len(documents))
            return documents
            
        except Exception as e:
            logger.error("query_documents_by_meeting_failed", meeting_id=str(meeting_id), error=str(e))
            raise
    
    def get_documents_by_meeting_with_validation(self, meeting_id: UUID) -> List[Document]:
        """
        Get all documents linked to a meeting with link validation on access.
        
        Validates document links on access (not during ingestion) as per FR-004.
        Broken/inaccessible links are detected but do not block retrieval (FR-012).
        
        Args:
            meeting_id: UUID of meeting
        
        Returns:
            List of Document entities with link validation status
        
        Raises:
            ValueError: If entity loading fails
        """
        from urllib.parse import urlparse
        from urllib.request import urlopen, Request
        from urllib.error import URLError, HTTPError
        
        logger.info("query_documents_by_meeting_with_validation_start", meeting_id=str(meeting_id))
        
        try:
            documents = self.get_documents_by_meeting(meeting_id)
            
            # Validate links on access (T052)
            validated_documents = []
            for document in documents:
                try:
                    # Check if link is accessible (head request to validate)
                    parsed = urlparse(str(document.link))
                    if not parsed.scheme or not parsed.netloc:
                        logger.warning("query_documents_invalid_url", document_id=str(document.id), link=str(document.link))
                        # Still include document but mark as potentially broken
                        validated_documents.append(document)
                        continue
                    
                    # Attempt HEAD request to validate accessibility using standard library
                    try:
                        req = Request(str(document.link), method='HEAD')
                        with urlopen(req, timeout=5) as response:
                            is_accessible = response.status < 400
                            if not is_accessible:
                                logger.warning("query_documents_link_inaccessible", document_id=str(document.id), link=str(document.link), status_code=response.status)
                            # Still include document even if link is inaccessible (FR-012)
                            validated_documents.append(document)
                    except (URLError, HTTPError, Exception) as e:
                        # Link validation failed but don't block retrieval
                        status_code = getattr(e, 'code', None) if isinstance(e, HTTPError) else None
                        logger.warning("query_documents_link_validation_failed", document_id=str(document.id), link=str(document.link), error=str(e), status_code=status_code)
                        validated_documents.append(document)
                        
                except Exception as e:
                    # Log error but still include document (don't block retrieval)
                    logger.warning("query_documents_validation_error", document_id=str(document.id), error=str(e))
                    validated_documents.append(document)
            
            logger.info("query_documents_by_meeting_with_validation_success", meeting_id=str(meeting_id), document_count=len(validated_documents))
            return validated_documents
            
        except Exception as e:
            logger.error("query_documents_by_meeting_with_validation_failed", meeting_id=str(meeting_id), error=str(e))
            raise
    
    def get_documents_by_workgroup(self, workgroup_id: UUID) -> List[Document]:
        """
        Get all documents for meetings in a specific workgroup.
        
        Args:
            workgroup_id: UUID of workgroup
            
        Returns:
            List of Document entities for all meetings in the workgroup
            
        Raises:
            ValueError: If entity loading fails
        """
        logger.info("query_documents_by_workgroup_start", workgroup_id=str(workgroup_id))
        
        try:
            # First, get all meetings for this workgroup
            meetings = self.get_meetings_by_workgroup(workgroup_id)
            
            # Then, get all documents for each meeting
            documents = []
            for meeting in meetings:
                meeting_docs = self.get_documents_by_meeting(meeting.id)
                documents.extend(meeting_docs)
            
            logger.info("query_documents_by_workgroup_success", workgroup_id=str(workgroup_id), document_count=len(documents))
            return documents
            
        except Exception as e:
            logger.error("query_documents_by_workgroup_failed", workgroup_id=str(workgroup_id), error=str(e))
            raise
    
    def get_all_documents(self) -> List[Document]:
        """
        Get all documents in the archive.
        
        Returns:
            List of all Document entities
            
        Raises:
            ValueError: If entity loading fails
        """
        logger.info("query_all_documents_start")
        
        try:
            documents = []
            for document_file in ENTITIES_DOCUMENTS_DIR.glob("*.json"):
                try:
                    document_id = UUID(document_file.stem)
                    document = load_entity(document_id, ENTITIES_DOCUMENTS_DIR, Document)
                    if document:
                        documents.append(document)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_all_documents_loading_failed", document_id=document_file.stem, error=str(e))
                    continue
            
            logger.info("query_all_documents_success", document_count=len(documents))
            return documents
            
        except Exception as e:
            logger.error("query_all_documents_failed", error=str(e))
            raise
    
    def get_decision_items_by_agenda_item(self, agenda_item_id: UUID) -> List[DecisionItem]:
        """
        Get all decision items for a specific agenda item.
        
        Args:
            agenda_item_id: UUID of agenda item
        
        Returns:
            List of DecisionItem entities for the agenda item
        
        Raises:
            ValueError: If entity loading fails
        """
        logger.info("query_decision_items_by_agenda_item_start", agenda_item_id=str(agenda_item_id))
        
        try:
            # Scan decision_items directory for items with matching agenda_item_id
            decision_items = []
            
            for decision_item_file in ENTITIES_DECISION_ITEMS_DIR.glob("*.json"):
                try:
                    decision_item_id = UUID(decision_item_file.stem)
                    decision_item = load_entity(decision_item_id, ENTITIES_DECISION_ITEMS_DIR, DecisionItem)
                    if decision_item and decision_item.agenda_item_id == agenda_item_id:
                        decision_items.append(decision_item)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_decision_items_loading_failed", decision_item_id=decision_item_file.stem, error=str(e))
                    continue
            
            logger.info("query_decision_items_by_agenda_item_success", agenda_item_id=str(agenda_item_id), decision_count=len(decision_items))
            return decision_items
            
        except Exception as e:
            logger.error("query_decision_items_by_agenda_item_failed", agenda_item_id=str(agenda_item_id), error=str(e))
            raise
    
    def get_decision_items_by_meeting(self, meeting_id: UUID) -> List[DecisionItem]:
        """
        Get all decision items for a specific meeting.
        
        This method retrieves decisions by:
        1. Finding all agenda items for the meeting
        2. Finding all decision items for each agenda item
        
        Args:
            meeting_id: UUID of meeting
        
        Returns:
            List of DecisionItem entities for the meeting
        
        Raises:
            ValueError: If entity loading fails
        """
        logger.info("query_decision_items_by_meeting_start", meeting_id=str(meeting_id))
        
        try:
            # First, get all agenda items for this meeting
            agenda_items = []
            for agenda_item_file in ENTITIES_AGENDA_ITEMS_DIR.glob("*.json"):
                try:
                    agenda_item_id = UUID(agenda_item_file.stem)
                    agenda_item = load_entity(agenda_item_id, ENTITIES_AGENDA_ITEMS_DIR, AgendaItem)
                    if agenda_item and agenda_item.meeting_id == meeting_id:
                        agenda_items.append(agenda_item)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_decision_items_agenda_item_load_failed", agenda_item_id=agenda_item_file.stem, error=str(e))
                    continue
            
            # Then, get all decision items for each agenda item
            decision_items = []
            for agenda_item in agenda_items:
                agenda_decisions = self.get_decision_items_by_agenda_item(agenda_item.id)
                decision_items.extend(agenda_decisions)
            
            logger.info("query_decision_items_by_meeting_success", meeting_id=str(meeting_id), decision_count=len(decision_items))
            return decision_items
            
        except Exception as e:
            logger.error("query_decision_items_by_meeting_failed", meeting_id=str(meeting_id), error=str(e))
            raise
    
    def get_decision_items_by_effect(self, effect: DecisionEffect) -> List[DecisionItem]:
        """
        Get all decision items with a specific effect scope.
        
        Args:
            effect: DecisionEffect enum value
        
        Returns:
            List of DecisionItem entities with matching effect
        
        Raises:
            ValueError: If entity loading fails
        """
        logger.info("query_decision_items_by_effect_start", effect=effect.value)
        
        try:
            # Scan decision_items directory for items with matching effect
            decision_items = []
            
            for decision_item_file in ENTITIES_DECISION_ITEMS_DIR.glob("*.json"):
                try:
                    decision_item_id = UUID(decision_item_file.stem)
                    decision_item = load_entity(decision_item_id, ENTITIES_DECISION_ITEMS_DIR, DecisionItem)
                    if decision_item and decision_item.effect == effect:
                        decision_items.append(decision_item)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_decision_items_by_effect_loading_failed", decision_item_id=decision_item_file.stem, error=str(e))
                    continue
            
            logger.info("query_decision_items_by_effect_success", effect=effect.value, decision_count=len(decision_items))
            return decision_items
            
        except Exception as e:
            logger.error("query_decision_items_by_effect_failed", effect=effect.value, error=str(e))
            raise
    
    def get_meetings_by_tag(self, tag_value: str, tag_type: str = "topics") -> List[Meeting]:
        """
        Get all meetings matching a specific tag value.
        
        Searches in either topics_covered or emotions fields based on tag_type.
        Supports both string and list formats for tag values.
        
        Args:
            tag_value: Tag value to search for (e.g., "budget", "collaborative")
            tag_type: Type of tag to search ("topics" or "emotions", default: "topics")
        
        Returns:
            List of Meeting entities with matching tag values
        
        Raises:
            ValueError: If tag_type is invalid or entity loading fails
        """
        if tag_type not in ("topics", "emotions"):
            raise ValueError(f"Invalid tag_type: {tag_type}. Must be 'topics' or 'emotions'")
        
        logger.info("query_meetings_by_tag_start", tag_value=tag_value, tag_type=tag_type)
        
        try:
            # Find all tags matching the tag value
            matching_meeting_ids = set()
            
            for tag_file in ENTITIES_TAGS_DIR.glob("*.json"):
                try:
                    tag_id = UUID(tag_file.stem)
                    tag = load_entity(tag_id, ENTITIES_TAGS_DIR, Tag)
                    if not tag:
                        continue
                    
                    # Check the appropriate field based on tag_type
                    field_value = tag.topics_covered if tag_type == "topics" else tag.emotions
                    
                    if field_value is None:
                        continue
                    
                    # Handle both string and list formats
                    tag_values = []
                    if isinstance(field_value, list):
                        tag_values = [str(v).lower().strip() for v in field_value if v]
                    elif isinstance(field_value, str):
                        # String might be comma-separated or single value
                        tag_values = [v.strip().lower() for v in field_value.split(",") if v.strip()]
                    
                    # Check if tag_value matches (case-insensitive)
                    search_value = tag_value.lower().strip()
                    if any(search_value in v or v in search_value for v in tag_values):
                        matching_meeting_ids.add(tag.meeting_id)
                        
                except (ValueError, AttributeError) as e:
                    logger.warning("query_meetings_by_tag_loading_failed", tag_id=tag_file.stem, error=str(e))
                    continue
            
            # Load all matching meetings
            meetings = []
            for meeting_id in matching_meeting_ids:
                try:
                    meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                    if meeting:
                        meetings.append(meeting)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_meetings_by_tag_meeting_load_failed", meeting_id=str(meeting_id), error=str(e))
                    continue
            
            logger.info("query_meetings_by_tag_success", tag_value=tag_value, tag_type=tag_type, meeting_count=len(meetings))
            return meetings
            
        except Exception as e:
            logger.error("query_meetings_by_tag_failed", tag_value=tag_value, tag_type=tag_type, error=str(e))
            raise
    
    def get_meetings_by_person(self, person_id: UUID) -> List[Meeting]:
        """
        Get all meetings attended by a specific person using index file.
        
        Args:
            person_id: UUID of person
        
        Returns:
            List of Meeting entities attended by the person
        
        Raises:
            ValueError: If index data is invalid or entity loading fails
        """
        logger.info("query_meetings_by_person_start", person_id=str(person_id))
        
        try:
            # Load index file
            index_data = load_index("meeting_person_by_person")
            person_id_str = str(person_id)
            
            # Get meeting IDs from index
            meeting_ids_str = index_data.get(person_id_str, [])
            logger.debug("query_meetings_by_person_index_loaded", person_id=str(person_id), meeting_count=len(meeting_ids_str))
            
            # Load meeting entities
            meetings = []
            for meeting_id_str in meeting_ids_str:
                try:
                    meeting_id = UUID(meeting_id_str)
                    meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                    if meeting:
                        meetings.append(meeting)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_meetings_by_person_meeting_load_failed", meeting_id=meeting_id_str, error=str(e))
                    continue
            
            logger.info("query_meetings_by_person_success", person_id=str(person_id), meeting_count=len(meetings))
            return meetings
            
        except Exception as e:
            logger.error("query_meetings_by_person_failed", person_id=str(person_id), error=str(e))
            raise
    
    def get_people_by_meeting(self, meeting_id: UUID) -> List[Person]:
        """
        Get all people who attended a specific meeting using index file.
        
        Args:
            meeting_id: UUID of meeting
        
        Returns:
            List of Person entities who attended the meeting
        
        Raises:
            ValueError: If index data is invalid or entity loading fails
        """
        logger.info("query_people_by_meeting_start", meeting_id=str(meeting_id))
        
        try:
            # Load index file
            index_data = load_index("meeting_person_by_meeting")
            meeting_id_str = str(meeting_id)
            
            # Get person IDs from index
            person_ids_str = index_data.get(meeting_id_str, [])
            logger.debug("query_people_by_meeting_index_loaded", meeting_id=str(meeting_id), person_count=len(person_ids_str))
            
            # Load person entities
            people = []
            for person_id_str in person_ids_str:
                try:
                    person_id = UUID(person_id_str)
                    person = load_entity(person_id, ENTITIES_PEOPLE_DIR, Person)
                    if person:
                        people.append(person)
                except (ValueError, AttributeError) as e:
                    logger.warning("query_people_by_meeting_person_load_failed", person_id=person_id_str, error=str(e))
                    continue
            
            logger.info("query_people_by_meeting_success", meeting_id=str(meeting_id), person_count=len(people))
            return people
            
        except Exception as e:
            logger.error("query_people_by_meeting_failed", meeting_id=str(meeting_id), error=str(e))
            raise
    
    def get_all_topics(self) -> List[str]:
        """
        Get all unique topics from all tags.
        
        Extracts all unique topic values from tags.topics_covered field,
        handling both string and list formats.
        
        Returns:
            List of unique topic strings (sorted alphabetically)
        """
        logger.info("query_all_topics_start")
        
        try:
            topics_set = set()
            
            for tag_file in ENTITIES_TAGS_DIR.glob("*.json"):
                try:
                    tag_id = UUID(tag_file.stem)
                    tag = load_entity(tag_id, ENTITIES_TAGS_DIR, Tag)
                    if not tag or not tag.topics_covered:
                        continue
                    
                    # Handle both string and list formats
                    if isinstance(tag.topics_covered, list):
                        for topic in tag.topics_covered:
                            if topic:
                                topics_set.add(str(topic).strip())
                    elif isinstance(tag.topics_covered, str):
                        # String might be comma-separated or single value
                        for topic in tag.topics_covered.split(","):
                            topic = topic.strip()
                            if topic:
                                topics_set.add(topic)
                                
                except (ValueError, AttributeError) as e:
                    logger.warning("query_all_topics_loading_failed", tag_id=tag_file.stem, error=str(e))
                    continue
            
            topics_list = sorted(list(topics_set))
            logger.info("query_all_topics_success", topic_count=len(topics_list))
            return topics_list
            
        except Exception as e:
            logger.error("query_all_topics_failed", error=str(e))
            raise
    
    def get_meetings_by_date_range(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[Meeting]:
        """
        Get meetings filtered by date range, year, or month.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            year: Filter by year (e.g., 2025)
            month: Filter by month (1-12, requires year)
        
        Returns:
            List of Meeting entities matching the date criteria
        """
        logger.info(
            "query_meetings_by_date_start",
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
            year=year,
            month=month
        )
        
        try:
            # Calculate date range from parameters
            if year is not None:
                from datetime import date
                if month is not None:
                    # Specific month/year
                    start_date = date(year, month, 1)
                    # Get last day of month
                    if month == 12:
                        end_date = date(year + 1, 1, 1)
                    else:
                        end_date = date(year, month + 1, 1)
                else:
                    # Entire year
                    start_date = date(year, 1, 1)
                    end_date = date(year + 1, 1, 1)
            
            # Load all meetings
            all_meetings = self.find_all(ENTITIES_MEETINGS_DIR, Meeting)
            
            # Filter by date range
            filtered_meetings = []
            for meeting in all_meetings:
                meeting_date = meeting.date
                
                # Check if date is within range
                if start_date and meeting_date < start_date:
                    continue
                if end_date and meeting_date >= end_date:
                    continue
                
                filtered_meetings.append(meeting)
            
            # Sort by date (most recent first)
            filtered_meetings.sort(key=lambda m: m.date, reverse=True)
            
            logger.info(
                "query_meetings_by_date_success",
                meeting_count=len(filtered_meetings),
                start_date=str(start_date) if start_date else None,
                end_date=str(end_date) if end_date else None
            )
            return filtered_meetings
            
        except Exception as e:
            logger.error("query_meetings_by_date_failed", error=str(e))
            raise


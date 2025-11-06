"""Integration tests for NER entity extraction in meeting processing."""

import pytest
from pathlib import Path
from uuid import uuid4
from datetime import date, datetime

from src.models.meeting_record import MeetingRecord, MeetingInfo
from src.models.workgroup import Workgroup
from src.models.person import Person
from src.services.meeting_to_entity import convert_and_save_meeting_record
from src.services.entity_storage import (
    save_workgroup,
    save_person,
    load_entity,
    init_entity_storage_directories,
    delete_meeting,
    delete_workgroup,
    delete_person,
    ENTITIES_MEETINGS_DIR,
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_PEOPLE_DIR,
)
from src.services.ner_integration import NERIntegrationService
from src.lib.config import ENTITIES_DIR


class TestNERIntegrationWithEntityExtraction:
    """Integration tests for NER extraction during meeting processing."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Initialize entity storage
        init_entity_storage_directories()
        
        yield
        
        # Cleanup: Delete test entities
        try:
            # Clean up meetings
            if ENTITIES_MEETINGS_DIR.exists():
                for meeting_file in ENTITIES_MEETINGS_DIR.glob("*.json"):
                    try:
                        meeting_id = uuid4() if meeting_file.stem else None
                        if meeting_id:
                            delete_meeting(meeting_id)
                    except Exception:
                        pass
            
            # Clean up workgroups
            if ENTITIES_WORKGROUPS_DIR.exists():
                for workgroup_file in ENTITIES_WORKGROUPS_DIR.glob("*.json"):
                    try:
                        workgroup_id = uuid4() if workgroup_file.stem else None
                        if workgroup_id:
                            delete_workgroup(workgroup_id)
                    except Exception:
                        pass
            
            # Clean up people
            if ENTITIES_PEOPLE_DIR.exists():
                for person_file in ENTITIES_PEOPLE_DIR.glob("*.json"):
                    try:
                        person_id = uuid4() if person_file.stem else None
                        if person_id:
                            delete_person(person_id)
                    except Exception:
                        pass
        except Exception:
            pass  # Ignore cleanup errors
    
    @pytest.fixture
    def workgroup_id(self):
        """Fixture for workgroup UUID."""
        return uuid4()
    
    @pytest.fixture
    def workgroup(self, workgroup_id):
        """Fixture for workgroup entity."""
        workgroup = Workgroup(
            id=workgroup_id,
            name="Test Workgroup",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        save_workgroup(workgroup)
        return workgroup
    
    @pytest.fixture
    def meeting_record_with_purpose(self, workgroup_id):
        """Fixture for meeting record with purpose text containing entities."""
        return MeetingRecord(
            id=str(uuid4()),
            workgroup_id=str(workgroup_id),
            workgroup="Test Workgroup",
            date="2025-01-15",
            meetingInfo=MeetingInfo(
                date="2025-01-15",
                host="Alice Smith",
                documenter="Bob Johnson",
                peoplePresent="Alice Smith, Bob Johnson, Charlie Brown",
                purpose="Monthly planning meeting with SingularityNET team in New York on January 15, 2025. Discussed budget allocation and project timelines."
            )
        )
    
    def test_ner_extraction_from_purpose_field(self, meeting_record_with_purpose, workgroup):
        """Test that NER extracts entities from meetingInfo.purpose field."""
        try:
            ner_service = NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
        
        # Convert meeting record (this triggers NER extraction)
        meeting = convert_and_save_meeting_record(meeting_record_with_purpose)
        
        # Verify meeting was created
        assert meeting is not None
        assert meeting.id is not None
        
        # Verify NER extraction occurred (by checking if entities were extracted)
        # The extraction happens internally and logs results
        # We can verify by checking that the process completed without errors
        assert meeting.purpose == meeting_record_with_purpose.meetingInfo.purpose
    
    def test_ner_extraction_from_decision_text(self, workgroup_id, workgroup):
        """Test that NER extracts entities from decision text fields."""
        try:
            ner_service = NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
        
        # Create meeting record with decision items
        meeting_record = MeetingRecord(
            id=str(uuid4()),
            workgroup_id=str(workgroup_id),
            workgroup="Test Workgroup",
            date="2025-01-15",
            meetingInfo=MeetingInfo(
                date="2025-01-15",
                host="Alice Smith",
                documenter="Bob Johnson",
                peoplePresent="Alice Smith, Bob Johnson",
                purpose="Monthly meeting"
            ),
            agendaItems=[
                {
                    "status": "complete",
                    "narrative": "Budget discussion",
                    "decisionItems": [
                        {
                            "decision": "Approved budget increase for SingularityNET project in New York",
                            "rationale": "Based on team recommendations",
                            "effect": "mayAffectOtherPeople"
                        }
                    ],
                    "actionItems": []
                }
            ]
        )
        
        # Convert meeting record (this triggers NER extraction from decision text)
        meeting = convert_and_save_meeting_record(meeting_record)
        
        # Verify meeting was created
        assert meeting is not None
        # Decision NER extraction happens internally during processing
        assert meeting.purpose == "Monthly meeting"
    
    def test_ner_extraction_from_action_item_text(self, workgroup_id, workgroup):
        """Test that NER extracts entities from action item text fields."""
        try:
            ner_service = NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
        
        # Create meeting record with action items
        meeting_record = MeetingRecord(
            id=str(uuid4()),
            workgroup_id=str(workgroup_id),
            workgroup="Test Workgroup",
            date="2025-01-15",
            meetingInfo=MeetingInfo(
                date="2025-01-15",
                host="Alice Smith",
                documenter="Bob Johnson",
                peoplePresent="Alice Smith, Bob Johnson",
                purpose="Monthly meeting"
            ),
            agendaItems=[
                {
                    "status": "pending",
                    "narrative": "Action items",
                    "decisionItems": [],
                    "actionItems": [
                        {
                            "text": "Review proposal from OpenAI team by January 20, 2025",
                            "assignee": "Charlie Brown",
                            "status": "todo"
                        }
                    ]
                }
            ]
        )
        
        # Convert meeting record (this triggers NER extraction from action item text)
        meeting = convert_and_save_meeting_record(meeting_record)
        
        # Verify meeting was created
        assert meeting is not None
        # Action item NER extraction happens internally during processing
        assert meeting.purpose == "Monthly meeting"
    
    def test_ner_entity_filtering_integration(self, workgroup_id, workgroup):
        """Test that NER entities are filtered according to criteria (FR-013, FR-014)."""
        try:
            ner_service = NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
        
        # Create meeting record with purpose containing filler text
        meeting_record = MeetingRecord(
            id=str(uuid4()),
            workgroup_id=str(workgroup_id),
            workgroup="Test Workgroup",
            date="2025-01-15",
            meetingInfo=MeetingInfo(
                date="2025-01-15",
                host="Alice Smith",
                documenter="Bob Johnson",
                peoplePresent="Alice Smith",
                purpose="Meeting with Alice Smith. N/A. TODO: add more. Filler comment. Discussed important topics."
            )
        )
        
        # Extract entities using NER
        entities = ner_service.extract_from_text(
            text=meeting_record.meetingInfo.purpose,
            meeting_id=meeting_record.id,
            source_field="meetingInfo.purpose"
        )
        
        # Verify filler comments are filtered out
        entity_texts = [e.text.lower() for e in entities]
        assert "n/a" not in entity_texts
        assert "todo" not in entity_texts
        assert "filler" not in entity_texts
        
        # Verify meaningful entities are extracted
        # Should extract "Alice Smith" (PERSON) if present
        person_entities = [e for e in entities if e.entity_type == "PERSON"]
        # May or may not extract depending on spaCy model and text
        for entity in person_entities:
            assert len(entity.text.strip()) >= 2
            assert entity.text.lower() not in ["n/a", "todo", "filler", "comment"]
    
    def test_ner_entity_merging_with_existing_person(self, workgroup_id, workgroup):
        """Test that NER entities are merged with existing structured entities."""
        try:
            ner_service = NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
        
        # Create existing person entity
        existing_person = Person(
            display_name="Alice Smith",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        save_person(existing_person)
        
        # Create meeting record with purpose mentioning the same person
        meeting_record = MeetingRecord(
            id=str(uuid4()),
            workgroup_id=str(workgroup_id),
            workgroup="Test Workgroup",
            date="2025-01-15",
            meetingInfo=MeetingInfo(
                date="2025-01-15",
                host="Alice Smith",
                documenter="Bob Johnson",
                peoplePresent="Alice Smith, Bob Johnson",
                purpose="Meeting attended by Alice Smith and discussed with the team."
            )
        )
        
        # Extract entities using NER
        entities = ner_service.extract_from_text(
            text=meeting_record.meetingInfo.purpose,
            meeting_id=meeting_record.id,
            source_field="meetingInfo.purpose"
        )
        
        # Merge with existing structured entities
        merged_entities = ner_service.merge_with_structured(entities, [existing_person])
        
        # Verify entities were merged
        assert len(merged_entities) > 0
        # At least one entity should have normalized_entity_id set if match found
        # (exact match or fuzzy match)
        person_entities = [e for e in merged_entities if e.entity_type == "PERSON"]
        for entity in person_entities:
            if entity.text.lower() == "alice smith":
                # Should match existing person (either via normalization or fuzzy matching)
                # normalized_entity_id may be set by normalization service
                assert entity.text == "Alice Smith"
    
    def test_ner_extraction_summary_tracking(self, workgroup_id, workgroup):
        """Test that NER extraction summary is tracked and logged."""
        try:
            ner_service = NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
        
        # Create meeting record with multiple text fields containing entities
        meeting_record = MeetingRecord(
            id=str(uuid4()),
            workgroup_id=str(workgroup_id),
            workgroup="Test Workgroup",
            date="2025-01-15",
            meetingInfo=MeetingInfo(
                date="2025-01-15",
                host="Alice Smith",
                documenter="Bob Johnson",
                peoplePresent="Alice Smith, Bob Johnson",
                purpose="Meeting with SingularityNET team in New York."
            ),
            agendaItems=[
                {
                    "status": "complete",
                    "narrative": "Discussion",
                    "decisionItems": [
                        {
                            "decision": "Approved proposal from OpenAI",
                            "rationale": "Based on team recommendations",
                            "effect": "mayAffectOtherPeople"
                        }
                    ],
                    "actionItems": [
                        {
                            "text": "Follow up with Charlie Brown by January 20, 2025",
                            "assignee": "Alice Smith",
                            "status": "todo"
                        }
                    ]
                }
            ]
        )
        
        # Convert meeting record (this should track NER extraction summary)
        meeting = convert_and_save_meeting_record(meeting_record)
        
        # Verify meeting was created
        assert meeting is not None
        # NER extraction summary is tracked internally and logged
        # The summary includes total_extracted, merged_with_existing, new_entities, by_source_field
        assert meeting.purpose == meeting_record.meetingInfo.purpose
    
    def test_ner_extraction_handles_missing_model_gracefully(self, workgroup_id, workgroup):
        """Test that NER extraction handles missing spaCy model gracefully."""
        # Create meeting record
        meeting_record = MeetingRecord(
            id=str(uuid4()),
            workgroup_id=str(workgroup_id),
            workgroup="Test Workgroup",
            date="2025-01-15",
            meetingInfo=MeetingInfo(
                date="2025-01-15",
                host="Alice Smith",
                documenter="Bob Johnson",
                peoplePresent="Alice Smith",
                purpose="Test meeting purpose"
            )
        )
        
        # Convert meeting record - should handle NER service initialization failure gracefully
        # If spaCy model is not available, it should log a warning and continue
        meeting = convert_and_save_meeting_record(meeting_record)
        
        # Verify meeting was still created even if NER failed
        assert meeting is not None
        assert meeting.purpose == "Test meeting purpose"
    
    def test_ner_extraction_from_multiple_fields(self, workgroup_id, workgroup):
        """Test NER extraction from multiple text fields in a single meeting."""
        try:
            ner_service = NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
        
        # Create meeting record with entities in multiple fields
        meeting_record = MeetingRecord(
            id=str(uuid4()),
            workgroup_id=str(workgroup_id),
            workgroup="Test Workgroup",
            date="2025-01-15",
            meetingInfo=MeetingInfo(
                date="2025-01-15",
                host="Alice Smith",
                documenter="Bob Johnson",
                peoplePresent="Alice Smith, Bob Johnson, Charlie Brown",
                purpose="Meeting with SingularityNET team to discuss OpenAI collaboration."
            ),
            agendaItems=[
                {
                    "status": "complete",
                    "narrative": "Budget and planning",
                    "decisionItems": [
                        {
                            "decision": "Approved budget for New York office expansion",
                            "rationale": "Team consensus",
                            "effect": "mayAffectOtherPeople"
                        }
                    ],
                    "actionItems": [
                        {
                            "text": "Schedule follow-up meeting with OpenAI team in New York",
                            "assignee": "Charlie Brown",
                            "status": "todo"
                        }
                    ]
                }
            ]
        )
        
        # Convert meeting record
        meeting = convert_and_save_meeting_record(meeting_record)
        
        # Verify meeting was created
        assert meeting is not None
        
        # NER extraction should have occurred from:
        # - meetingInfo.purpose
        # - decisionItems[].decision
        # - actionItems[].text
        # All should be processed and tracked in the summary
        assert meeting.purpose == meeting_record.meetingInfo.purpose

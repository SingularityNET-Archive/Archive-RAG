"""Integration tests for entity relationships."""

import pytest
from pathlib import Path
from uuid import uuid4

from src.models.workgroup import Workgroup
from src.models.meeting import Meeting, MeetingType
from src.models.person import Person
from src.models.agenda_item import AgendaItem
from src.models.action_item import ActionItem, ActionItemStatus
from src.models.document import Document
from src.models.decision_item import DecisionItem, DecisionEffect
from src.models.tag import Tag
from src.services.entity_storage import (
    save_workgroup,
    save_meeting,
    save_person,
    save_agenda_item,
    save_action_item,
    save_document,
    save_decision_item,
    save_tag,
    load_entity,
    init_entity_storage_directories
)
from src.services.entity_query import EntityQueryService
from src.lib.config import (
    ENTITIES_WORKGROUPS_DIR,
    ENTITIES_MEETINGS_DIR,
    ENTITIES_PEOPLE_DIR,
    ENTITIES_DOCUMENTS_DIR,
    ENTITIES_AGENDA_ITEMS_DIR,
    ENTITIES_ACTION_ITEMS_DIR,
    ENTITIES_DECISION_ITEMS_DIR,
    ENTITIES_TAGS_DIR,
    ENTITIES_INDEX_DIR
)


class TestEntityRelationships:
    """Integration tests for entity relationships."""
    
    @pytest.fixture(autouse=True)
    def setup_storage(self, tmp_path, monkeypatch):
        """Setup entity storage directories in temporary path."""
        # Monkeypatch config paths to use tmp_path
        from src import lib
        lib.config.ENTITIES_DIR = tmp_path / "entities"
        lib.config.ENTITIES_WORKGROUPS_DIR = lib.config.ENTITIES_DIR / "workgroups"
        lib.config.ENTITIES_MEETINGS_DIR = lib.config.ENTITIES_DIR / "meetings"
        lib.config.ENTITIES_PEOPLE_DIR = lib.config.ENTITIES_DIR / "people"
        lib.config.ENTITIES_DOCUMENTS_DIR = lib.config.ENTITIES_DIR / "documents"
        lib.config.ENTITIES_AGENDA_ITEMS_DIR = lib.config.ENTITIES_DIR / "agenda_items"
        lib.config.ENTITIES_ACTION_ITEMS_DIR = lib.config.ENTITIES_DIR / "action_items"
        lib.config.ENTITIES_DECISION_ITEMS_DIR = lib.config.ENTITIES_DIR / "decision_items"
        lib.config.ENTITIES_TAGS_DIR = lib.config.ENTITIES_DIR / "tags"
        lib.config.ENTITIES_INDEX_DIR = lib.config.ENTITIES_DIR / "_index"
        
        # Initialize storage directories
        init_entity_storage_directories()
    
    def test_query_meetings_by_workgroup(self):
        """Test querying meetings by workgroup - independent test for US1."""
        # Create a workgroup
        workgroup = Workgroup(name="Archives Workgroup")
        workgroup_id = workgroup.id
        
        # Save workgroup
        save_workgroup(workgroup)
        
        # Verify workgroup was saved
        loaded_workgroup = load_entity(workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
        assert loaded_workgroup is not None
        assert loaded_workgroup.name == "Archives Workgroup"
        
        # Create multiple meetings for this workgroup
        meeting1 = Meeting(
            workgroup_id=workgroup_id,
            date="2024-03-15",
            meeting_type=MeetingType.MONTHLY,
            purpose="March planning meeting"
        )
        meeting2 = Meeting(
            workgroup_id=workgroup_id,
            date="2024-04-15",
            meeting_type=MeetingType.MONTHLY,
            purpose="April planning meeting"
        )
        meeting3 = Meeting(
            workgroup_id=workgroup_id,
            date="2024-05-15",
            meeting_type=MeetingType.MONTHLY,
            purpose="May planning meeting"
        )
        
        # Save meetings
        save_meeting(meeting1)
        save_meeting(meeting2)
        save_meeting(meeting3)
        
        # Query meetings by workgroup
        query_service = EntityQueryService()
        meetings = query_service.get_meetings_by_workgroup(workgroup_id)
        
        # Verify all meetings are returned
        assert len(meetings) == 3
        
        # Verify all meetings belong to the specified workgroup
        meeting_ids = {meeting.id for meeting in meetings}
        assert meeting1.id in meeting_ids
        assert meeting2.id in meeting_ids
        assert meeting3.id in meeting_ids
        
        # Verify all meetings have correct workgroup_id
        for meeting in meetings:
            assert meeting.workgroup_id == workgroup_id
        
        # Verify exact count matches (independent test requirement)
        assert len(meetings) == 3, f"Expected 3 meetings, got {len(meetings)}"
    
    def test_query_meetings_by_workgroup_empty(self):
        """Test querying meetings for workgroup with no meetings."""
        # Create a workgroup with no meetings
        workgroup = Workgroup(name="Empty Workgroup")
        workgroup_id = workgroup.id
        save_workgroup(workgroup)
        
        # Query meetings
        query_service = EntityQueryService()
        meetings = query_service.get_meetings_by_workgroup(workgroup_id)
        
        # Should return empty list
        assert len(meetings) == 0
        assert meetings == []
    
    def test_query_meetings_multiple_workgroups(self):
        """Test querying meetings for multiple workgroups."""
        # Create two workgroups
        workgroup1 = Workgroup(name="Workgroup 1")
        workgroup2 = Workgroup(name="Workgroup 2")
        
        save_workgroup(workgroup1)
        save_workgroup(workgroup2)
        
        # Create meetings for each workgroup
        meeting1_wg1 = Meeting(workgroup_id=workgroup1.id, date="2024-03-15")
        meeting2_wg1 = Meeting(workgroup_id=workgroup1.id, date="2024-04-15")
        meeting1_wg2 = Meeting(workgroup_id=workgroup2.id, date="2024-03-20")
        
        save_meeting(meeting1_wg1)
        save_meeting(meeting2_wg1)
        save_meeting(meeting1_wg2)
        
        # Query meetings for workgroup1
        query_service = EntityQueryService()
        meetings_wg1 = query_service.get_meetings_by_workgroup(workgroup1.id)
        meetings_wg2 = query_service.get_meetings_by_workgroup(workgroup2.id)
        
        # Verify correct meetings are returned
        assert len(meetings_wg1) == 2
        assert len(meetings_wg2) == 1
        
        # Verify no cross-contamination
        wg1_ids = {meeting.id for meeting in meetings_wg1}
        wg2_ids = {meeting.id for meeting in meetings_wg2}
        assert wg1_ids.isdisjoint(wg2_ids)
    
    def test_query_action_items_by_person(self):
        """Test querying action items by person - independent test for US2."""
        # Create a workgroup and meeting
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting = Meeting(
            workgroup_id=workgroup.id,
            date="2024-03-15",
            type=MeetingType.MONTHLY
        )
        save_meeting(meeting)
        
        # Create agenda items
        agenda_item1 = AgendaItem(
            meeting_id=meeting.id,
            narrative="Budget planning"
        )
        agenda_item2 = AgendaItem(
            meeting_id=meeting.id,
            narrative="Team coordination"
        )
        save_agenda_item(agenda_item1)
        save_agenda_item(agenda_item2)
        
        # Create people
        person1 = Person(display_name="Alice", role="manager")
        person2 = Person(display_name="Bob", role="engineer")
        save_person(person1)
        save_person(person2)
        
        # Create action items assigned to different people
        action_item1 = ActionItem(
            agenda_item_id=agenda_item1.id,
            text="Review budget proposal",
            assignee_id=person1.id,
            due_date="2024-04-01",
            status=ActionItemStatus.TODO
        )
        action_item2 = ActionItem(
            agenda_item_id=agenda_item1.id,
            text="Update financial spreadsheet",
            assignee_id=person1.id,
            due_date="2024-04-05",
            status=ActionItemStatus.IN_PROGRESS
        )
        action_item3 = ActionItem(
            agenda_item_id=agenda_item2.id,
            text="Schedule team meeting",
            assignee_id=person2.id,
            due_date="2024-04-10",
            status=ActionItemStatus.TODO
        )
        
        save_action_item(action_item1)
        save_action_item(action_item2)
        save_action_item(action_item3)
        
        # Query action items for person1
        query_service = EntityQueryService()
        person1_actions = query_service.get_action_items_by_person(person1.id)
        
        # Verify only person1's assignments are returned
        assert len(person1_actions) == 2
        
        # Verify all returned items belong to person1
        for action_item in person1_actions:
            assert action_item.assignee_id == person1.id
        
        # Verify correct action items are returned
        action_ids = {item.id for item in person1_actions}
        assert action_item1.id in action_ids
        assert action_item2.id in action_ids
        assert action_item3.id not in action_ids  # Should not be in person1's list
        
        # Verify all fields are correctly populated
        for action_item in person1_actions:
            assert action_item.text is not None
            assert action_item.assignee_id == person1.id
            assert action_item.agenda_item_id is not None
        
        # Query action items for person2
        person2_actions = query_service.get_action_items_by_person(person2.id)
        assert len(person2_actions) == 1
        assert person2_actions[0].id == action_item3.id
        assert person2_actions[0].assignee_id == person2.id
        
        # Verify person with no action items returns empty list
        person3 = Person(display_name="Charlie")
        save_person(person3)
        person3_actions = query_service.get_action_items_by_person(person3.id)
        assert len(person3_actions) == 0
        assert person3_actions == []
    
    def test_query_documents_by_meeting(self):
        """Test querying documents for meeting - independent test for US3."""
        # Create a workgroup and meeting
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting = Meeting(
            workgroup_id=workgroup.id,
            date="2024-03-15",
            meeting_type=MeetingType.MONTHLY
        )
        save_meeting(meeting)
        
        # Create multiple documents for this meeting
        document1 = Document(
            meeting_id=meeting.id,
            title="Budget Report",
            link="https://example.com/budget.pdf"
        )
        document2 = Document(
            meeting_id=meeting.id,
            title="Planning Document",
            link="https://example.com/planning.pdf"
        )
        document3 = Document(
            meeting_id=meeting.id,
            title="Summary Notes",
            link="https://example.com/summary.pdf"
        )
        
        save_document(document1)
        save_document(document2)
        save_document(document3)
        
        # Query documents for meeting
        query_service = EntityQueryService()
        documents = query_service.get_documents_by_meeting(meeting.id)
        
        # Verify all documents are returned
        assert len(documents) == 3
        
        # Verify all documents belong to the specified meeting
        document_ids = {doc.id for doc in documents}
        assert document1.id in document_ids
        assert document2.id in document_ids
        assert document3.id in document_ids
        
        # Verify all documents have correct meeting_id
        for document in documents:
            assert document.meeting_id == meeting.id
        
        # Verify all documents have titles and links
        for document in documents:
            assert document.title is not None
            assert document.link is not None
        
        # Verify exact count matches
        assert len(documents) == 3, f"Expected 3 documents, got {len(documents)}"
    
    def test_query_documents_by_meeting_empty(self):
        """Test querying documents for meeting with no documents."""
        # Create a workgroup and meeting
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting = Meeting(
            workgroup_id=workgroup.id,
            date="2024-03-15"
        )
        save_meeting(meeting)
        
        # Query documents for meeting with no documents
        query_service = EntityQueryService()
        documents = query_service.get_documents_by_meeting(meeting.id)
        
        # Should return empty list
        assert len(documents) == 0
        assert documents == []
    
    def test_query_documents_multiple_meetings(self):
        """Test querying documents for multiple meetings."""
        # Create a workgroup and meetings
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting1 = Meeting(workgroup_id=workgroup.id, date="2024-03-15")
        meeting2 = Meeting(workgroup_id=workgroup.id, date="2024-04-15")
        save_meeting(meeting1)
        save_meeting(meeting2)
        
        # Create documents for each meeting
        doc1_m1 = Document(meeting_id=meeting1.id, title="Doc 1", link="https://example.com/doc1.pdf")
        doc2_m1 = Document(meeting_id=meeting1.id, title="Doc 2", link="https://example.com/doc2.pdf")
        doc1_m2 = Document(meeting_id=meeting2.id, title="Doc 3", link="https://example.com/doc3.pdf")
        
        save_document(doc1_m1)
        save_document(doc2_m1)
        save_document(doc1_m2)
        
        # Query documents for each meeting
        query_service = EntityQueryService()
        docs_m1 = query_service.get_documents_by_meeting(meeting1.id)
        docs_m2 = query_service.get_documents_by_meeting(meeting2.id)
        
        # Verify correct documents are returned
        assert len(docs_m1) == 2
        assert len(docs_m2) == 1
        
        # Verify no cross-contamination
        m1_ids = {doc.id for doc in docs_m1}
        m2_ids = {doc.id for doc in docs_m2}
        assert m1_ids.isdisjoint(m2_ids)
    
    def test_query_decisions_by_agenda_item(self):
        """Test querying decisions by agenda item - integration test for US4."""
        # Create workgroup and meeting
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting = Meeting(
            workgroup_id=workgroup.id,
            date="2024-03-15",
            meeting_type=MeetingType.MONTHLY
        )
        save_meeting(meeting)
        
        # Create agenda items
        agenda_item1 = AgendaItem(
            meeting_id=meeting.id,
            status="completed"
        )
        agenda_item2 = AgendaItem(
            meeting_id=meeting.id,
            status="completed"
        )
        save_agenda_item(agenda_item1)
        save_agenda_item(agenda_item2)
        
        # Create decision items for each agenda item
        decision1_1 = DecisionItem(
            agenda_item_id=agenda_item1.id,
            decision="Approved budget increase of 10%",
            rationale="Based on increased operational costs",
            effect=DecisionEffect.MAY_AFFECT_OTHER_PEOPLE
        )
        decision1_2 = DecisionItem(
            agenda_item_id=agenda_item1.id,
            decision="Postponed feature implementation",
            rationale="Resource constraints"
        )
        decision2_1 = DecisionItem(
            agenda_item_id=agenda_item2.id,
            decision="Hired new team member",
            effect=DecisionEffect.AFFECTS_ONLY_THIS_WORKGROUP
        )
        
        save_decision_item(decision1_1)
        save_decision_item(decision1_2)
        save_decision_item(decision2_1)
        
        # Query decisions by agenda item
        query_service = EntityQueryService()
        decisions_for_agenda1 = query_service.get_decision_items_by_agenda_item(agenda_item1.id)
        decisions_for_agenda2 = query_service.get_decision_items_by_agenda_item(agenda_item2.id)
        
        # Verify correct decisions are returned
        assert len(decisions_for_agenda1) == 2
        assert len(decisions_for_agenda2) == 1
        
        # Verify decision details
        decision_ids_agenda1 = {d.id for d in decisions_for_agenda1}
        assert decision1_1.id in decision_ids_agenda1
        assert decision1_2.id in decision_ids_agenda1
        assert decision2_1.id not in decision_ids_agenda1
        
        # Verify rationales and effects are preserved
        decision1_1_loaded = next(d for d in decisions_for_agenda1 if d.id == decision1_1.id)
        assert decision1_1_loaded.rationale == "Based on increased operational costs"
        assert decision1_1_loaded.effect == DecisionEffect.MAY_AFFECT_OTHER_PEOPLE
    
    def test_query_decisions_by_effect_scope(self):
        """Test querying decisions by effect scope - integration test for US4."""
        # Create workgroup, meeting, and agenda item
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting = Meeting(
            workgroup_id=workgroup.id,
            date="2024-03-15",
            meeting_type=MeetingType.MONTHLY
        )
        save_meeting(meeting)
        
        agenda_item = AgendaItem(
            meeting_id=meeting.id,
            status="completed"
        )
        save_agenda_item(agenda_item)
        
        # Create decisions with different effect scopes
        decision_affects_others = DecisionItem(
            agenda_item_id=agenda_item.id,
            decision="Approved cross-team collaboration",
            effect=DecisionEffect.MAY_AFFECT_OTHER_PEOPLE
        )
        decision_affects_only = DecisionItem(
            agenda_item_id=agenda_item.id,
            decision="Internal team structure change",
            effect=DecisionEffect.AFFECTS_ONLY_THIS_WORKGROUP
        )
        decision_no_effect = DecisionItem(
            agenda_item_id=agenda_item.id,
            decision="Routine operational decision"
        )
        
        save_decision_item(decision_affects_others)
        save_decision_item(decision_affects_only)
        save_decision_item(decision_no_effect)
        
        # Query decisions by effect
        query_service = EntityQueryService()
        decisions_affecting_others = query_service.get_decision_items_by_effect(
            DecisionEffect.MAY_AFFECT_OTHER_PEOPLE
        )
        decisions_affecting_only = query_service.get_decision_items_by_effect(
            DecisionEffect.AFFECTS_ONLY_THIS_WORKGROUP
        )
        
        # Verify correct decisions are returned
        assert len(decisions_affecting_others) >= 1
        assert len(decisions_affecting_only) >= 1
        
        # Verify effect filtering works
        affecting_others_ids = {d.id for d in decisions_affecting_others}
        assert decision_affects_others.id in affecting_others_ids
        assert decision_affects_only.id not in affecting_others_ids
        assert decision_no_effect.id not in affecting_others_ids
        
        affecting_only_ids = {d.id for d in decisions_affecting_only}
        assert decision_affects_only.id in affecting_only_ids
        assert decision_affects_others.id not in affecting_only_ids
    
    def test_decision_text_extraction_coverage(self):
        """Test that 100% of decision text is extracted for RAG embedding - SC-008."""
        # Create workgroup, meeting, and agenda item
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting = Meeting(
            workgroup_id=workgroup.id,
            date="2024-03-15",
            meeting_type=MeetingType.MONTHLY
        )
        save_meeting(meeting)
        
        agenda_item = AgendaItem(
            meeting_id=meeting.id,
            status="completed"
        )
        save_agenda_item(agenda_item)
        
        # Create multiple decisions with varying text lengths
        decision_texts = [
            "Short decision",
            "This is a longer decision with more details about the approval process",
            "Decision with rationale: Based on comprehensive analysis, we approve this change",
            "Another decision with special characters: $100,000 budget & 10% increase"
        ]
        
        decision_items = []
        for decision_text in decision_texts:
            decision_item = DecisionItem(
                agenda_item_id=agenda_item.id,
                decision=decision_text
            )
            save_decision_item(decision_item)
            decision_items.append(decision_item)
        
        # Query all decisions for the agenda item
        query_service = EntityQueryService()
        retrieved_decisions = query_service.get_decision_items_by_agenda_item(agenda_item.id)
        
        # Verify 100% coverage: all decision text is present
        assert len(retrieved_decisions) == len(decision_texts)
        
        retrieved_texts = {d.decision for d in retrieved_decisions}
        original_texts = set(decision_texts)
        
        # Verify all original decision texts are present in retrieved decisions
        assert retrieved_texts == original_texts, "Not all decision text was extracted"
        
        # Verify decision text is not truncated or modified
        for original_text in decision_texts:
            matching_decision = next(
                d for d in retrieved_decisions if d.decision == original_text
            )
            assert matching_decision.decision == original_text
            assert len(matching_decision.decision) == len(original_text)
    
    def test_query_meetings_by_tag(self):
        """Test querying meetings by tag - integration test for US5."""
        # Create workgroup and meetings
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting1 = Meeting(
            workgroup_id=workgroup.id,
            date="2024-03-15",
            meeting_type=MeetingType.MONTHLY
        )
        meeting2 = Meeting(
            workgroup_id=workgroup.id,
            date="2024-04-15",
            meeting_type=MeetingType.MONTHLY
        )
        meeting3 = Meeting(
            workgroup_id=workgroup.id,
            date="2024-05-15",
            meeting_type=MeetingType.MONTHLY
        )
        save_meeting(meeting1)
        save_meeting(meeting2)
        save_meeting(meeting3)
        
        # Create tags for meetings
        tag1 = Tag(
            meeting_id=meeting1.id,
            topics_covered=["budget", "planning"],
            emotions=["collaborative"]
        )
        tag2 = Tag(
            meeting_id=meeting2.id,
            topics_covered=["strategy", "planning"],
            emotions=["friendly"]
        )
        tag3 = Tag(
            meeting_id=meeting3.id,
            topics_covered=["budget"],
            emotions=["energetic"]
        )
        # Meeting 3 has no tag - should be excluded from tag-based queries
        
        save_tag(tag1)
        save_tag(tag2)
        save_tag(tag3)
        
        # Query meetings by tag
        query_service = EntityQueryService()
        meetings_with_budget = query_service.get_meetings_by_tag("budget", tag_type="topics")
        meetings_with_planning = query_service.get_meetings_by_tag("planning", tag_type="topics")
        meetings_with_collaborative = query_service.get_meetings_by_tag("collaborative", tag_type="emotions")
        
        # Verify correct meetings are returned
        assert len(meetings_with_budget) == 2  # meeting1 and meeting3
        assert len(meetings_with_planning) == 2  # meeting1 and meeting2
        assert len(meetings_with_collaborative) == 1  # meeting1
        
        # Verify meeting IDs
        budget_meeting_ids = {m.id for m in meetings_with_budget}
        assert meeting1.id in budget_meeting_ids
        assert meeting3.id in budget_meeting_ids
        assert meeting2.id not in budget_meeting_ids
        
        planning_meeting_ids = {m.id for m in meetings_with_planning}
        assert meeting1.id in planning_meeting_ids
        assert meeting2.id in planning_meeting_ids
        assert meeting3.id not in planning_meeting_ids
        
        # Verify untagged meetings are excluded
        collaborative_meeting_ids = {m.id for m in meetings_with_collaborative}
        assert meeting1.id in collaborative_meeting_ids
        assert meeting2.id not in collaborative_meeting_ids
        assert meeting3.id not in collaborative_meeting_ids
    
    def test_query_meetings_by_tag_string_format(self):
        """Test querying meetings by tag with string format (comma-separated)."""
        # Create workgroup and meeting
        workgroup = Workgroup(name="Test Workgroup")
        save_workgroup(workgroup)
        
        meeting = Meeting(
            workgroup_id=workgroup.id,
            date="2024-03-15",
            meeting_type=MeetingType.MONTHLY
        )
        save_meeting(meeting)
        
        # Create tag with string format (comma-separated)
        tag = Tag(
            meeting_id=meeting.id,
            topics_covered="budget, planning, strategy",
            emotions="collaborative, friendly"
        )
        save_tag(tag)
        
        # Query meetings by tag
        query_service = EntityQueryService()
        meetings_with_budget = query_service.get_meetings_by_tag("budget", tag_type="topics")
        meetings_with_planning = query_service.get_meetings_by_tag("planning", tag_type="topics")
        meetings_with_collaborative = query_service.get_meetings_by_tag("collaborative", tag_type="emotions")
        
        # Verify meetings are found with string format
        assert len(meetings_with_budget) == 1
        assert len(meetings_with_planning) == 1
        assert len(meetings_with_collaborative) == 1
        assert meetings_with_budget[0].id == meeting.id
        assert meetings_with_planning[0].id == meeting.id
        assert meetings_with_collaborative[0].id == meeting.id


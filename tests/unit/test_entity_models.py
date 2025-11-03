"""Unit tests for entity model validation."""

import pytest
from datetime import date
from uuid import UUID, uuid4
from pydantic import ValidationError

from src.models.workgroup import Workgroup
from src.models.meeting import Meeting, MeetingType
from src.models.person import Person
from src.models.agenda_item import AgendaItem, AgendaItemStatus
from src.models.action_item import ActionItem, ActionItemStatus
from src.models.document import Document
from src.models.decision_item import DecisionItem, DecisionEffect


class TestWorkgroupModel:
    """Unit tests for Workgroup model validation."""
    
    def test_workgroup_creation_valid(self):
        """Test creating a valid workgroup."""
        workgroup = Workgroup(name="Archives Workgroup")
        assert workgroup.name == "Archives Workgroup"
        assert isinstance(workgroup.id, UUID)
        assert workgroup.created_at is not None
        assert workgroup.updated_at is not None
    
    def test_workgroup_name_required(self):
        """Test workgroup name is required."""
        with pytest.raises(ValidationError) as exc_info:
            Workgroup()
        assert "name" in str(exc_info.value)
    
    def test_workgroup_name_not_empty(self):
        """Test workgroup name cannot be empty."""
        with pytest.raises(ValidationError):
            Workgroup(name="")
        
        with pytest.raises(ValidationError):
            Workgroup(name="   ")
    
    def test_workgroup_name_trimmed(self):
        """Test workgroup name is trimmed."""
        workgroup = Workgroup(name="  Archives Workgroup  ")
        assert workgroup.name == "Archives Workgroup"
    
    def test_workgroup_with_custom_id(self):
        """Test creating workgroup with custom UUID."""
        custom_id = uuid4()
        workgroup = Workgroup(id=custom_id, name="Test Workgroup")
        assert workgroup.id == custom_id


class TestMeetingModel:
    """Unit tests for Meeting model validation."""
    
    @pytest.fixture
    def workgroup_id(self):
        """Fixture for workgroup UUID."""
        return uuid4()
    
    def test_meeting_creation_valid(self, workgroup_id):
        """Test creating a valid meeting."""
        meeting = Meeting(
            workgroup_id=workgroup_id,
            date="2024-03-15"
        )
        assert meeting.workgroup_id == workgroup_id
        assert meeting.date == date(2024, 3, 15)
        assert isinstance(meeting.id, UUID)
        assert meeting.created_at is not None
        assert meeting.updated_at is not None
    
    def test_meeting_workgroup_id_required(self):
        """Test workgroup_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            Meeting(date="2024-03-15")
        assert "workgroup_id" in str(exc_info.value)
    
    def test_meeting_date_required(self):
        """Test date is required."""
        workgroup_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            Meeting(workgroup_id=workgroup_id)
        assert "date" in str(exc_info.value)
    
    def test_meeting_date_formats(self, workgroup_id):
        """Test meeting date accepts various formats."""
        # ISO 8601 date format
        meeting1 = Meeting(workgroup_id=workgroup_id, date="2024-03-15")
        assert meeting1.date == date(2024, 3, 15)
        
        # Date object
        meeting2 = Meeting(workgroup_id=workgroup_id, date=date(2024, 3, 15))
        assert meeting2.date == date(2024, 3, 15)
    
    def test_meeting_type_enum(self, workgroup_id):
        """Test meeting type enum values."""
        meeting = Meeting(
            workgroup_id=workgroup_id,
            date="2024-03-15",
            meeting_type=MeetingType.MONTHLY
        )
        assert meeting.meeting_type == MeetingType.MONTHLY
        
        meeting2 = Meeting(
            workgroup_id=workgroup_id,
            date="2024-03-15",
            meeting_type="Weekly"  # String enum value
        )
        assert meeting2.meeting_type == MeetingType.WEEKLY
    
    def test_meeting_optional_fields(self, workgroup_id):
        """Test meeting optional fields."""
        host_id = uuid4()
        documenter_id = uuid4()
        meeting = Meeting(
            workgroup_id=workgroup_id,
            date="2024-03-15",
            host_id=host_id,
            documenter_id=documenter_id,
            purpose="Monthly planning meeting",
            no_summary_given=True,
            canceled_summary=False
        )
        assert meeting.host_id == host_id
        assert meeting.documenter_id == documenter_id
        assert meeting.purpose == "Monthly planning meeting"
        assert meeting.no_summary_given is True
        assert meeting.canceled_summary is False
    
    def test_meeting_default_values(self, workgroup_id):
        """Test meeting default values."""
        meeting = Meeting(
            workgroup_id=workgroup_id,
            date="2024-03-15"
        )
        assert meeting.no_summary_given is False
        assert meeting.canceled_summary is False
        assert meeting.meeting_type is None
        assert meeting.purpose is None


class TestPersonModel:
    """Unit tests for Person model validation."""
    
    def test_person_creation_valid(self):
        """Test creating a valid person."""
        person = Person(display_name="Alice Smith")
        assert person.display_name == "Alice Smith"
        assert isinstance(person.id, UUID)
        assert person.created_at is not None
        assert person.updated_at is not None
    
    def test_person_display_name_required(self):
        """Test display_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            Person()
        assert "display_name" in str(exc_info.value)
    
    def test_person_display_name_not_empty(self):
        """Test display_name cannot be empty."""
        with pytest.raises(ValidationError):
            Person(display_name="")
        
        with pytest.raises(ValidationError):
            Person(display_name="   ")
    
    def test_person_optional_fields(self):
        """Test person optional fields."""
        person = Person(
            display_name="Bob Johnson",
            alias="bob",
            role="host"
        )
        assert person.alias == "bob"
        assert person.role == "host"
    
    def test_person_with_custom_id(self):
        """Test creating person with custom UUID."""
        custom_id = uuid4()
        person = Person(id=custom_id, display_name="Charlie Brown")
        assert person.id == custom_id


class TestAgendaItemModel:
    """Unit tests for AgendaItem model validation."""
    
    @pytest.fixture
    def meeting_id(self):
        """Fixture for meeting UUID."""
        return uuid4()
    
    def test_agenda_item_creation_valid(self, meeting_id):
        """Test creating a valid agenda item."""
        agenda_item = AgendaItem(
            meeting_id=meeting_id,
            narrative="Budget discussion"
        )
        assert agenda_item.meeting_id == meeting_id
        assert agenda_item.narrative == "Budget discussion"
        assert isinstance(agenda_item.id, UUID)
        assert agenda_item.created_at is not None
    
    def test_agenda_item_meeting_id_required(self):
        """Test meeting_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            AgendaItem(narrative="Test narrative")
        assert "meeting_id" in str(exc_info.value)
    
    def test_agenda_item_status_enum(self, meeting_id):
        """Test agenda item status enum values."""
        agenda_item = AgendaItem(
            meeting_id=meeting_id,
            status=AgendaItemStatus.COMPLETE
        )
        assert agenda_item.status == AgendaItemStatus.COMPLETE
        
        agenda_item2 = AgendaItem(
            meeting_id=meeting_id,
            status="carry over"  # String enum value
        )
        assert agenda_item2.status == AgendaItemStatus.CARRY_OVER
    
    def test_agenda_item_optional_fields(self, meeting_id):
        """Test agenda item optional fields."""
        agenda_item = AgendaItem(
            meeting_id=meeting_id,
            status=AgendaItemStatus.PENDING,
            narrative="Review quarterly reports"
        )
        assert agenda_item.status == AgendaItemStatus.PENDING
        assert agenda_item.narrative == "Review quarterly reports"
    
    def test_agenda_item_without_action_items(self, meeting_id):
        """Test agenda item can exist without action items (FR-005)."""
        agenda_item = AgendaItem(meeting_id=meeting_id)
        assert agenda_item.meeting_id == meeting_id
        assert agenda_item.status is None
        assert agenda_item.narrative is None


class TestActionItemModel:
    """Unit tests for ActionItem model validation."""
    
    @pytest.fixture
    def agenda_item_id(self):
        """Fixture for agenda item UUID."""
        return uuid4()
    
    @pytest.fixture
    def person_id(self):
        """Fixture for person UUID."""
        return uuid4()
    
    def test_action_item_creation_valid(self, agenda_item_id):
        """Test creating a valid action item."""
        action_item = ActionItem(
            agenda_item_id=agenda_item_id,
            text="Review budget proposal"
        )
        assert action_item.agenda_item_id == agenda_item_id
        assert action_item.text == "Review budget proposal"
        assert isinstance(action_item.id, UUID)
        assert action_item.created_at is not None
        assert action_item.updated_at is not None
    
    def test_action_item_agenda_item_id_required(self):
        """Test agenda_item_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(text="Test action item")
        assert "agenda_item_id" in str(exc_info.value)
    
    def test_action_item_text_required(self, agenda_item_id):
        """Test text is required."""
        with pytest.raises(ValidationError) as exc_info:
            ActionItem(agenda_item_id=agenda_item_id)
        assert "text" in str(exc_info.value)
    
    def test_action_item_text_not_empty(self, agenda_item_id):
        """Test text cannot be empty."""
        with pytest.raises(ValidationError):
            ActionItem(agenda_item_id=agenda_item_id, text="")
        
        with pytest.raises(ValidationError):
            ActionItem(agenda_item_id=agenda_item_id, text="   ")
    
    def test_action_item_status_enum(self, agenda_item_id):
        """Test action item status enum values."""
        action_item = ActionItem(
            agenda_item_id=agenda_item_id,
            text="Complete task",
            status=ActionItemStatus.DONE
        )
        assert action_item.status == ActionItemStatus.DONE
        
        action_item2 = ActionItem(
            agenda_item_id=agenda_item_id,
            text="In progress task",
            status="in progress"  # String enum value
        )
        assert action_item2.status == ActionItemStatus.IN_PROGRESS
    
    def test_action_item_with_assignee(self, agenda_item_id, person_id):
        """Test action item with assignee."""
        action_item = ActionItem(
            agenda_item_id=agenda_item_id,
            text="Review document",
            assignee_id=person_id,
            due_date="2024-04-01",
            status=ActionItemStatus.TODO
        )
        assert action_item.assignee_id == person_id
        assert action_item.due_date == date(2024, 4, 1)
        assert action_item.status == ActionItemStatus.TODO
    
    def test_action_item_optional_assignee(self, agenda_item_id):
        """Test action item without assignee (assignee is optional)."""
        action_item = ActionItem(
            agenda_item_id=agenda_item_id,
            text="General task"
        )
        assert action_item.assignee_id is None
        assert action_item.due_date is None
        assert action_item.status is None


class TestDocumentModel:
    """Unit tests for Document model validation."""
    
    @pytest.fixture
    def meeting_id(self):
        """Fixture for meeting UUID."""
        return uuid4()
    
    def test_document_creation_valid(self, meeting_id):
        """Test creating a valid document."""
        document = Document(
            meeting_id=meeting_id,
            title="Budget Report",
            link="https://example.com/budget.pdf"
        )
        assert document.meeting_id == meeting_id
        assert document.title == "Budget Report"
        assert document.link == "https://example.com/budget.pdf"
        assert isinstance(document.id, UUID)
        assert document.created_at is not None
    
    def test_document_meeting_id_required(self):
        """Test meeting_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            Document(title="Test Document", link="https://example.com/doc.pdf")
        assert "meeting_id" in str(exc_info.value)
    
    def test_document_title_required(self, meeting_id):
        """Test title is required."""
        with pytest.raises(ValidationError) as exc_info:
            Document(meeting_id=meeting_id, link="https://example.com/doc.pdf")
        assert "title" in str(exc_info.value)
    
    def test_document_link_required(self, meeting_id):
        """Test link is required."""
        with pytest.raises(ValidationError) as exc_info:
            Document(meeting_id=meeting_id, title="Test Document")
        assert "link" in str(exc_info.value)
    
    def test_document_title_not_empty(self, meeting_id):
        """Test title cannot be empty."""
        with pytest.raises(ValidationError):
            Document(
                meeting_id=meeting_id,
                title="",
                link="https://example.com/doc.pdf"
            )
        
        with pytest.raises(ValidationError):
            Document(
                meeting_id=meeting_id,
                title="   ",
                link="https://example.com/doc.pdf"
            )
    
    def test_document_link_url_format(self, meeting_id):
        """Test link must be valid URL format."""
        # Valid URL
        document = Document(
            meeting_id=meeting_id,
            title="Valid Document",
            link="https://example.com/document.pdf"
        )
        assert str(document.link) == "https://example.com/document.pdf"
        
        # HTTP URL also valid
        document2 = Document(
            meeting_id=meeting_id,
            title="HTTP Document",
            link="http://example.com/doc.pdf"
        )
        assert str(document2.link) == "http://example.com/doc.pdf"
    
    def test_document_link_validates_on_access(self, meeting_id):
        """Test that invalid links are stored but validation happens on access (FR-004)."""
        # Pydantic will validate URL format at creation time
        # But broken/inaccessible links are detected on access, not during ingestion
        # This test verifies valid URL format is accepted
        document = Document(
            meeting_id=meeting_id,
            title="Document with Link",
            link="https://example.com/potentially-broken-link.pdf"
        )
        assert document.link is not None
        # Actual link accessibility check happens in query service (T052)
    
    def test_document_with_custom_id(self, meeting_id):
        """Test creating document with custom UUID."""
        custom_id = uuid4()
        document = Document(
            id=custom_id,
            meeting_id=meeting_id,
            title="Custom Document",
            link="https://example.com/custom.pdf"
        )
        assert document.id == custom_id


class TestDecisionItemModel:
    """Unit tests for DecisionItem model validation."""
    
    @pytest.fixture
    def agenda_item_id(self):
        """Fixture for agenda item UUID."""
        return uuid4()
    
    def test_decision_item_creation_valid(self, agenda_item_id):
        """Test creating a valid decision item."""
        decision_item = DecisionItem(
            agenda_item_id=agenda_item_id,
            decision="Approved budget increase of 10%"
        )
        assert decision_item.agenda_item_id == agenda_item_id
        assert decision_item.decision == "Approved budget increase of 10%"
        assert isinstance(decision_item.id, UUID)
        assert decision_item.created_at is not None
        assert decision_item.updated_at is not None
    
    def test_decision_item_agenda_item_id_required(self):
        """Test agenda_item_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionItem(decision="Test decision")
        assert "agenda_item_id" in str(exc_info.value)
    
    def test_decision_item_decision_required(self, agenda_item_id):
        """Test decision text is required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionItem(agenda_item_id=agenda_item_id)
        assert "decision" in str(exc_info.value)
    
    def test_decision_item_decision_not_empty(self, agenda_item_id):
        """Test decision text cannot be empty."""
        with pytest.raises(ValidationError):
            DecisionItem(agenda_item_id=agenda_item_id, decision="")
        
        with pytest.raises(ValidationError):
            DecisionItem(agenda_item_id=agenda_item_id, decision="   ")
    
    def test_decision_item_with_rationale(self, agenda_item_id):
        """Test decision item with rationale."""
        decision_item = DecisionItem(
            agenda_item_id=agenda_item_id,
            decision="Approved new feature",
            rationale="Based on user feedback and technical feasibility"
        )
        assert decision_item.rationale == "Based on user feedback and technical feasibility"
    
    def test_decision_item_with_effect(self, agenda_item_id):
        """Test decision item with effect scope."""
        decision_item = DecisionItem(
            agenda_item_id=agenda_item_id,
            decision="Approved budget change",
            effect=DecisionEffect.MAY_AFFECT_OTHER_PEOPLE
        )
        assert decision_item.effect == DecisionEffect.MAY_AFFECT_OTHER_PEOPLE
    
    def test_decision_item_effect_enum(self, agenda_item_id):
        """Test decision effect enum values."""
        # Test both enum values
        decision1 = DecisionItem(
            agenda_item_id=agenda_item_id,
            decision="Decision 1",
            effect=DecisionEffect.AFFECTS_ONLY_THIS_WORKGROUP
        )
        assert decision1.effect == DecisionEffect.AFFECTS_ONLY_THIS_WORKGROUP
        
        decision2 = DecisionItem(
            agenda_item_id=agenda_item_id,
            decision="Decision 2",
            effect=DecisionEffect.MAY_AFFECT_OTHER_PEOPLE
        )
        assert decision2.effect == DecisionEffect.MAY_AFFECT_OTHER_PEOPLE
    
    def test_decision_item_optional_fields(self, agenda_item_id):
        """Test decision item with optional fields."""
        decision_item = DecisionItem(
            agenda_item_id=agenda_item_id,
            decision="Simple decision"
        )
        assert decision_item.rationale is None
        assert decision_item.effect is None
    
    def test_decision_item_with_custom_id(self, agenda_item_id):
        """Test creating decision item with custom UUID."""
        custom_id = uuid4()
        decision_item = DecisionItem(
            id=custom_id,
            agenda_item_id=agenda_item_id,
            decision="Custom decision"
        )
        assert decision_item.id == custom_id


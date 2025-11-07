"""Unit tests for PeopleCommand entity normalization."""

import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from src.bot.commands.people import PeopleCommand
from src.models.person import Person
from src.services.entity_normalization import EntityNormalizationService
from src.services.entity_query import EntityQueryService


class TestPeopleCommandNormalization:
    """Unit tests for PeopleCommand normalization features."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock Discord bot."""
        return Mock()
    
    @pytest.fixture
    def mock_rate_limiter(self):
        """Create mock rate limiter."""
        rate_limiter = Mock()
        rate_limiter.check_rate_limit.return_value = (True, None)
        rate_limiter.record_query.return_value = None
        return rate_limiter
    
    @pytest.fixture
    def mock_permission_checker(self):
        """Create mock permission checker."""
        checker = Mock()
        checker.has_permission.return_value = True
        return checker
    
    @pytest.fixture
    def mock_message_formatter(self):
        """Create mock message formatter."""
        formatter = Mock()
        formatter.format_meeting_citation.return_value = "[meeting-id | date | workgroup]"
        formatter.format_error_message.return_value = "Error message"
        formatter.create_issue_report_button_view.return_value = None
        return formatter
    
    @pytest.fixture
    def mock_entity_query_service(self):
        """Create mock entity query service."""
        service = Mock(spec=EntityQueryService)
        return service
    
    @pytest.fixture
    def normalization_service(self):
        """Create real normalization service."""
        return EntityNormalizationService()
    
    @pytest.fixture
    def people_command(
        self,
        mock_bot,
        mock_rate_limiter,
        mock_permission_checker,
        mock_message_formatter,
        mock_entity_query_service,
        normalization_service
    ):
        """Create PeopleCommand instance."""
        return PeopleCommand(
            bot=mock_bot,
            rate_limiter=mock_rate_limiter,
            permission_checker=mock_permission_checker,
            message_formatter=mock_message_formatter,
            entity_query_service=mock_entity_query_service,
            normalization_service=normalization_service
        )
    
    @pytest.fixture
    def sample_people(self):
        """Create sample person entities with variations."""
        person1 = Person(
            id=uuid4(),
            display_name="Stephen",
            alias="Stephen [QADAO]"
        )
        person2 = Person(
            id=uuid4(),
            display_name="stephen",
            alias=None
        )
        person3 = Person(
            id=uuid4(),
            display_name="Stephen QADAO",
            alias=None
        )
        return [person1, person2, person3]
    
    def test_get_name_variations(self, people_command, sample_people):
        """Test _get_name_variations method finds all variations."""
        canonical_name = "Stephen"
        
        variations, person_ids = people_command._get_name_variations(
            canonical_name,
            sample_people
        )
        
        # Should find variations
        assert len(variations) > 0
        assert "Stephen" in variations or "stephen" in variations
        assert len(person_ids) > 0
    
    def test_format_people_response_with_normalization(self, people_command):
        """Test response formatting shows normalization."""
        person = Person(
            id=uuid4(),
            display_name="Stephen",
            alias="Stephen [QADAO]"
        )
        meetings = []
        
        response = people_command._format_people_response(
            person=person,
            meetings=meetings,
            original_query="Stephen [QADAO]",
            canonical_name="Stephen",
            name_variations=["Stephen", "Stephen [QADAO]", "stephen"]
        )
        
        # Should show normalization message
        assert "normalized from" in response
        assert "Stephen [QADAO]" in response
        assert "Name variations" in response
    
    def test_format_people_response_without_normalization(self, people_command):
        """Test response formatting without normalization."""
        person = Person(
            id=uuid4(),
            display_name="Stephen",
            alias=None
        )
        meetings = []
        
        response = people_command._format_people_response(
            person=person,
            meetings=meetings,
            original_query="Stephen",
            canonical_name="Stephen",
            name_variations=["Stephen"]
        )
        
        # Should not show normalization message
        assert "normalized from" not in response
        assert "**Person:** Stephen" in response
    
    @pytest.mark.asyncio
    async def test_normalization_integration(
        self,
        people_command,
        mock_entity_query_service,
        sample_people
    ):
        """Test normalization is called during search."""
        # Mock entity query service
        mock_entity_query_service.find_all = Mock(return_value=sample_people)
        mock_entity_query_service.get_by_id = Mock(return_value=sample_people[0])
        mock_entity_query_service.get_meetings_by_person = Mock(return_value=[])
        
        # Mock interaction
        mock_interaction = Mock()
        mock_interaction.user = Mock()
        mock_interaction.user.id = 123
        mock_interaction.user.name = "testuser"
        mock_interaction.guild = None
        mock_interaction.response = AsyncMock()
        mock_interaction.followup = AsyncMock()
        
        # Test normalization is used
        with patch.object(
            people_command.normalization_service,
            'normalize_entity_name',
            return_value=(sample_people[0].id, "Stephen")
        ):
            await people_command.handle_people_command(
                mock_interaction,
                "Stephen [QADAO]"
            )
            
            # Verify normalization was attempted
            mock_entity_query_service.find_all.assert_called_once()


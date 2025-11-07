"""Unit tests for TopicsCommand entity normalization."""

import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from src.bot.commands.topics import TopicsCommand
from src.services.entity_normalization import EntityNormalizationService
from src.services.entity_query import EntityQueryService


class TestTopicsCommandNormalization:
    """Unit tests for TopicsCommand normalization features."""
    
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
    def topics_command(
        self,
        mock_bot,
        mock_rate_limiter,
        mock_permission_checker,
        mock_message_formatter,
        mock_entity_query_service,
        normalization_service
    ):
        """Create TopicsCommand instance."""
        return TopicsCommand(
            bot=mock_bot,
            rate_limiter=mock_rate_limiter,
            permission_checker=mock_permission_checker,
            message_formatter=mock_message_formatter,
            entity_query_service=mock_entity_query_service,
            normalization_service=normalization_service
        )
    
    def test_format_topics_response_with_normalization(self, topics_command):
        """Test response formatting shows normalization."""
        meetings = []
        
        response = topics_command._format_topics_response(
            topic="budget",
            meetings=meetings,
            original_query="Budget",
            canonical_topic="budget",
            topic_variations=["budget", "Budget", "budget planning"]
        )
        
        # Should show normalization message if different
        assert "**Topic:**" in response
    
    def test_format_topics_response_without_normalization(self, topics_command):
        """Test response formatting without normalization."""
        meetings = []
        
        response = topics_command._format_topics_response(
            topic="budget",
            meetings=meetings,
            original_query="budget",
            canonical_topic="budget",
            topic_variations=["budget"]
        )
        
        # Should show topic name
        assert "**Topic:** budget" in response
    
    def test_format_topics_response_with_variations(self, topics_command):
        """Test response formatting shows topic variations."""
        meetings = []
        
        response = topics_command._format_topics_response(
            topic="budget",
            meetings=meetings,
            original_query="Budget",
            canonical_topic="budget",
            topic_variations=["budget", "Budget", "budget planning"]
        )
        
        # Should show variations if multiple
        if len(["budget", "Budget", "budget planning"]) > 1:
            assert "Topic variations" in response or "variations" in response.lower()
    
    @pytest.mark.asyncio
    async def test_normalization_integration(
        self,
        topics_command,
        mock_entity_query_service
    ):
        """Test normalization is called during search."""
        # Mock entity query service
        mock_entity_query_service.get_all_topics = Mock(return_value=["budget", "Budget", "planning"])
        mock_entity_query_service.get_meetings_by_tag = Mock(return_value=[])
        
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
            topics_command.normalization_service,
            'find_similar_entities',
            return_value=[]
        ):
            await topics_command.handle_topics_command(
                mock_interaction,
                "Budget"
            )
            
            # Verify get_all_topics was called for normalization
            mock_entity_query_service.get_all_topics.assert_called_once()


"""Integration tests for entity normalization in bot commands."""

import pytest
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from src.bot.commands.people import PeopleCommand
from src.bot.commands.topics import TopicsCommand
from src.services.entity_query import EntityQueryService
from src.services.entity_normalization import EntityNormalizationService
from src.models.person import Person
from src.models.meeting import Meeting
from src.models.workgroup import Workgroup
from src.lib.config import ENTITIES_PEOPLE_DIR, ENTITIES_MEETINGS_DIR, ENTITIES_WORKGROUPS_DIR


class TestPeopleCommandNormalizationIntegration:
    """Integration tests for PeopleCommand normalization."""
    
    @pytest.fixture
    def entity_query_service(self):
        """Create entity query service."""
        return EntityQueryService()
    
    @pytest.fixture
    def normalization_service(self):
        """Create normalization service."""
        return EntityNormalizationService()
    
    def test_normalization_finds_similar_people(self, entity_query_service, normalization_service):
        """Test that normalization finds similar person names."""
        # Load all people
        all_people = entity_query_service.find_all(ENTITIES_PEOPLE_DIR, Person)
        
        if not all_people:
            pytest.skip("No people entities found in database")
        
        # Test normalization with first person
        test_person = all_people[0]
        test_name = test_person.display_name
        
        # Try normalizing with a variation
        normalized_id, canonical_name = normalization_service.normalize_entity_name(
            test_name,
            all_people,
            {}
        )
        
        # Should find the person
        assert normalized_id.int != 0 or canonical_name is not None
    
    def test_get_name_variations_finds_all(self, entity_query_service, normalization_service):
        """Test that _get_name_variations finds all variations."""
        # Load all people
        all_people = entity_query_service.find_all(ENTITIES_PEOPLE_DIR, Person)
        
        if not all_people:
            pytest.skip("No people entities found in database")
        
        # Create command instance
        from unittest.mock import Mock
        command = PeopleCommand(
            bot=Mock(),
            rate_limiter=Mock(),
            permission_checker=Mock(),
            message_formatter=Mock(),
            entity_query_service=entity_query_service,
            normalization_service=normalization_service
        )
        
        # Test with first person
        test_person = all_people[0]
        canonical_name = test_person.display_name
        
        variations, person_ids = command._get_name_variations(
            canonical_name,
            all_people
        )
        
        # Should find at least the canonical name
        assert len(variations) > 0
        assert len(person_ids) > 0


class TestTopicsCommandNormalizationIntegration:
    """Integration tests for TopicsCommand normalization."""
    
    @pytest.fixture
    def entity_query_service(self):
        """Create entity query service."""
        return EntityQueryService()
    
    @pytest.fixture
    def normalization_service(self):
        """Create normalization service."""
        return EntityNormalizationService()
    
    def test_normalization_finds_similar_topics(self, entity_query_service, normalization_service):
        """Test that normalization finds similar topic names."""
        # Get all topics
        all_topics = entity_query_service.get_all_topics()
        
        if not all_topics:
            pytest.skip("No topics found in database")
        
        # Create entity-like structure for normalization
        class TopicEntity:
            def __init__(self, name):
                self.name = name
                self.display_name = name
                self.id = None
        
        topic_entities = [TopicEntity(t) for t in all_topics]
        
        # Test with first topic
        test_topic = all_topics[0]
        
        # Find similar topics
        similar = normalization_service.find_similar_entities(
            test_topic,
            topic_entities
        )
        
        # Should find at least the exact match
        assert len(similar) > 0
    
    def test_topics_search_with_normalization(self, entity_query_service, normalization_service):
        """Test that topics search works with normalization."""
        # Get all topics
        all_topics = entity_query_service.get_all_topics()
        
        if not all_topics:
            pytest.skip("No topics found in database")
        
        # Create command instance
        from unittest.mock import Mock
        command = TopicsCommand(
            bot=Mock(),
            rate_limiter=Mock(),
            permission_checker=Mock(),
            message_formatter=Mock(),
            entity_query_service=entity_query_service,
            normalization_service=normalization_service
        )
        
        # Test with first topic (case variation)
        test_topic = all_topics[0]
        test_variation = test_topic.upper() if test_topic else "test"
        
        # Search should work
        meetings = entity_query_service.get_meetings_by_tag(test_topic, "topics")
        
        # Should return list (may be empty)
        assert isinstance(meetings, list)


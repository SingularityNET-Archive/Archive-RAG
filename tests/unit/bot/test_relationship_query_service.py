"""Unit tests for relationship query service."""

import pytest
from uuid import UUID, uuid4

from src.bot.services.relationship_query_service import RelationshipQueryService
from src.services.relationship_triple_generator import RelationshipTripleGenerator
from src.services.entity_normalization import EntityNormalizationService
from src.services.entity_query import EntityQueryService


class TestRelationshipQueryService:
    """Unit tests for RelationshipQueryService."""
    
    @pytest.fixture
    def service(self):
        """Create relationship query service instance."""
        return RelationshipQueryService()
    
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert service.relationship_generator is not None
        assert service.normalization_service is not None
        assert service.entity_query_service is not None
    
    def test_get_relationships_for_workgroup_nonexistent(self, service):
        """Test getting relationships for non-existent workgroup."""
        triples, canonical_name, error_msg = service.get_relationships_for_workgroup("Nonexistent Workgroup")
        
        assert error_msg is not None
        assert "not found" in error_msg.lower()
        assert len(triples) == 0
    
    def test_get_relationships_for_person_nonexistent(self, service):
        """Test getting relationships for non-existent person."""
        triples, canonical_name, error_msg = service.get_relationships_for_person("Nonexistent Person")
        
        assert error_msg is not None
        assert "not found" in error_msg.lower()
        assert len(triples) == 0
    
    def test_get_relationships_for_meeting_nonexistent(self, service):
        """Test getting relationships for non-existent meeting."""
        meeting_id = uuid4()
        triples, error_msg = service.get_relationships_for_meeting(meeting_id)
        
        assert error_msg is not None
        assert "not found" in error_msg.lower() or len(triples) == 0
    
    def test_suggest_workgroups(self, service):
        """Test workgroup name suggestions."""
        # Should return empty list or suggestions for non-existent workgroup
        suggestions = service._suggest_workgroups("Test", limit=3)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3
    
    def test_suggest_people(self, service):
        """Test person name suggestions."""
        # Should return empty list or suggestions for non-existent person
        suggestions = service._suggest_people("Test", limit=3)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3
    
    def test_find_workgroup_by_name(self, service):
        """Test finding workgroup by name."""
        # Should return None for non-existent workgroup
        workgroup = service._find_workgroup_by_name("Nonexistent Workgroup")
        
        assert workgroup is None
    
    def test_find_person_by_name(self, service):
        """Test finding person by name."""
        # Should return None for non-existent person
        person = service._find_person_by_name("Nonexistent Person")
        
        assert person is None
    
    def test_load_meeting_related_entities(self, service):
        """Test loading meeting-related entities."""
        meeting_id = uuid4()
        entities = service._load_meeting_related_entities(meeting_id)
        
        assert isinstance(entities, list)
        # May be empty if meeting doesn't exist



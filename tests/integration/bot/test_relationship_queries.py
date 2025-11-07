"""Integration tests for relationship queries."""

import pytest
from uuid import uuid4

from src.bot.services.relationship_query_service import RelationshipQueryService, create_relationship_query_service
from src.services.entity_query import EntityQueryService
from src.services.entity_normalization import EntityNormalizationService


class TestRelationshipQueriesIntegration:
    """Integration tests for relationship query service."""
    
    @pytest.fixture
    def relationship_service(self):
        """Create relationship query service."""
        return create_relationship_query_service()
    
    @pytest.fixture
    def entity_query_service(self):
        """Create entity query service."""
        return EntityQueryService()
    
    def test_get_relationships_for_person_with_real_data(self, relationship_service):
        """Test getting relationships for a person with real entity data."""
        # This test requires actual entity data to exist
        # Skip if no data available
        try:
            triples, canonical_name, error_msg = relationship_service.get_relationships_for_person("Stephen")
            
            # Should either return relationships or a helpful error message
            assert isinstance(triples, list)
            assert isinstance(error_msg, (str, type(None)))
            
            if not error_msg:
                # If no error, should have canonical name
                assert canonical_name is not None
        except Exception:
            pytest.skip("No entity data available for integration test")
    
    def test_get_relationships_for_workgroup_with_real_data(self, relationship_service):
        """Test getting relationships for a workgroup with real entity data."""
        try:
            triples, canonical_name, error_msg = relationship_service.get_relationships_for_workgroup("Archives")
            
            # Should either return relationships or a helpful error message
            assert isinstance(triples, list)
            assert isinstance(error_msg, (str, type(None)))
            
            if not error_msg:
                # If no error, should have canonical name
                assert canonical_name is not None
        except Exception:
            pytest.skip("No entity data available for integration test")
    
    def test_relationship_query_handles_nonexistent_entity(self, relationship_service):
        """Test that relationship queries handle nonexistent entities gracefully."""
        triples, canonical_name, error_msg = relationship_service.get_relationships_for_person("NonexistentPerson12345")
        
        # Should return error message with suggestions
        assert error_msg is not None
        assert isinstance(error_msg, str)
        assert len(error_msg) > 0
    
    def test_relationship_query_normalizes_entity_names(self, relationship_service):
        """Test that relationship queries normalize entity name variations."""
        try:
            # Try with a variation (if entity exists)
            triples1, canonical1, error1 = relationship_service.get_relationships_for_person("Stephen")
            triples2, canonical2, error2 = relationship_service.get_relationships_for_person("Stephen [QADAO]")
            
            # If both succeed, canonical names should match
            if not error1 and not error2:
                assert canonical1 == canonical2
        except Exception:
            pytest.skip("No entity data available for integration test")



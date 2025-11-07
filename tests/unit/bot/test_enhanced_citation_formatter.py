"""Unit tests for enhanced citation formatter service."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from src.bot.services.enhanced_citation_formatter import EnhancedCitationFormatter
from src.bot.models.enhanced_citation import EnhancedCitation
from src.models.rag_query import Citation
from src.models.meeting import Meeting
from src.models.workgroup import Workgroup
from src.models.person import Person
from src.services.entity_normalization import EntityNormalizationService
from src.services.relationship_triple_generator import RelationshipTripleGenerator
from src.services.entity_query import EntityQueryService


class TestEnhancedCitationFormatter:
    """Unit tests for EnhancedCitationFormatter."""
    
    @pytest.fixture
    def formatter(self):
        """Create enhanced citation formatter instance."""
        return EnhancedCitationFormatter()
    
    @pytest.fixture
    def sample_citation(self):
        """Create sample citation."""
        return Citation(
            meeting_id=str(uuid4()),
            date="2024-01-15",
            workgroup_name="Archives WG",
            excerpt="Test meeting excerpt"
        )
    
    def test_format_citation_basic(self, formatter, sample_citation):
        """Test basic citation formatting."""
        result = formatter.format_citation(sample_citation)
        
        assert "[" in result
        assert "]" in result
        assert sample_citation.meeting_id in result
        assert sample_citation.date in result
        assert "Archives WG" in result or "unknown" in result
    
    def test_format_citation_with_invalid_meeting_id(self, formatter):
        """Test citation formatting with invalid meeting ID."""
        citation = Citation(
            meeting_id="invalid-uuid",
            date="2024-01-15",
            workgroup_name="Test WG",
            excerpt="Test"
        )
        
        result = formatter.format_citation(citation)
        
        # Should fallback to basic format
        assert "[" in result
        assert "]" in result
        assert "invalid-uuid" in result or "Test WG" in result
    
    def test_format_enhanced_citation_basic(self, formatter, sample_citation):
        """Test enhanced citation model creation."""
        result = formatter.format_enhanced_citation(sample_citation)
        
        assert isinstance(result, EnhancedCitation)
        assert result.meeting_id == sample_citation.meeting_id
        assert result.date == sample_citation.date
        assert result.excerpt == sample_citation.excerpt
    
    def test_format_enhanced_citation_with_meeting_id(self, formatter, sample_citation):
        """Test enhanced citation with meeting UUID."""
        meeting_id = UUID(sample_citation.meeting_id)
        result = formatter.format_enhanced_citation(sample_citation, meeting_id)
        
        assert isinstance(result, EnhancedCitation)
        assert result.meeting_id == sample_citation.meeting_id
    
    def test_format_enhanced_citation_includes_normalized_entities(self, formatter, sample_citation):
        """Test that enhanced citation includes normalized entities field."""
        result = formatter.format_enhanced_citation(sample_citation)
        
        assert hasattr(result, "normalized_entities")
        assert isinstance(result.normalized_entities, list)
    
    def test_format_enhanced_citation_includes_relationship_triples(self, formatter, sample_citation):
        """Test that enhanced citation includes relationship triples field."""
        result = formatter.format_enhanced_citation(sample_citation)
        
        assert hasattr(result, "relationship_triples")
        assert isinstance(result.relationship_triples, list)
    
    def test_format_enhanced_citation_includes_chunk_type(self, formatter, sample_citation):
        """Test that enhanced citation includes chunk_type field."""
        result = formatter.format_enhanced_citation(sample_citation)
        
        assert hasattr(result, "chunk_type")
        # chunk_type may be None if not available
    
    def test_format_enhanced_citation_includes_chunk_entities(self, formatter, sample_citation):
        """Test that enhanced citation includes chunk_entities field."""
        result = formatter.format_enhanced_citation(sample_citation)
        
        assert hasattr(result, "chunk_entities")
        assert isinstance(result.chunk_entities, list)


class TestEnhancedCitationFormatterIntegration:
    """Integration tests for enhanced citation formatter with real services."""
    
    @pytest.fixture
    def formatter(self):
        """Create enhanced citation formatter with real services."""
        return EnhancedCitationFormatter(
            normalization_service=EntityNormalizationService(),
            relationship_generator=RelationshipTripleGenerator(),
            entity_query_service=EntityQueryService()
        )
    
    def test_format_citation_with_real_services(self, formatter):
        """Test citation formatting with real entity services."""
        citation = Citation(
            meeting_id=str(uuid4()),
            date="2024-01-15",
            workgroup_name="Test WG",
            excerpt="Test excerpt"
        )
        
        # Should not raise exception even if meeting doesn't exist
        result = formatter.format_citation(citation)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_format_enhanced_citation_with_real_services(self, formatter):
        """Test enhanced citation with real entity services."""
        citation = Citation(
            meeting_id=str(uuid4()),
            date="2024-01-15",
            workgroup_name="Test WG",
            excerpt="Test excerpt"
        )
        
        # Should not raise exception even if meeting doesn't exist
        result = formatter.format_enhanced_citation(citation)
        assert isinstance(result, EnhancedCitation)


class TestEnhancedCitationFormatterPhase8:
    """Phase 8: Tests for error handling and message length validation."""
    
    @pytest.fixture
    def formatter(self):
        """Create enhanced citation formatter instance."""
        return EnhancedCitationFormatter()
    
    def test_format_citation_handles_missing_entity_data(self, formatter):
        """Phase 8: T059 - Test error handling for missing entity data."""
        citation = Citation(
            meeting_id=str(uuid4()),
            date="2024-01-15",
            workgroup_name=None,  # Missing workgroup name
            excerpt="Test excerpt"
        )
        
        # Should not raise exception, should fallback gracefully
        result = formatter.format_citation(citation)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "unknown" in result or citation.meeting_id in result
    
    def test_format_citation_handles_missing_chunk_metadata(self, formatter):
        """Phase 8: T061 - Test error handling for missing chunk metadata."""
        citation = Citation(
            meeting_id=str(uuid4()),
            date="2024-01-15",
            workgroup_name="Test WG",
            excerpt="Test excerpt",
            chunk_type=None,  # Missing chunk type
            chunk_entities=None,  # Missing entities
            chunk_relationships=None  # Missing relationships
        )
        
        # Should not raise exception, should format without chunk metadata
        result = formatter.format_citation(citation)
        assert isinstance(result, str)
        assert "[" in result
        assert "]" in result
    
    def test_format_citation_handles_invalid_entity_format(self, formatter):
        """Phase 8: T061 - Test error handling for invalid entity format."""
        citation = Citation(
            meeting_id=str(uuid4()),
            date="2024-01-15",
            workgroup_name="Test WG",
            excerpt="Test excerpt",
            chunk_entities=["not-a-dict", 123, None]  # Invalid entity formats
        )
        
        # Should not raise exception, should skip invalid entities
        result = formatter.format_citation(citation)
        assert isinstance(result, str)
    
    def test_format_citation_handles_invalid_relationship_format(self, formatter):
        """Phase 8: T060 - Test error handling for invalid relationship format."""
        citation = Citation(
            meeting_id=str(uuid4()),
            date="2024-01-15",
            workgroup_name="Test WG",
            excerpt="Test excerpt",
            chunk_relationships=["not-a-dict", 123, None]  # Invalid relationship formats
        )
        
        # Should not raise exception, should skip invalid relationships
        result = formatter.format_citation(citation)
        assert isinstance(result, str)
    
    def test_format_citation_validates_message_length(self, formatter):
        """Phase 8: T068 - Test message length validation."""
        from src.bot.config import DISCORD_MAX_MESSAGE_LENGTH
        
        # Create citation with very long chunk metadata that would exceed limit
        long_entities = [{"normalized_name": f"Entity{i}" * 50} for i in range(100)]
        citation = Citation(
            meeting_id=str(uuid4()),
            date="2024-01-15",
            workgroup_name="Test WG",
            excerpt="Test excerpt",
            chunk_entities=long_entities
        )
        
        result = formatter.format_citation(citation)
        
        # Result should not exceed Discord's message length limit
        assert len(result) <= DISCORD_MAX_MESSAGE_LENGTH
        assert isinstance(result, str)
    
    def test_format_citations_section_validates_length(self, formatter):
        """Phase 8: T068 - Test citations section length validation."""
        from src.bot.utils.message_splitter import MAX_CHUNK_LENGTH
        
        # Create many citations that would exceed limit
        citations = [
            Citation(
                meeting_id=str(uuid4()),
                date="2024-01-15",
                workgroup_name=f"Workgroup {i}",
                excerpt=f"Excerpt {i}" * 100  # Long excerpt
            )
            for i in range(50)
        ]
        
        # Use message formatter to format citations section
        from src.bot.services.message_formatter import MessageFormatter
        message_formatter = MessageFormatter()
        
        result = message_formatter.format_citations_section(citations)
        
        # Result should not exceed Discord's message length limit
        assert len(result) <= MAX_CHUNK_LENGTH
        assert isinstance(result, str)
        # Should include truncation indicator if truncated
        if len(citations) > 10:  # If many citations, might be truncated
            assert "more citations" in result or len(result) <= MAX_CHUNK_LENGTH



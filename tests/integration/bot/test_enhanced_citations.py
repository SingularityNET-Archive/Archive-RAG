"""Integration tests for enhanced citations in query responses."""

import pytest
from uuid import uuid4
from datetime import datetime

from src.bot.services.message_formatter import MessageFormatter
from src.bot.services.enhanced_citation_formatter import EnhancedCitationFormatter
from src.models.rag_query import RAGQuery, Citation, RetrievedChunk


class TestEnhancedCitationsIntegration:
    """Integration tests for enhanced citations."""
    
    @pytest.fixture
    def message_formatter(self):
        """Create message formatter with enhanced citations."""
        return MessageFormatter()
    
    @pytest.fixture
    def sample_rag_query(self):
        """Create sample RAGQuery with citations."""
        return RAGQuery(
            query_id=str(uuid4()),
            user_input="What decisions were made?",
            timestamp=datetime.utcnow().isoformat(),
            retrieved_chunks=[
                RetrievedChunk(
                    meeting_id=str(uuid4()),
                    chunk_index=0,
                    text="Test chunk text",
                    score=0.85
                )
            ],
            output="Based on the meeting records...",
            citations=[
                Citation(
                    meeting_id=str(uuid4()),
                    date="2024-01-15",
                    workgroup_name="Archives WG",
                    excerpt="Test excerpt"
                )
            ],
            model_version="test-model-v1.0",
            embedding_version="test-embedding-v1.0",
            evidence_found=True,
            audit_log_path="test-audit-log.json"
        )
    
    def test_format_query_response_with_enhanced_citations(self, message_formatter, sample_rag_query):
        """Test that query response formatting includes enhanced citations."""
        answer_text, citation_strings = message_formatter.format_query_response(sample_rag_query)
        
        assert isinstance(answer_text, str)
        assert len(answer_text) > 0
        assert isinstance(citation_strings, list)
        assert len(citation_strings) == len(sample_rag_query.citations)
        
        # Check citation format
        for citation_str in citation_strings:
            assert "[" in citation_str
            assert "]" in citation_str
    
    def test_format_citation_uses_enhanced_formatter(self, message_formatter, sample_rag_query):
        """Test that MessageFormatter uses enhanced citation formatter."""
        citation = sample_rag_query.citations[0]
        
        # Format citation
        citation_str = message_formatter.format_citation(citation)
        
        assert isinstance(citation_str, str)
        assert len(citation_str) > 0
        assert citation.meeting_id in citation_str or "[" in citation_str
    
    def test_format_citations_section_with_enhanced_citations(self, message_formatter, sample_rag_query):
        """Test formatting citations section with enhanced citations."""
        citations_section = message_formatter.format_citations_section(sample_rag_query.citations)
        
        assert isinstance(citations_section, str)
        assert "Citations:" in citations_section or "**Citations:**" in citations_section
        
        # Should contain citation strings
        for citation in sample_rag_query.citations:
            assert citation.meeting_id in citations_section or "[" in citations_section




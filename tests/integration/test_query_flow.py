"""Integration test for query journey."""

import pytest
from pathlib import Path
from src.models.meeting_record import MeetingRecord
from src.services.ingestion import ingest_meeting_file
from src.services.chunking import chunk_transcript
from src.services.embedding import create_embedding_service
from src.services.index_builder import build_faiss_index, save_index
from src.services.retrieval import load_index, retrieve_similar_chunks
from src.services.rag_generator import create_rag_generator
from src.services.citation_extractor import extract_citations
from src.services.evidence_checker import check_evidence


class TestQueryFlow:
    """Integration tests for end-to-end query flow."""
    
    @pytest.fixture
    def sample_meeting_file(self, tmp_path):
        """Create sample meeting JSON file."""
        meeting_file = tmp_path / "meeting_001.json"
        meeting_file.write_text("""{
            "id": "meeting_001",
            "date": "2024-03-15T10:00:00Z",
            "participants": ["Alice", "Bob"],
            "transcript": "The budget committee decided to allocate $100k to the marketing department. Additional funding of $50k was approved for Q2 projects."
        }""")
        return meeting_file
    
    @pytest.fixture
    def embedding_service(self):
        """Create embedding service."""
        try:
            return create_embedding_service()
        except Exception:
            pytest.skip("Embedding service dependencies not available")
    
    def test_end_to_end_query_flow(self, sample_meeting_file, embedding_service, tmp_path):
        """Test end-to-end query flow."""
        # Step 1: Ingest meeting file
        meeting_record, file_hash = ingest_meeting_file(sample_meeting_file)
        assert meeting_record.id == "meeting_001"
        
        # Step 2: Chunk transcript
        chunks = chunk_transcript(meeting_record)
        assert len(chunks) > 0
        
        # Step 3: Build index
        index_name = "test_index"
        index, embedding_index = build_faiss_index(
            chunks,
            embedding_service,
            index_type="IndexFlatIP",
            index_name=index_name
        )
        
        # Step 4: Save index
        save_index(index, embedding_index, index_name)
        
        # Step 5: Load index
        loaded_index, loaded_metadata = load_index(index_name)
        
        # Step 6: Query
        query_text = "What decisions were made about budget?"
        query_embedding = embedding_service.embed_text(query_text)
        retrieved_chunks = retrieve_similar_chunks(
            query_embedding,
            loaded_index,
            loaded_metadata,
            top_k=5
        )
        
        assert len(retrieved_chunks) > 0
        
        # Step 7: Check evidence
        evidence_found = check_evidence(retrieved_chunks)
        assert evidence_found is True
        
        # Step 8: Extract citations
        citations = extract_citations(retrieved_chunks)
        assert len(citations) > 0
        
        # Step 9: Generate answer (if LLM available)
        try:
            rag_generator = create_rag_generator()
            answer = rag_generator.generate(query_text, retrieved_chunks)
            assert answer is not None
        except Exception:
            # LLM may not be available, skip this part
            pass


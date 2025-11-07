"""RAGQuery model for user queries and responses."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """Retrieved chunk from FAISS index."""
    
    meeting_id: str = Field(..., description="Meeting identifier")
    chunk_index: int = Field(..., description="Chunk index within meeting")
    text: str = Field(..., description="Chunk text content")
    score: float = Field(..., description="Similarity score")


class Citation(BaseModel):
    """Citation in format [meeting_id | date | workgroup_name]."""
    
    meeting_id: str = Field(..., description="Meeting identifier")
    date: str = Field(..., description="Meeting date")
    workgroup_name: Optional[str] = Field(None, description="Workgroup name")
    excerpt: str = Field(..., description="Cited text excerpt")
    # Semantic chunk metadata (Phase 7)
    chunk_type: Optional[str] = Field(None, description="Semantic chunk type (meeting_summary, decision_record, action_item, attendance, resource)")
    chunk_entities: Optional[List[Dict[str, Any]]] = Field(None, description="Entities mentioned in the chunk (from chunk metadata)")
    chunk_relationships: Optional[List[Dict[str, Any]]] = Field(None, description="Relationships relevant to chunk (from chunk metadata)")


class RAGQuery(BaseModel):
    """
    RAG query model representing a user query and its processed response.
    
    Fields:
        query_id: Unique query identifier (UUID)
        user_input: Original user question
        timestamp: Query execution timestamp
        retrieved_chunks: Retrieved document chunks with metadata
        output: Generated answer text
        citations: Verifiable citations in format [meeting_id | date | workgroup_name]
        model_version: Version of LLM used for generation
        embedding_version: Version of embedding model used
        user_id: SSO user identifier (optional)
        evidence_found: Whether credible evidence was found
        audit_log_path: Path to immutable audit log entry
    """
    
    query_id: str = Field(..., description="Unique query identifier (UUID)")
    user_input: str = Field(..., description="Original user question")
    timestamp: str = Field(..., description="Query execution timestamp (ISO 8601)")
    retrieved_chunks: List[RetrievedChunk] = Field(..., description="Retrieved document chunks with metadata")
    output: str = Field(..., description="Generated answer text")
    citations: List[Citation] = Field(..., description="Verifiable citations")
    model_version: str = Field(..., description="Version of LLM used for generation")
    embedding_version: str = Field(..., description="Version of embedding model used")
    user_id: Optional[str] = Field(None, description="SSO user identifier")
    evidence_found: bool = Field(..., description="Whether credible evidence was found")
    audit_log_path: str = Field(..., description="Path to immutable audit log entry")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RAGQuery":
        """Create from dictionary."""
        return cls(**data)
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "query_id": "uuid-123",
                "user_input": "What decisions were made about budget allocation?",
                "timestamp": "2024-11-02T10:00:00Z",
                "retrieved_chunks": [
                    {
                        "meeting_id": "meeting_001",
                        "chunk_index": 0,
                        "text": "The budget committee decided...",
                        "score": 0.85
                    }
                ],
                "output": "Based on the meeting records...",
                "citations": [
                    {
                        "meeting_id": "meeting_001",
                        "date": "2024-03-15",
                        "workgroup_name": "Budget Committee",
                        "excerpt": "The budget committee decided..."
                    }
                ],
                "model_version": "model-name-v1.0",
                "embedding_version": "all-MiniLM-L6-v2",
                "user_id": "user@example.com",
                "evidence_found": True,
                "audit_log_path": "audit_logs/query-uuid-123.json"
            }
        }


"""EmbeddingIndex model for FAISS vector index."""

from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field


class EmbeddingIndex(BaseModel):
    """
    Embedding index model representing a FAISS vector index.
    
    Fields:
        index_id: Unique index identifier
        version_hash: SHA-256 hash of index configuration and model versions
        embedding_model: Name and version of embedding model used
        embedding_dimension: Dimension of embedding vectors
        index_type: FAISS index type (e.g., IndexFlatIP, IndexIVFFlat)
        metadata: Mapping from vector index to document metadata
        total_documents: Total number of document chunks indexed
        created_at: Index creation timestamp
        index_path: File system path to FAISS index file
    """
    
    index_id: str = Field(..., description="Unique index identifier")
    version_hash: str = Field(..., description="SHA-256 hash of index configuration and model versions")
    embedding_model: str = Field(..., description="Name and version of embedding model used")
    embedding_dimension: int = Field(..., description="Dimension of embedding vectors")
    index_type: str = Field(..., description="FAISS index type (e.g., IndexFlatIP, IndexIVFFlat)")
    metadata: Dict[int, Dict[str, Any]] = Field(
        ...,
        description="Mapping from vector index to document metadata"
    )
    total_documents: int = Field(..., description="Total number of document chunks indexed")
    created_at: str = Field(..., description="Index creation timestamp (ISO 8601)")
    index_path: str = Field(..., description="File system path to FAISS index file")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingIndex":
        """Create from dictionary."""
        return cls(**data)
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "index_id": "index_001",
                "version_hash": "abc123...",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_dimension": 384,
                "index_type": "IndexFlatIP",
                "metadata": {
                    0: {
                        "meeting_id": "meeting_001",
                        "chunk_index": 0,
                        "text": "chunk text",
                        "date": "2024-03-15",
                        "participants": ["Alice", "Bob"]
                    }
                },
                "total_documents": 100,
                "created_at": "2024-11-02T10:00:00Z",
                "index_path": "indexes/meetings.faiss"
            }
        }


"""Chunk metadata model for semantic chunks with entity information."""

from typing import List, Optional
from uuid import UUID
from pydantic import Field, BaseModel


class ChunkEntity(BaseModel):
    """Entity information embedded in a chunk."""
    
    entity_id: UUID = Field(..., description="Entity UUID")
    entity_type: str = Field(..., description="Entity type (Person, Workgroup, Meeting, Document, DecisionItem, ActionItem)")
    normalized_name: str = Field(..., description="Canonical entity name")
    mentions: List[str] = Field(default_factory=list, description="All name variations found in chunk")


class ChunkRelationship(BaseModel):
    """Relationship information in chunk metadata."""
    
    subject: str = Field(..., description="Subject entity type")
    relationship: str = Field(..., description="Relationship type")
    object: str = Field(..., description="Object entity type")


class ChunkMetadataModel(BaseModel):
    """Metadata for a semantic chunk."""
    
    meeting_id: UUID = Field(..., description="Source meeting ID")
    chunk_type: str = Field(..., description="Chunk type (meeting_summary, action_item, decision_record, attendance, resource)")
    source_field: str = Field(..., description="JSON path source (e.g., 'meetingInfo.purpose')")
    relationships: List[ChunkRelationship] = Field(default_factory=list, description="Relationships relevant to chunk")
    chunk_index: Optional[int] = Field(None, description="0-based index for chunks from same source")
    total_chunks: Optional[int] = Field(None, description="Total chunks from same source")


class ChunkMetadata(BaseModel):
    """
    Complete chunk structure with text, entities, and metadata.
    
    Used for semantic chunks with embedded entity context.
    """
    
    text: str = Field(..., description="Chunk text content")
    entities: List[ChunkEntity] = Field(default_factory=list, description="Entities mentioned in chunk")
    metadata: ChunkMetadataModel = Field(..., description="Chunk metadata")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "text": "Meeting summary text...",
                "entities": [
                    {
                        "entity_id": "770e8400-e29b-41d4-a716-446655440000",
                        "entity_type": "Person",
                        "normalized_name": "Stephen",
                        "mentions": ["Stephen", "Stephen [QADAO]"]
                    }
                ],
                "metadata": {
                    "meeting_id": "880e8400-e29b-41d4-a716-446655440000",
                    "chunk_type": "meeting_summary",
                    "source_field": "meetingInfo.purpose",
                    "relationships": [
                        {
                            "subject": "Person",
                            "relationship": "attended",
                            "object": "Meeting"
                        }
                    ],
                    "chunk_index": 0,
                    "total_chunks": 1
                }
            }
        }


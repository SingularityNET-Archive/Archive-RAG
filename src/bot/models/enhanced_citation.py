"""Enhanced citation model for citations with entity context."""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class EnhancedCitation(BaseModel):
    """
    Enhanced citation with entity context including normalized names, relationships, and chunk metadata.
    
    Extends the base Citation model with:
    - Normalized entity names (canonical names)
    - Relationship triples (Subject -> Relationship -> Object)
    - Semantic chunk type (meeting_summary, decision_record, etc.)
    - Entity metadata from chunk (which entities are mentioned)
    """
    
    meeting_id: str = Field(..., description="Meeting identifier")
    date: str = Field(..., description="Meeting date")
    workgroup_name: Optional[str] = Field(None, description="Workgroup name (normalized)")
    excerpt: str = Field(..., description="Cited text excerpt")
    
    # Enhanced fields
    normalized_entities: List[dict] = Field(default_factory=list, description="Normalized entity names mentioned in citation")
    relationship_triples: List[dict] = Field(default_factory=list, description="Relationship triples relevant to citation")
    chunk_type: Optional[str] = Field(None, description="Semantic chunk type (meeting_summary, decision_record, action_item, attendance, resource)")
    chunk_entities: List[dict] = Field(default_factory=list, description="Entities mentioned in the chunk (from chunk metadata)")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "meeting_id": "meeting_001",
                "date": "2024-01-15",
                "workgroup_name": "Archives WG",
                "excerpt": "The decision was made to...",
                "normalized_entities": [
                    {
                        "entity_id": "entity_001",
                        "entity_type": "Person",
                        "canonical_name": "Stephen",
                        "variations": ["Stephen", "Stephen [QADAO]"]
                    }
                ],
                "relationship_triples": [
                    {
                        "subject": "Workgroup",
                        "relationship": "held",
                        "object": "Meeting"
                    },
                    {
                        "subject": "Person",
                        "relationship": "attended",
                        "object": "Meeting"
                    }
                ],
                "chunk_type": "decision_record",
                "chunk_entities": [
                    {
                        "entity_id": "entity_001",
                        "entity_type": "Person",
                        "normalized_name": "Stephen",
                        "mentions": ["Stephen"]
                    }
                ]
            }
        }



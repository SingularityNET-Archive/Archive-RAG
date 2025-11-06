"""NER-extracted entity model."""

from typing import Optional
from uuid import UUID
from pydantic import Field, BaseModel


class NEREntity(BaseModel):
    """
    Entity extracted from unstructured text using Named Entity Recognition (NER).
    
    NER entities are extracted from text fields and merged with structured
    entities when they refer to the same real-world object.
    """
    
    text: str = Field(..., description="Extracted entity text", min_length=1)
    entity_type: str = Field(..., description="spaCy entity type (PERSON, ORG, GPE, DATE, etc.)")
    source_text: str = Field(..., description="Original text field where entity was found")
    source_field: str = Field(..., description="JSON path (e.g., 'meetingInfo.purpose')")
    source_meeting_id: UUID = Field(..., description="Source meeting ID")
    normalized_entity_id: Optional[UUID] = Field(None, description="Canonical entity ID if merged with structured entity")
    confidence: float = Field(..., description="NER confidence score (0.0-1.0)", ge=0.0, le=1.0)
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "text": "QADAO",
                "entity_type": "ORG",
                "source_text": "Discuss QADAO budget proposal",
                "source_field": "meetingInfo.purpose",
                "source_meeting_id": "880e8400-e29b-41d4-a716-446655440000",
                "normalized_entity_id": "660e8400-e29b-41d4-a716-446655440000",
                "confidence": 0.95
            }
        }


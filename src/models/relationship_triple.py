"""Relationship triple model for entity relationships."""

from typing import Optional
from uuid import UUID
from pydantic import Field

from src.models.base import BaseEntity


class RelationshipTriple(BaseEntity):
    """
    Relationship triple representing a connection between two entities.
    
    Format: Subject -> Relationship -> Object
    Example: "Person -> attended -> Meeting"
    """
    
    subject_id: UUID = Field(..., description="Subject entity ID")
    subject_type: str = Field(..., description="Subject entity type (e.g., 'Person', 'Workgroup', 'Meeting')")
    subject_name: str = Field(..., description="Subject entity canonical name")
    relationship: str = Field(..., description="Relationship type (e.g., 'held', 'attended', 'produced', 'assigned_to')")
    object_id: UUID = Field(..., description="Object entity ID")
    object_type: str = Field(..., description="Object entity type")
    object_name: str = Field(..., description="Object entity canonical name")
    source_meeting_id: UUID = Field(..., description="Source meeting ID where relationship was found")
    source_field: str = Field(..., description="JSON path where relationship was extracted (e.g., 'meetingInfo.workgroup_id')")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440000",
                "subject_id": "990e8400-e29b-41d4-a716-446655440000",
                "subject_type": "Workgroup",
                "subject_name": "Archives Workgroup",
                "relationship": "held",
                "object_id": "880e8400-e29b-41d4-a716-446655440000",
                "object_type": "Meeting",
                "object_name": "Meeting Jan 08 2025",
                "source_meeting_id": "880e8400-e29b-41d4-a716-446655440000",
                "source_field": "meetingInfo.workgroup_id",
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


"""MeetingPerson junction entity model for many-to-many relationship."""

from typing import Optional
from uuid import UUID
from pydantic import Field

from src.models.base import BaseEntity


class MeetingPerson(BaseEntity):
    """
    MeetingPerson junction entity for many-to-many relationship between Meetings and People.
    
    This junction table enables bidirectional queries:
    - Find all meetings attended by a person
    - Find all people who attended a meeting
    """
    
    meeting_id: UUID = Field(..., description="Meeting foreign key")
    person_id: UUID = Field(..., description="Person foreign key")
    role: Optional[str] = Field(None, description="Person's role in meeting (e.g., 'host', 'documenter', 'participant')")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440000",
                "meeting_id": "990e8400-e29b-41d4-a716-446655440000",
                "person_id": "770e8400-e29b-41d4-a716-446655440000",
                "role": "participant",
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


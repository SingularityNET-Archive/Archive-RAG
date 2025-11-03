"""Tag entity model."""

from typing import Optional, List, Union
from uuid import UUID
from pydantic import Field

from src.models.base import BaseEntity


class Tag(BaseEntity):
    """
    Tag entity representing topic and emotional metadata for meetings.
    
    Tags belong to Meetings and contain topics covered and emotions
    associated with the meeting.
    """
    
    meeting_id: UUID = Field(..., description="Meeting foreign key")
    topics_covered: Optional[Union[str, List[str]]] = Field(None, description="Topics covered in meeting")
    emotions: Optional[Union[str, List[str]]] = Field(None, description="Emotional tone of meeting")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440000",
                "meeting_id": "990e8400-e29b-41d4-a716-446655440000",
                "topics_covered": ["budget", "planning", "strategy"],
                "emotions": ["collaborative", "friendly"],
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


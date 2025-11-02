"""MeetingRecord model for archived meeting JSON logs."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class MeetingRecord(BaseModel):
    """
    Meeting record model representing an archived meeting JSON log.
    
    Fields:
        id: Unique meeting identifier
        date: Meeting date and time (ISO 8601)
        participants: List of participant names or IDs
        transcript: Full meeting transcript text
        decisions: List of decisions made in meeting (optional)
        tags: Categorization tags for meeting (optional)
    """
    
    id: str = Field(..., description="Unique meeting identifier")
    date: str = Field(..., description="Meeting date and time (ISO 8601 format)")
    participants: List[str] = Field(..., description="List of participant names or IDs")
    transcript: str = Field(..., description="Full meeting transcript text")
    decisions: Optional[List[str]] = Field(default=None, description="List of decisions made in meeting")
    tags: Optional[List[str]] = Field(default=None, description="Categorization tags for meeting")
    
    @validator("transcript")
    def transcript_not_empty(cls, v):
        """Validate transcript is not empty."""
        if not v or not v.strip():
            raise ValueError("Transcript must not be empty")
        return v
    
    @validator("date")
    def validate_date_format(cls, v):
        """Validate date is ISO 8601 format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid ISO 8601 date format: {v}")
        return v
    
    @validator("participants")
    def participants_not_empty(cls, v):
        """Validate participants list is not empty."""
        if not v or len(v) == 0:
            raise ValueError("Participants list must not be empty")
        return v
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "meeting_001",
                "date": "2024-03-15T10:00:00Z",
                "participants": ["Alice", "Bob", "Charlie"],
                "transcript": "Meeting transcript text here...",
                "decisions": ["Decision 1", "Decision 2"],
                "tags": ["budget", "planning"]
            }
        }


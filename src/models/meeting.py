"""Meeting entity model."""

from datetime import datetime, date as date_type
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import Field, field_validator, HttpUrl

from src.models.base import BaseEntity


class MeetingType(str, Enum):
    """Meeting type enumeration."""
    MONTHLY = "Monthly"
    WEEKLY = "Weekly"
    BIWEEKLY = "Biweekly"
    CUSTOM = "Custom"
    STANDARD = "Standard"


class Meeting(BaseEntity):
    """
    Meeting entity representing a documented meeting event.
    
    Meetings belong to a workgroup and can have documents, agenda items,
    and tags. They also have many-to-many relationships with people via
    the MeetingPerson junction table.
    """
    
    workgroup_id: UUID = Field(..., description="Workgroup foreign key")
    meeting_type: Optional[MeetingType] = Field(None, description="Meeting type")
    date: date_type = Field(..., description="Meeting date (ISO 8601 format)")
    host_id: Optional[UUID] = Field(None, description="Meeting host foreign key (Person)")
    documenter_id: Optional[UUID] = Field(None, description="Meeting documenter foreign key (Person)")
    purpose: Optional[str] = Field(None, description="Meeting purpose")
    video_link: Optional[HttpUrl] = Field(None, description="Meeting video link")
    timestamped_video: Optional[Dict[str, Any]] = Field(None, description="Timestamped video data")
    no_summary_given: bool = Field(default=False, description="Flag indicating no summary provided")
    canceled_summary: bool = Field(default=False, description="Flag indicating summary was canceled")
    
    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> date_type:
        """Validate and normalize date format to ISO 8601."""
        if isinstance(v, date_type):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            # Try parsing ISO 8601 formats
            try:
                # Try date format YYYY-MM-DD
                return datetime.strptime(v[:10], "%Y-%m-%d").date()
            except ValueError:
                pass
            try:
                # Try ISO format
                return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
            except ValueError:
                raise ValueError(f"Invalid date format: {v}. Expected ISO 8601 date")
        raise ValueError(f"Invalid date type: {type(v)}. Expected date, datetime, or ISO 8601 string")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440000",
                "workgroup_id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "Monthly",
                "date": "2024-03-15",
                "host_id": "770e8400-e29b-41d4-a716-446655440000",
                "documenter_id": "880e8400-e29b-41d4-a716-446655440000",
                "purpose": "Monthly planning meeting",
                "video_link": "https://example.com/meeting/video",
                "no_summary_given": False,
                "canceled_summary": False,
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


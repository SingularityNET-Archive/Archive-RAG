"""AgendaItem entity model."""

from datetime import date
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import Field

from src.models.base import BaseEntity


class AgendaItemStatus(str, Enum):
    """Agenda item status enumeration."""
    CARRY_OVER = "carry over"
    COMPLETE = "complete"
    PENDING = "pending"
    IN_PROGRESS = "in progress"


class AgendaItem(BaseEntity):
    """
    AgendaItem entity representing topics or issues discussed in meetings.
    
    AgendaItems belong to meetings and can have multiple ActionItems
    and DecisionItems.
    """
    
    meeting_id: UUID = Field(..., description="Meeting foreign key")
    status: Optional[AgendaItemStatus] = Field(None, description="Agenda item status")
    narrative: Optional[str] = Field(None, description="Narrative text describing agenda item")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440000",
                "meeting_id": "660e8400-e29b-41d4-a716-446655440000",
                "status": "complete",
                "narrative": "Budget allocation discussion",
                "created_at": "2024-03-15T10:00:00Z",
            }
        }


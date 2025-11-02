"""ActionItem entity model."""

from datetime import date
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import Field

from src.models.base import BaseEntity


class ActionItemStatus(str, Enum):
    """Action item status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in progress"
    DONE = "done"
    CANCELLED = "cancelled"


class ActionItem(BaseEntity):
    """
    ActionItem entity representing tasks arising from meetings.
    
    ActionItems belong to AgendaItems and can be assigned to People.
    """
    
    agenda_item_id: UUID = Field(..., description="Agenda item foreign key")
    text: str = Field(..., description="Action item description", min_length=1, pattern="^.*[^\\s].*$")
    assignee_id: Optional[UUID] = Field(None, description="Person assigned to action item (foreign key)")
    due_date: Optional[date] = Field(None, description="Due date for action item")
    status: Optional[ActionItemStatus] = Field(None, description="Action item status")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440000",
                "agenda_item_id": "990e8400-e29b-41d4-a716-446655440000",
                "text": "Review budget proposal",
                "assignee_id": "770e8400-e29b-41d4-a716-446655440000",
                "due_date": "2024-04-01",
                "status": "todo",
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


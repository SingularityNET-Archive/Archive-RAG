"""Person entity model."""

from typing import Optional
from pydantic import Field

from src.models.base import BaseEntity


class Person(BaseEntity):
    """
    Person entity representing participants, hosts, and documenters.
    
    People attend meetings via many-to-many relationships (MeetingPerson)
    and can be assigned to action items.
    """
    
    display_name: str = Field(..., description="Person's display name", min_length=1, pattern="^.*[^\\s].*$")
    alias: Optional[str] = Field(None, description="Alternative name or alias")
    role: Optional[str] = Field(None, description="Person's role (e.g., 'host', 'documenter', 'participant')")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440000",
                "display_name": "Alice Smith",
                "alias": "alice",
                "role": "host",
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


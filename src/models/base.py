"""Base entity model pattern with UUID, created_at, updated_at fields."""

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """
    Base entity model with common fields for all entities.
    
    All entities extend this base class to ensure consistent
    id, created_at, and updated_at fields across the data model.
    """
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier (UUID)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.utcnow()
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


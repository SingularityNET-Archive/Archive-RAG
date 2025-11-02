"""Workgroup entity model."""

from pydantic import Field, field_validator

from src.models.base import BaseEntity


class Workgroup(BaseEntity):
    """
    Workgroup entity representing an organizational group.
    
    Workgroups contain meetings and optionally contain people via
    meeting attendance relationships.
    """
    
    name: str = Field(..., description="Workgroup name", min_length=1)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v or not v.strip():
            raise ValueError("Workgroup name must not be empty")
        return v.strip()
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Archives Workgroup",
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


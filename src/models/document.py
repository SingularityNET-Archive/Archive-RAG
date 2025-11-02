"""Document entity model."""

from typing import Optional
from uuid import UUID
from pydantic import Field, field_validator, HttpUrl

from src.models.base import BaseEntity


class Document(BaseEntity):
    """
    Document entity representing working documents or reference links.
    
    Documents belong to meetings and provide quick access to meeting-related
    resources. Links are validated on access, not during ingestion (FR-004).
    """
    
    meeting_id: UUID = Field(..., description="Meeting foreign key")
    title: str = Field(..., description="Document title", min_length=1, pattern="^.*[^\\s].*$")
    link: HttpUrl = Field(..., description="Document link/URL")
    
    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, v: str) -> str:
        """Strip whitespace from title."""
        if isinstance(v, str):
            return v.strip()
        return v


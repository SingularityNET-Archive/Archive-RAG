"""DecisionItem entity model."""

from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import Field

from src.models.base import BaseEntity


class DecisionEffect(str, Enum):
    """Decision effect scope enumeration."""
    AFFECTS_ONLY_THIS_WORKGROUP = "affectsOnlyThisWorkgroup"
    MAY_AFFECT_OTHER_PEOPLE = "mayAffectOtherPeople"


class DecisionItem(BaseEntity):
    """
    DecisionItem entity representing decisions and rationales from meetings.
    
    DecisionItems belong to AgendaItems and contain the decision text,
    rationale, and effect scope.
    """
    
    agenda_item_id: UUID = Field(..., description="Agenda item foreign key")
    decision: str = Field(..., description="Decision text (used for transcript extraction)", min_length=1, pattern="^.*[^\\s].*$")
    rationale: Optional[str] = Field(None, description="Rationale for decision")
    effect: Optional[DecisionEffect] = Field(None, description="Effect scope")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "dd0e8400-e29b-41d4-a716-446655440000",
                "agenda_item_id": "990e8400-e29b-41d4-a716-446655440000",
                "decision": "Approved budget increase of 10%",
                "rationale": "Based on increased operational costs and projected revenue growth",
                "effect": "mayAffectOtherPeople",
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z",
            }
        }


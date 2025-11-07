"""Issue report model for tracking incorrect or misleading bot responses."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from src.lib.logging import get_logger

logger = get_logger(__name__)


class IssueReport(BaseModel):
    """
    Issue report model for user-submitted reports about incorrect or misleading bot responses.
    
    Contains:
    - Query context (query text, response text, citations)
    - User feedback (description of what was incorrect)
    - Metadata (timestamp, user ID, message ID)
    - Spam detection flags
    """
    
    id: UUID = Field(..., description="Unique issue report identifier")
    query_text: str = Field(..., description="Original query text that triggered the response")
    response_text: str = Field(..., description="Bot response text that was reported")
    citations: List[dict] = Field(default_factory=list, description="Citations from the response")
    user_description: str = Field(..., description="User's description of what was incorrect or misleading")
    user_id: str = Field(..., description="Discord user ID who submitted the report")
    username: str = Field(..., description="Discord username who submitted the report")
    message_id: Optional[str] = Field(None, description="Discord message ID of the bot response")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the issue was reported")
    is_spam: bool = Field(default=False, description="Flag indicating if report was detected as spam")
    spam_reason: Optional[str] = Field(None, description="Reason for spam flag (e.g., 'duplicate', 'rapid_fire')")
    is_resolved: bool = Field(default=False, description="Whether the issue has been reviewed and resolved")
    admin_notes: Optional[str] = Field(None, description="Admin notes about the issue")
    resolved_at: Optional[datetime] = Field(None, description="When the issue was resolved")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440000",
                "query_text": "What decisions were made last January?",
                "response_text": "Based on the meeting records...",
                "citations": [
                    {
                        "meeting_id": "meeting_001",
                        "date": "2024-01-15",
                        "workgroup_name": "Archives WG"
                    }
                ],
                "user_description": "The response incorrectly stated that no decisions were made, but I know there was a decision about budget allocation.",
                "user_id": "123456789012345678",
                "username": "alice",
                "message_id": "987654321098765432",
                "timestamp": "2024-11-06T01:00:00Z",
                "is_spam": False,
                "spam_reason": None,
                "is_resolved": False,
                "admin_notes": None,
                "resolved_at": None
            }
        }



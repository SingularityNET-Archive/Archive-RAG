"""MeetingRecord model for archived meeting JSON logs."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class MeetingInfo(BaseModel):
    """Meeting information nested structure."""
    typeOfMeeting: Optional[str] = None
    date: str = Field(..., description="Meeting date (YYYY-MM-DD format)")
    host: Optional[str] = None
    documenter: Optional[str] = None
    peoplePresent: Optional[str] = None
    purpose: Optional[str] = None
    meetingVideoLink: Optional[str] = None
    workingDocs: Optional[List[Dict[str, str]]] = None
    timestampedVideo: Optional[Dict[str, Any]] = None


class AgendaItem(BaseModel):
    """Agenda item structure."""
    status: Optional[str] = None
    actionItems: Optional[List[Dict[str, Any]]] = None
    decisionItems: Optional[List[Dict[str, Any]]] = None


class TagsModel(BaseModel):
    """Tags structure."""
    topicsCovered: Optional[str] = None
    emotions: Optional[str] = None


class MeetingRecord(BaseModel):
    """
    Meeting record model representing an archived meeting JSON log.
    
    Supports both old format (id, date, participants, transcript) and
    new format (workgroup, workgroup_id, meetingInfo, agendaItems).
    """
    
    # New format fields
    workgroup: Optional[str] = None
    workgroup_id: Optional[str] = None
    meetingInfo: Optional[MeetingInfo] = None
    agendaItems: Optional[List[AgendaItem]] = None
    tags: Optional[TagsModel] = None  # TagsModel (new format) or converted from List[str] (legacy)
    type: Optional[str] = None
    noSummaryGiven: Optional[bool] = None
    canceledSummary: Optional[bool] = None
    
    # Legacy format fields (for backward compatibility)
    id: Optional[str] = None
    date: Optional[str] = None
    participants: Optional[List[str]] = None
    transcript: Optional[str] = None
    decisions: Optional[List[str]] = None
    
    @model_validator(mode='before')
    @classmethod
    def extract_standard_fields(cls, data):
        """Extract and normalize fields from new or legacy format."""
        if isinstance(data, dict):
            # Handle tags - convert legacy array format to object if needed
            if "tags" in data and isinstance(data["tags"], list):
                # Legacy format: convert array to TagsModel-compatible dict
                tags_list = data["tags"]
                data["tags"] = {
                    "topicsCovered": ", ".join(tags_list) if tags_list else None
                }
            
            # If new format (workgroup_id and meetingInfo present)
            if data.get("workgroup_id") and data.get("meetingInfo"):
                meeting_info = data["meetingInfo"]
                
                # Set id from workgroup_id
                if not data.get("id"):
                    data["id"] = data["workgroup_id"]
                
                # Set date from meetingInfo.date
                if not data.get("date") and meeting_info.get("date"):
                    # Convert YYYY-MM-DD to ISO 8601 format
                    date_str = meeting_info["date"]
                    if "T" not in date_str:
                        date_str = f"{date_str}T00:00:00Z"
                    data["date"] = date_str
                
                # Set participants from meetingInfo.peoplePresent
                if not data.get("participants") and meeting_info.get("peoplePresent"):
                    # Parse comma-separated string
                    people = [p.strip() for p in meeting_info["peoplePresent"].split(",")]
                    data["participants"] = people
                
                # Extract transcript from decisionItems
                if not data.get("transcript") and data.get("agendaItems"):
                    transcript_parts = []
                    for item in data["agendaItems"]:
                        if isinstance(item, dict) and item.get("decisionItems"):
                            for decision in item["decisionItems"]:
                                if isinstance(decision, dict):
                                    decision_text = decision.get("decision", "")
                                    if decision_text:
                                        transcript_parts.append(decision_text)
                    if transcript_parts:
                        data["transcript"] = " ".join(transcript_parts)
                
                # Extract decisions
                if not data.get("decisions") and data.get("agendaItems"):
                    decisions = []
                    for item in data["agendaItems"]:
                        if isinstance(item, dict) and item.get("decisionItems"):
                            for decision in item["decisionItems"]:
                                if isinstance(decision, dict):
                                    decision_text = decision.get("decision", "")
                                    if decision_text:
                                        decisions.append(decision_text)
                    if decisions:
                        data["decisions"] = decisions
        
        return data
    
    @field_validator("id", mode="before")
    @classmethod
    def ensure_id(cls, v):
        """Ensure id is present (from workgroup_id or legacy id)."""
        # This is handled in model_validator, so just return v
        return v
    
    @field_validator("date", mode="before")
    @classmethod
    def normalize_date(cls, v):
        """Normalize date format to ISO 8601."""
        if not v:
            return v
        
        # If already ISO 8601 format, return as is
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except (ValueError, AttributeError):
            pass
        
        # If YYYY-MM-DD format, convert to ISO 8601
        try:
            dt = datetime.strptime(v, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%dT00:00:00Z")
        except ValueError:
            pass
        
        # Try other formats
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).isoformat() + "Z"
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid date format: {v}. Expected ISO 8601 or YYYY-MM-DD")
    
    @field_validator("participants", mode="before")
    @classmethod
    def ensure_participants(cls, v):
        """Ensure participants are present (from meetingInfo.peoplePresent or legacy participants)."""
        # This is handled in model_validator, so just validate here
        if not v or (isinstance(v, list) and len(v) == 0):
            raise ValueError("Either 'participants' or 'meetingInfo.peoplePresent' must be provided")
        return v
    
    @field_validator("transcript", mode="before")
    @classmethod
    def ensure_transcript(cls, v):
        """Ensure transcript is not empty (from decisionItems or legacy transcript)."""
        # This is handled in model_validator, so just validate here
        if not v or not v.strip():
            raise ValueError("Transcript must not be empty (extracted from decisionItems or provided directly)")
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


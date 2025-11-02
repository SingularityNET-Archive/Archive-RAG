"""EvaluationCase model for benchmark test cases."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    """
    Evaluation case model representing a benchmark test case.
    
    Fields:
        case_id: Unique evaluation case identifier
        prompt: Test query prompt
        ground_truth: Expected answer content
        expected_citations: Expected citations in format [meeting_id | date | speaker]
        evaluation_metrics: Scoring results
        run_timestamp: Evaluation run timestamp
        model_version: LLM version used for evaluation
        embedding_version: Embedding model version used
    """
    
    case_id: str = Field(..., description="Unique evaluation case identifier")
    prompt: str = Field(..., description="Test query prompt")
    ground_truth: str = Field(..., description="Expected answer content")
    expected_citations: List[Dict[str, Any]] = Field(
        ...,
        description="Expected citations in format [meeting_id | date | speaker]"
    )
    evaluation_metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="Scoring results (citation_accuracy, factuality, hallucination_count, etc.)"
    )
    run_timestamp: Optional[str] = Field(None, description="Evaluation run timestamp (ISO 8601)")
    model_version: Optional[str] = Field(None, description="LLM version used for evaluation")
    embedding_version: Optional[str] = Field(None, description="Embedding model version used")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationCase":
        """Create from dictionary."""
        return cls(**data)
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "case_id": "case_001",
                "prompt": "What decisions were made about budget allocation?",
                "ground_truth": "The budget committee decided to allocate $100k to marketing.",
                "expected_citations": [
                    {
                        "meeting_id": "meeting_001",
                        "date": "2024-03-15",
                        "speaker": "Alice",
                        "excerpt": "budget allocation"
                    }
                ],
                "evaluation_metrics": {
                    "citation_accuracy": 1.0,
                    "factuality": 0.9,
                    "hallucination_count": 0
                },
                "run_timestamp": "2024-11-02T10:00:00Z",
                "model_version": "model-name-v1.0",
                "embedding_version": "all-MiniLM-L6-v2"
            }
        }


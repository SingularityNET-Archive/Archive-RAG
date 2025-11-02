"""BERTopic-lite alternative topic modeling service."""

from typing import List, Dict, Any, Optional

from ..lib.config import DEFAULT_NUM_TOPICS, DEFAULT_SEED
from ..lib.logging import get_logger

logger = get_logger(__name__)


class BERTopicModelingService:
    """Service for topic modeling using BERTopic (alternative method)."""
    
    def __init__(
        self,
        num_topics: int = DEFAULT_NUM_TOPICS,
        seed: int = DEFAULT_SEED,
        no_pii: bool = False
    ):
        """
        Initialize BERTopic modeling service.
        
        Args:
            num_topics: Number of topics to discover (default: 10)
            seed: Random seed for reproducibility (default: 42)
            no_pii: Skip PII detection and redaction (default: False)
        """
        self.num_topics = num_topics
        self.seed = seed
        self.no_pii = no_pii
        
        logger.info(
            "bertopic_initialized",
            num_topics=num_topics,
            seed=seed
        )
    
    def extract_topics(self, documents: List[str]) -> Dict[str, Any]:
        """
        Extract topics from documents using BERTopic.
        
        Note: This is a placeholder implementation. In production,
        you would install and use the bertopic library.
        
        Args:
            documents: List of document text strings
            
        Returns:
            Dictionary with topics, keywords, and metadata
        """
        logger.warning(
            "bertopic_not_available",
            message="BERTopic library not available. Install with: pip install bertopic"
        )
        
        # Fallback: Return placeholder structure
        topics = []
        for topic_id in range(self.num_topics):
            topics.append({
                "topic_id": topic_id,
                "keywords": [f"keyword_{i}" for i in range(10)],
                "word_probs": {}
            })
        
        return {
            "topics": topics,
            "method": "bertopic",
            "num_topics": self.num_topics,
            "note": "BERTopic not installed - placeholder output"
        }


def create_bertopic_modeling_service(
    num_topics: int = DEFAULT_NUM_TOPICS,
    seed: int = DEFAULT_SEED,
    no_pii: bool = False
) -> BERTopicModelingService:
    """
    Create a BERTopic modeling service instance.
    
    Args:
        num_topics: Number of topics to discover
        seed: Random seed for reproducibility
        no_pii: Skip PII detection and redaction
        
    Returns:
        BERTopicModelingService instance
    """
    return BERTopicModelingService(num_topics, seed, no_pii)


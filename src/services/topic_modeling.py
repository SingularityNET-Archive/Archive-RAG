"""Topic modeling service using gensim LDA."""

from typing import List, Dict, Any, Optional
import gensim
from gensim import corpora
from gensim.models import LdaModel
import numpy as np

from ..lib.config import DEFAULT_NUM_TOPICS, DEFAULT_TOPIC_METHOD, DEFAULT_SEED
from ..lib.pii_detection import create_pii_detector
from ..lib.logging import get_logger

logger = get_logger(__name__)


class TopicModelingService:
    """Service for topic modeling using gensim LDA."""
    
    def __init__(
        self,
        num_topics: int = DEFAULT_NUM_TOPICS,
        method: str = DEFAULT_TOPIC_METHOD,
        seed: int = DEFAULT_SEED,
        no_pii: bool = False
    ):
        """
        Initialize topic modeling service.
        
        Args:
            num_topics: Number of topics to discover (default: 10)
            method: Topic modeling method ("lda" or "bertopic", default: "lda")
            seed: Random seed for reproducibility (default: 42)
            no_pii: Skip PII detection and redaction (default: False)
        """
        self.num_topics = num_topics
        self.method = method
        self.seed = seed
        self.no_pii = no_pii
        self.pii_detector = None if no_pii else create_pii_detector()
        
        # Set random seeds for reproducibility
        np.random.seed(seed)
        
        logger.info(
            "topic_modeling_initialized",
            num_topics=num_topics,
            method=method,
            seed=seed
        )
    
    def extract_topics(self, documents: List[str]) -> Dict[str, Any]:
        """
        Extract topics from documents.
        
        Args:
            documents: List of document text strings
            
        Returns:
            Dictionary with topics, keywords, and metadata
        """
        if not documents:
            raise ValueError("No documents provided for topic modeling")
        
        # Preprocess documents
        processed_docs = []
        for doc in documents:
            # Redact PII if enabled
            if not self.no_pii and self.pii_detector:
                doc = self.pii_detector.redact(doc)
            
            # Simple tokenization (gensim will handle preprocessing)
            processed_docs.append(doc.split())
        
        # Create dictionary and corpus
        dictionary = corpora.Dictionary(processed_docs)
        dictionary.filter_extremes(no_below=2, no_above=0.5)  # Filter rare/common words
        corpus = [dictionary.doc2bow(doc) for doc in processed_docs]
        
        # Train LDA model
        lda_model = LdaModel(
            corpus=corpus,
            num_topics=self.num_topics,
            id2word=dictionary,
            random_state=self.seed,
            passes=10,
            alpha='auto',
            per_word_topics=True
        )
        
        # Extract topics
        topics = []
        for topic_id in range(self.num_topics):
            topic_words = lda_model.show_topic(topic_id, topn=10)
            keywords = [word for word, prob in topic_words]
            
            topics.append({
                "topic_id": topic_id,
                "keywords": keywords,
                "word_probs": {word: float(prob) for word, prob in topic_words}
            })
        
        logger.info(
            "topics_extracted",
            num_topics=self.num_topics,
            num_documents=len(documents)
        )
        
        return {
            "topics": topics,
            "method": self.method,
            "num_topics": self.num_topics,
            "timestamp": gensim.utils.to_unicode(gensim.__version__)
        }


def create_topic_modeling_service(
    num_topics: int = DEFAULT_NUM_TOPICS,
    method: str = DEFAULT_TOPIC_METHOD,
    seed: int = DEFAULT_SEED,
    no_pii: bool = False
) -> TopicModelingService:
    """
    Create a topic modeling service instance.
    
    Args:
        num_topics: Number of topics to discover
        method: Topic modeling method
        seed: Random seed for reproducibility
        no_pii: Skip PII detection and redaction
        
    Returns:
        TopicModelingService instance
    """
    return TopicModelingService(num_topics, method, seed, no_pii)


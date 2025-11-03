"""Embedding service using sentence-transformers."""

import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer

from ..lib.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_SEED
from ..lib.logging import get_logger
from ..lib.compliance import ConstitutionViolation

logger = get_logger(__name__)

# Global compliance checker instance
_compliance_checker = None


def _get_compliance_checker():
    """Get or create compliance checker instance."""
    global _compliance_checker
    if _compliance_checker is None:
        from ..services.compliance_checker import ComplianceChecker
        _compliance_checker = ComplianceChecker()
        # Enable monitoring by default for compliance checking
        _compliance_checker.enable_monitoring()
    return _compliance_checker


class EmbeddingService:
    """Service for generating embeddings using sentence-transformers."""
    
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        device: Optional[str] = None
    ):
        """
        Initialize embedding service.
        
        Args:
            model_name: Name of sentence-transformers model
            device: Device to use ("cpu" or "cuda", None for auto)
        """
        self.model_name = model_name
        # Loading model can take time - this is where the "hang" actually occurs
        self.model = SentenceTransformer(model_name, device=device)
        logger.debug("embedding_service_initialized", model_name=model_name)
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
            
        Raises:
            ConstitutionViolation: If compliance violation detected
        """
        # Check compliance before embedding
        checker = _get_compliance_checker()
        violations = checker.check_embedding_operations()
        if violations:
            # Fail-fast on first violation
            raise violations[0]
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Check compliance after embedding
        violations = checker.check_embedding_operations()
        if violations:
            raise violations[0]
        
        return embedding
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for encoding
            
        Returns:
            Numpy array of embedding vectors
            
        Raises:
            ConstitutionViolation: If compliance violation detected
        """
        # Check compliance before embedding
        checker = _get_compliance_checker()
        violations = checker.check_embedding_operations()
        if violations:
            # Fail-fast on first violation
            raise violations[0]
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        # Check compliance after embedding
        violations = checker.check_embedding_operations()
        if violations:
            raise violations[0]
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Get dimension of embedding vectors.
        
        Returns:
            Embedding dimension
        """
        return self.model.get_sentence_embedding_dimension()


def create_embedding_service(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    device: Optional[str] = None
) -> EmbeddingService:
    """
    Create an embedding service instance.
    
    Args:
        model_name: Name of sentence-transformers model
        device: Device to use
        
    Returns:
        EmbeddingService instance
    """
    return EmbeddingService(model_name, device)


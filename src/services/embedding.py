"""Embedding service using sentence-transformers."""

import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer

from ..lib.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_SEED
from ..lib.logging import get_logger

logger = get_logger(__name__)


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
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for encoding
            
        Returns:
            Numpy array of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False
        )
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


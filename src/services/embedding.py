"""Embedding service using sentence-transformers (local) or remote API (opt-in)."""

import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer

from ..lib.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_SEED
from ..lib.remote_config import get_embedding_remote_config
from ..lib.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using sentence-transformers (local) or remote API (opt-in)."""
    
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        device: Optional[str] = None,
        use_remote: Optional[bool] = None
    ):
        """
        Initialize embedding service.
        
        Args:
            model_name: Name of sentence-transformers model
            device: Device to use ("cpu" or "cuda", None for auto)
            use_remote: Force remote/local mode (None = auto-detect from env)
        """
        self.model_name = model_name
        self.device = device
        self._remote_service = None
        
        # Check if remote processing is enabled
        remote_enabled, api_url, api_key, remote_model = get_embedding_remote_config()
        if use_remote is None:
            use_remote = remote_enabled
        
        # Use remote model name if remote is enabled, otherwise use provided model_name
        effective_model_name = remote_model if use_remote and remote_model else model_name
        
        if use_remote and api_url:
            # Use remote embedding service (no fallback)
            try:
                from ..services.remote_embedding import RemoteEmbeddingService
                self._remote_service = RemoteEmbeddingService(
                    api_url=api_url,
                    api_key=api_key,
                    model_name=effective_model_name
                )
                logger.info("embedding_service_remote_initialized", model_name=effective_model_name, api_url=api_url)
                self.model = None  # No local model when using remote
            except ImportError:
                logger.error("remote_embedding_service_unavailable", api_url=api_url)
                raise RuntimeError(
                    f"Remote embedding service unavailable. "
                    f"Required dependencies not installed or API URL invalid: {api_url}"
                )
        else:
            # Use local embedding service (default, constitution-compliant)
            self.model = SentenceTransformer(model_name, device=device)
            self._remote_service = None  # No remote service when using local
            logger.debug("embedding_service_local_initialized", model_name=model_name, device=device)
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        
        Raises:
            RuntimeError: If remote embedding fails (no fallback to local)
        """
        if self._remote_service:
            try:
                return self._remote_service.embed_text(text)
            except Exception as e:
                logger.error(
                    "remote_embedding_failed",
                    error=str(e),
                    model=self.model_name,
                    api_url=getattr(self._remote_service, 'api_url', 'unknown')
                )
                raise RuntimeError(
                    f"Remote embedding failed: {e}\n"
                    f"Model: {self.model_name}\n"
                    f"Check your API configuration and ensure the model supports feature extraction. "
                    f"To use local embeddings instead, disable remote processing in your .env file."
                ) from e
        
        # Use local embedding service
        if self.model is None:
            raise RuntimeError("Local embedding model not initialized")
        
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
        
        Raises:
            RuntimeError: If remote embedding fails (no fallback to local)
        """
        if self._remote_service:
            try:
                return self._remote_service.embed_texts(texts, batch_size=batch_size)
            except Exception as e:
                logger.error(
                    "remote_embedding_failed",
                    error=str(e),
                    model=self.model_name,
                    batch_size=len(texts),
                    api_url=getattr(self._remote_service, 'api_url', 'unknown')
                )
                raise RuntimeError(
                    f"Remote embedding failed: {e}\n"
                    f"Model: {self.model_name}\n"
                    f"Check your API configuration and ensure the model supports feature extraction. "
                    f"To use local embeddings instead, disable remote processing in your .env file."
                ) from e
        
        # Use local embedding service
        if self.model is None:
            raise RuntimeError("Local embedding model not initialized")
        
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
        if self._remote_service:
            return self._remote_service.get_embedding_dimension()
        else:
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


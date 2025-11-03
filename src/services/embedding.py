"""Embedding service using sentence-transformers (local) or remote API (opt-in)."""

import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer

from ..lib.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_SEED
from ..lib.remote_config import get_embedding_remote_config
from ..lib.logging import get_logger
from ..lib.compliance import ConstitutionViolation

logger = get_logger(__name__)

def _get_compliance_checker():
    """Get singleton compliance checker instance."""
    from ..services.compliance_checker import get_compliance_checker
    return get_compliance_checker()


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
            ConstitutionViolation: If compliance violation detected
        """
        # Check compliance before embedding
        checker = _get_compliance_checker()
        violations = checker.check_embedding_operations()
        if violations:
            # Fail-fast on first violation
            raise violations[0]
        
        if self._remote_service:
            try:
                # Temporarily disable network monitoring during remote embedding
                # (Compliance already checked above, and monitoring can interfere with HTTP clients)
                # CRITICAL: The socket may have been monkey-patched by load_index() or other operations
                # We must ensure it's restored before making HTTP calls
                was_enabled = checker.enabled
                if was_enabled:
                    # Save monitoring state before disabling
                    checker.disable_monitoring()
                    # Force restore original socket (socket may have been monkey-patched earlier)
                    import socket
                    if hasattr(checker.network_monitor, '_original_socket') and checker.network_monitor._original_socket:
                        socket.socket = checker.network_monitor._original_socket
                try:
                    result = self._remote_service.embed_text(text)
                finally:
                    # Re-enable monitoring if it was enabled before
                    if was_enabled:
                        checker.enable_monitoring()
                
                # Check compliance after remote embedding
                violations = checker.check_embedding_operations()
                if violations:
                    raise violations[0]
                return result
            except Exception as e:
                # Get the actual remote model name from the remote service
                remote_model_name = getattr(self._remote_service, 'model_name', self.model_name)
                remote_api_url = getattr(self._remote_service, 'api_url', 'unknown')
                
                logger.error(
                    "remote_embedding_failed",
                    error=str(e),
                    local_model=self.model_name,
                    remote_model=remote_model_name,
                    api_url=remote_api_url
                )
                raise RuntimeError(
                    f"Remote embedding failed: {e}\n"
                    f"  Remote Model: {remote_model_name}\n"
                    f"  API URL: {remote_api_url}\n"
                    f"  Check your API configuration and ensure the model supports feature extraction.\n"
                    f"  To use local embeddings instead, disable remote processing in your .env file."
                ) from e
        
        # Use local embedding service
        if self.model is None:
            raise RuntimeError("Local embedding model not initialized")
        
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
            RuntimeError: If remote embedding fails (no fallback to local)
            ConstitutionViolation: If compliance violation detected
        """
        # Check compliance before embedding
        checker = _get_compliance_checker()
        violations = checker.check_embedding_operations()
        if violations:
            # Fail-fast on first violation
            raise violations[0]
        
        if self._remote_service:
            try:
                # Temporarily disable network monitoring during remote embedding
                # (Compliance already checked above, and monitoring can interfere with HTTP clients)
                # CRITICAL: The socket may have been monkey-patched by load_index() or other operations
                # We must ensure it's restored before making HTTP calls
                was_enabled = checker.enabled
                if was_enabled:
                    # Save monitoring state before disabling
                    checker.disable_monitoring()
                    # Force restore original socket (socket may have been monkey-patched earlier)
                    import socket
                    if hasattr(checker.network_monitor, '_original_socket') and checker.network_monitor._original_socket:
                        socket.socket = checker.network_monitor._original_socket
                try:
                    result = self._remote_service.embed_texts(texts, batch_size=batch_size)
                finally:
                    # Re-enable monitoring if it was enabled before
                    if was_enabled:
                        checker.enable_monitoring()
                
                # Check compliance after remote embedding
                violations = checker.check_embedding_operations()
                if violations:
                    raise violations[0]
                return result
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
        if self._remote_service:
            # For remote service, get_embedding_dimension() may call embed_text() internally
            # We need to ensure socket is restored if monitoring was enabled
            checker = _get_compliance_checker()
            was_enabled = checker.enabled
            if was_enabled:
                # Disable monitoring and restore socket before calling remote service
                checker.disable_monitoring()
                import socket
                if hasattr(checker.network_monitor, '_original_socket') and checker.network_monitor._original_socket:
                    socket.socket = checker.network_monitor._original_socket
            try:
                dim = self._remote_service.get_embedding_dimension()
            finally:
                # Re-enable monitoring if it was enabled before
                if was_enabled:
                    checker.enable_monitoring()
            return dim
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


"""Remote embedding service using API endpoints (optional, opt-in mode)."""

import numpy as np
import requests
from typing import List, Optional
import json

from ..lib.remote_config import get_embedding_remote_config, HUGGINGFACE_INFERENCE_URL, HUGGINGFACE_API_KEY
from ..lib.logging import get_logger

logger = get_logger(__name__)


class RemoteEmbeddingService:
    """Service for generating embeddings using remote API endpoints."""
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize remote embedding service.
        
        Args:
            api_url: Remote API URL (OpenAI, HuggingFace, or custom)
            api_key: API key for authentication
            model_name: Model name for embedding generation
        """
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model_name
        # Default dimension will be detected from first embedding call
        # Common defaults: 384 (MiniLM-L6-v2), 1536 (text-embedding-3-small)
        self.embedding_dimension = None  # Will be set after first embedding call
        
        # Determine API type from URL
        if api_url:
            if "openai" in api_url.lower():
                self.api_type = "openai"
            elif "huggingface" in api_url.lower() or api_url == HUGGINGFACE_INFERENCE_URL:
                self.api_type = "huggingface"
            else:
                self.api_type = "custom"
        else:
            # Default to HuggingFace if no URL provided
            self.api_type = "huggingface"
            self.api_url = HUGGINGFACE_INFERENCE_URL
        
        logger.info(
            "remote_embedding_service_initialized",
            api_type=self.api_type,
            model_name=model_name,
            api_url=api_url or "default"
        )
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text via remote API.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        """
        embeddings = self.embed_texts([text])
        return embeddings[0]
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts via remote API.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing (may be limited by API)
            
        Returns:
            Numpy array of embedding vectors
        """
        if self.api_type == "openai":
            return self._embed_openai(texts, batch_size=batch_size)
        elif self.api_type == "huggingface":
            return self._embed_huggingface(texts, batch_size=batch_size)
        else:
            return self._embed_custom(texts, batch_size=batch_size)
    
    def _embed_openai(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings using OpenAI API with retry logic."""
        import openai
        import time
        import httpx
        
        # Create a custom HTTP client with better connection settings
        # This helps with connection errors by configuring connection pooling,
        # timeouts, and retry behavior at the HTTP level
        http_client = httpx.Client(
            timeout=httpx.Timeout(120.0, connect=30.0),  # 2 min total, 30s connect
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            follow_redirects=True,
            verify=True  # SSL verification
        )
        
        # Create client with longer timeout and retries for connection issues
        # Normalize base_url: ensure it doesn't have trailing slash (OpenAI client handles it)
        base_url = (self.api_url.rstrip('/') + '/') if self.api_url else None
        
        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=120.0,  # 2 minute timeout for slow connections
            max_retries=0,  # We handle retries manually with better control
            http_client=http_client  # Use custom HTTP client with better connection handling
        )
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Retry logic with exponential backoff for connection errors
            max_attempts = 5
            retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            
            for attempt in range(max_attempts):
                try:
                    response = client.embeddings.create(
                        model=self.model_name,
                        input=batch
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    break  # Success, exit retry loop
                except openai.APIConnectionError as e:
                    # Connection errors (network issues, DNS, SSL, etc.)
                    if attempt < max_attempts - 1:
                        # Retry with exponential backoff
                        delay = retry_delays[attempt]
                        logger.warning(
                            "openai_embedding_connection_retry",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay=delay,
                            error=str(e)[:100]
                        )
                        time.sleep(delay)
                        continue  # Retry
                    else:
                        # Final attempt failed
                        error_msg = (
                            f"OpenAI API connection failed after {max_attempts} attempts: {e}\n"
                            f"  API URL: {self.api_url}\n"
                            f"  Model: {self.model_name}\n"
                            f"  Troubleshooting:\n"
                            f"    - Check internet connectivity\n"
                            f"    - Verify API URL is correct: {self.api_url}\n"
                            f"    - Check firewall/proxy settings\n"
                            f"    - Verify API key is valid (starts with 'sk-')\n"
                            f"    - Ensure model '{self.model_name}' is valid for OpenAI API\n"
                            f"    - Test connection: curl -v https://api.openai.com\n"
                            f"    - Check OpenAI status: https://status.openai.com\n"
                            f"    - For OpenAI, use models like 'text-embedding-3-small' or 'text-embedding-3-large'"
                        )
                        logger.error("openai_embedding_connection_failed", 
                                   error=str(e), 
                                   api_url=self.api_url,
                                   model=self.model_name,
                                   api_key_present=bool(self.api_key),
                                   attempts=max_attempts)
                        # Clean up HTTP client before raising
                        try:
                            http_client.close()
                        except Exception:
                            pass
                        raise RuntimeError(error_msg) from e
                except openai.APIError as e:
                    # API errors (authentication, rate limits, etc.) - don't retry, raise immediately
                    error_str = str(e)
                    status_code = getattr(e, 'status_code', None)
                    
                    # Check for quota errors (429)
                    if status_code == 429 or "429" in error_str or "insufficient_quota" in error_str.lower() or "quota" in error_str.lower():
                        logger.warning(
                            "openai_embedding_quota_exceeded",
                            error=error_str,
                            batch_size=len(batch),
                            status_code=status_code,
                            suggestion="OpenAI quota exceeded for embeddings. Check billing or usage limits."
                        )
                    # Check for authentication errors (401)
                    elif status_code == 401 or "401" in error_str or "unauthorized" in error_str.lower() or "invalid api key" in error_str.lower():
                        error_msg = (
                            f"OpenAI API authentication failed: {e}\n"
                            f"  API URL: {self.api_url}\n"
                            f"  Troubleshooting:\n"
                            f"    - Verify API key is correct and active\n"
                            f"    - Check API key format (should start with 'sk-')\n"
                            f"    - Ensure API key has permissions for embeddings API\n"
                            f"    - Check OpenAI account status and billing"
                        )
                        logger.error("openai_embedding_auth_failed", 
                                   error=error_str,
                                   api_url=self.api_url,
                                   api_key_present=bool(self.api_key),
                                   status_code=status_code)
                        # Clean up HTTP client before raising
                        try:
                            http_client.close()
                        except Exception:
                            pass
                        raise RuntimeError(error_msg) from e
                    else:
                        logger.error("openai_embedding_api_failed", 
                                   error=error_str, 
                                   batch_size=len(batch),
                                   status_code=status_code,
                                   model=self.model_name)
                    raise  # Don't retry API errors
                except Exception as e:
                    # Other unexpected errors - don't retry, raise immediately
                    error_str = str(e)
                    error_type = type(e).__name__
                    error_msg = (
                        f"Unexpected error during OpenAI embedding: {error_type}: {error_str}\n"
                        f"  API URL: {self.api_url}\n"
                        f"  Model: {self.model_name}\n"
                        f"  Batch size: {len(batch)}"
                    )
                    logger.error("openai_embedding_unexpected_error", 
                               error=error_str,
                               error_type=error_type,
                               api_url=self.api_url,
                               model=self.model_name,
                               batch_size=len(batch))
                    # Clean up HTTP client
                    try:
                        http_client.close()
                    except Exception:
                        pass
                    raise RuntimeError(error_msg) from e
        
        # Clean up HTTP client on success
        try:
            http_client.close()
        except Exception:
            pass
        
        # Determine dimension from first embedding
        if all_embeddings:
            self.embedding_dimension = len(all_embeddings[0])
            logger.debug("openai_embedding_dimension_detected", dimension=self.embedding_dimension, model=self.model_name)
        
        # Convert to numpy array and ensure float32 (required by FAISS)
        embeddings_array = np.array(all_embeddings, dtype=np.float32)
        
        return embeddings_array
    
    def _embed_huggingface(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings using HuggingFace Inference API."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                # HuggingFace Inference Providers API format (migrated from deprecated api-inference.huggingface.co)
                # URL format: https://router.huggingface.co/hf-inference/models/{model_name}
                # Remove any existing /models or /pipeline path from api_url
                base_url = self.api_url.rstrip('/')
                if '/models' in base_url:
                    # If api_url already contains /models, use as-is
                    model_url = f"{base_url}"
                elif '/pipeline' in base_url:
                    # Replace /pipeline/feature-extraction with /models
                    model_url = base_url.replace('/pipeline/feature-extraction', '/models')
                    model_url = model_url.rstrip('/') + f"/{self.model_name}"
                else:
                    # Standard format: append /models/{model_name}
                    model_url = f"{base_url}/models/{self.model_name}"
                
                # For sentence-transformers models on HuggingFace Inference API:
                # - Many are configured as SentenceSimilarityPipeline (need source_sentence + sentences)
                # - For embeddings, we need to use the underlying transformer model
                # - Try using feature-extraction task or underlying model
                
                # Use "inputs" parameter (required by HuggingFace Inference API)
                # The model should support feature-extraction task
                payload = {"inputs": batch}
                
                response = requests.post(
                    model_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                # Handle 503 (model loading) - wait and retry once
                if response.status_code == 503:
                    import time
                    logger.warning("huggingface_model_loading", model=self.model_name, wait_seconds=10)
                    time.sleep(10)  # Wait for model to load
                    response = requests.post(
                        model_url,
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                
                # Log error details before raising
                if response.status_code >= 400:
                    error_text = response.text[:500] if response.text else "No error message"
                    logger.error(
                        "huggingface_api_error",
                        status_code=response.status_code,
                        error=error_text,
                        url=model_url,
                        batch_size=len(batch)
                    )
                    
                    # If 400 error suggests model doesn't support feature extraction,
                    # suggest using local processing instead
                    if response.status_code == 400 and "SentenceSimilarityPipeline" in error_text:
                        logger.warning(
                            "huggingface_model_not_supporting_feature_extraction",
                            model=self.model_name,
                            suggestion="Model is configured for similarity, not feature extraction. Consider using local sentence-transformers instead."
                        )
                
                response.raise_for_status()
                result = response.json()
                
                # HuggingFace Inference API returns embeddings as a list of lists
                # Each input text becomes a list of floats (embedding vector)
                if isinstance(result, list):
                    # Batch response: list of embeddings
                    # Each element is a list of floats representing one embedding
                    all_embeddings.extend(result)
                elif isinstance(result, dict) and "embeddings" in result:
                    # Some APIs wrap in {"embeddings": [...]}
                    all_embeddings.extend(result["embeddings"])
                else:
                    # Single embedding (shouldn't happen, but handle it)
                    all_embeddings.append(result if isinstance(result, list) else [result])
            except Exception as e:
                logger.error("huggingface_embedding_failed", error=str(e), batch_size=len(batch))
                raise
        
        # Determine dimension from first embedding
        if all_embeddings:
            self.embedding_dimension = len(all_embeddings[0])
            logger.debug("openai_embedding_dimension_detected", dimension=self.embedding_dimension, model=self.model_name)
        
        # Convert to numpy array and ensure float32 (required by FAISS)
        embeddings_array = np.array(all_embeddings, dtype=np.float32)
        
        return embeddings_array
    
    def _embed_custom(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings using custom API endpoint."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                # Custom API format: POST with JSON body
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json={"texts": batch, "model": self.model_name},
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                
                # Expect {"embeddings": [[...], [...]]} format
                batch_embeddings = result.get("embeddings", result)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error("custom_embedding_failed", error=str(e), batch_size=len(batch))
                raise
        
        # Determine dimension from first embedding
        if all_embeddings:
            self.embedding_dimension = len(all_embeddings[0])
            logger.debug("openai_embedding_dimension_detected", dimension=self.embedding_dimension, model=self.model_name)
        
        # Convert to numpy array and ensure float32 (required by FAISS)
        embeddings_array = np.array(all_embeddings, dtype=np.float32)
        
        return embeddings_array
    
    def get_embedding_dimension(self) -> int:
        """
        Get dimension of embedding vectors.
        
        Returns:
            Embedding dimension
        
        Raises:
            ValueError: If dimension not yet determined (no embeddings generated yet)
        """
        if self.embedding_dimension is None:
            # Try to determine dimension by making a test call
            try:
                test_embedding = self.embed_text("test")
                self.embedding_dimension = len(test_embedding)
                logger.debug("embedding_dimension_determined_from_test", dimension=self.embedding_dimension)
            except Exception as e:
                # If test fails, use model-specific defaults
                if "text-embedding-3-small" in self.model_name.lower():
                    self.embedding_dimension = 1536
                    logger.debug("using_default_dimension_for_model", model=self.model_name, dimension=self.embedding_dimension)
                elif "text-embedding-3-large" in self.model_name.lower():
                    self.embedding_dimension = 3072
                    logger.debug("using_default_dimension_for_model", model=self.model_name, dimension=self.embedding_dimension)
                else:
                    # Default fallback
                    self.embedding_dimension = 384
                    logger.warning("using_fallback_dimension", model=self.model_name, dimension=self.embedding_dimension)
        
        return self.embedding_dimension


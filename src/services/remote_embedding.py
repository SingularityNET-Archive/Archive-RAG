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
        self.embedding_dimension = 384  # Default for MiniLM-L6-v2
        
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
            return self._embed_openai(texts)
        elif self.api_type == "huggingface":
            return self._embed_huggingface(texts)
        else:
            return self._embed_custom(texts)
    
    def _embed_openai(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using OpenAI API."""
        import openai
        
        client = openai.OpenAI(api_key=self.api_key, base_url=self.api_url or None)
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = client.embeddings.create(
                    model=self.model_name,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error("openai_embedding_failed", error=str(e), batch_size=len(batch))
                raise
        
        # Determine dimension from first embedding
        if all_embeddings:
            self.embedding_dimension = len(all_embeddings[0])
        
        return np.array(all_embeddings)
    
    def _embed_huggingface(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using HuggingFace Inference API."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                # HuggingFace inference API format
                response = requests.post(
                    f"{self.api_url}/pipeline/feature-extraction/{self.model_name}",
                    headers=headers,
                    json={"inputs": batch},
                    timeout=60
                )
                response.raise_for_status()
                batch_embeddings = response.json()
                
                # Handle single vs batch response
                if isinstance(batch_embeddings[0], list):
                    all_embeddings.extend(batch_embeddings)
                else:
                    all_embeddings.append(batch_embeddings)
            except Exception as e:
                logger.error("huggingface_embedding_failed", error=str(e), batch_size=len(batch))
                raise
        
        # Determine dimension from first embedding
        if all_embeddings:
            self.embedding_dimension = len(all_embeddings[0])
        
        return np.array(all_embeddings)
    
    def _embed_custom(self, texts: List[str]) -> np.ndarray:
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
        
        return np.array(all_embeddings)
    
    def get_embedding_dimension(self) -> int:
        """
        Get dimension of embedding vectors.
        
        Returns:
            Embedding dimension
        """
        return self.embedding_dimension


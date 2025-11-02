"""Remote LLM service using API endpoints (optional, opt-in mode)."""

import requests
from typing import List, Dict, Any, Optional
import json

from ..lib.remote_config import get_llm_remote_config, HUGGINGFACE_INFERENCE_URL, HUGGINGFACE_API_KEY
from ..lib.logging import get_logger

logger = get_logger(__name__)


class RemoteLLMService:
    """Service for generating text using remote LLM API endpoints."""
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: str = "gpt-3.5-turbo"
    ):
        """
        Initialize remote LLM service.
        
        Args:
            api_url: Remote API URL (OpenAI, HuggingFace, or custom)
            api_key: API key for authentication
            model_name: Model name for text generation
        """
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model_name
        
        # Determine API type from URL
        if api_url:
            if "openai" in api_url.lower():
                self.api_type = "openai"
            elif "huggingface" in api_url.lower() or api_url == HUGGINGFACE_INFERENCE_URL:
                self.api_type = "huggingface"
            else:
                self.api_type = "custom"
        else:
            # Default to OpenAI format if no URL provided
            self.api_type = "openai"
        
        logger.info(
            "remote_llm_service_initialized",
            api_type=self.api_type,
            model_name=model_name,
            api_url=api_url or "default"
        )
    
    def generate(
        self,
        prompt: str,
        max_length: int = 200,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text from prompt via remote API.
        
        Args:
            prompt: Input prompt text
            max_length: Maximum length of generated text
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Generated text
        """
        if self.api_type == "openai":
            return self._generate_openai(prompt, max_length, temperature)
        elif self.api_type == "huggingface":
            return self._generate_huggingface(prompt, max_length, temperature)
        else:
            return self._generate_custom(prompt, max_length, temperature)
    
    def _generate_openai(self, prompt: str, max_length: int, temperature: float) -> str:
        """Generate text using OpenAI API."""
        import openai
        
        client = openai.OpenAI(api_key=self.api_key, base_url=self.api_url or None)
        
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on meeting records."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("openai_generation_failed", error=str(e))
            raise
    
    def _generate_huggingface(self, prompt: str, max_length: int, temperature: float) -> str:
        """Generate text using HuggingFace Inference API."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.post(
                f"{HUGGINGFACE_INFERENCE_URL}/models/{self.model_name}",
                headers=headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_length,
                        "temperature": temperature,
                        "return_full_text": False
                    }
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle HuggingFace response format
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    return result[0]["generated_text"].strip()
                elif isinstance(result[0], str):
                    return result[0].strip()
            return str(result).strip()
        except Exception as e:
            logger.error("huggingface_generation_failed", error=str(e))
            raise
    
    def _generate_custom(self, prompt: str, max_length: int, temperature: float) -> str:
        """Generate text using custom API endpoint."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json={
                    "prompt": prompt,
                    "model": self.model_name,
                    "max_length": max_length,
                    "temperature": temperature
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            
            # Expect {"text": "..."} or {"generated_text": "..."} format
            return result.get("text", result.get("generated_text", str(result))).strip()
        except Exception as e:
            logger.error("custom_generation_failed", error=str(e))
            raise


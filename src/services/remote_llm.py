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
        import httpx
        import time
        
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
        
        # Retry logic with exponential backoff for connection errors
        max_attempts = 5
        retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
        
        for attempt in range(max_attempts):
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
                # Clean up HTTP client on success
                try:
                    http_client.close()
                except Exception:
                    pass
                return response.choices[0].message.content.strip()
            except openai.APIConnectionError as e:
                # Connection errors (network issues, DNS, SSL, etc.)
                if attempt < max_attempts - 1:
                    # Retry with exponential backoff
                    delay = retry_delays[attempt]
                    logger.warning(
                        "openai_llm_connection_retry",
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
                        f"    - Test connection: curl -v {self.api_url or 'https://api.openai.com/v1'}\n"
                        f"    - Check OpenAI status: https://status.openai.com"
                    )
                    logger.error("openai_llm_connection_failed", 
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
                        "openai_llm_quota_exceeded",
                        error=error_str,
                        status_code=status_code,
                        suggestion="OpenAI quota exceeded. Falling back to template-based generation."
                    )
                # Check for authentication errors (401)
                elif status_code == 401 or "401" in error_str or "unauthorized" in error_str.lower() or "invalid api key" in error_str.lower():
                    error_msg = (
                        f"OpenAI API authentication failed: {e}\n"
                        f"  API URL: {self.api_url}\n"
                        f"  Troubleshooting:\n"
                        f"    - Verify API key is correct and active\n"
                        f"    - Check API key format (should start with 'sk-')\n"
                        f"    - Ensure API key has permissions for chat completions API\n"
                        f"    - Check OpenAI account status and billing"
                    )
                    logger.error("openai_llm_auth_failed", 
                               error=error_str,
                               api_url=self.api_url,
                               api_key_present=bool(self.api_key),
                               status_code=status_code)
                
                # Clean up HTTP client before raising
                try:
                    http_client.close()
                except Exception:
                    pass
                raise RuntimeError(error_str) from e
            except Exception as e:
                # Unexpected errors
                error_str = str(e)
                error_type = type(e).__name__
                error_msg = (
                    f"Unexpected error during OpenAI LLM generation: {error_type}: {error_str}\n"
                    f"  API URL: {self.api_url}\n"
                    f"  Model: {self.model_name}"
                )
                logger.error("openai_llm_unexpected_error", 
                           error=error_str,
                           error_type=error_type,
                           api_url=self.api_url,
                           model=self.model_name)
                # Clean up HTTP client
                try:
                    http_client.close()
                except Exception:
                    pass
                raise RuntimeError(error_msg) from e
    
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
            # Handle 503 (model loading) - wait and retry once
            if response.status_code == 503:
                import time
                logger.warning("huggingface_model_loading", model=self.model_name, wait_seconds=10)
                time.sleep(10)  # Wait for model to load
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
            
            # Log error details before raising
            if response.status_code >= 400:
                error_text = response.text[:500] if response.text else "No error message"
                logger.error(
                    "huggingface_api_error",
                    status_code=response.status_code,
                    error=error_text,
                    url=f"{HUGGINGFACE_INFERENCE_URL}/models/{self.model_name}",
                    model=self.model_name
                )
                
                # If 404, suggest model might not exist or URL is wrong
                if response.status_code == 404:
                    logger.warning(
                        "huggingface_model_not_found",
                        model=self.model_name,
                        suggestion="Model not found on HuggingFace Inference API. Check model name or use a different model."
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


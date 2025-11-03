"""RAG generation service using LLM with retrieved context (local or remote, opt-in)."""

from typing import List, Dict, Any, Optional
import torch

from ..lib.config import DEFAULT_SEED
from ..lib.remote_config import get_llm_remote_config
from ..lib.logging import get_logger
from ..lib.compliance import ConstitutionViolation

logger = get_logger(__name__)

def _get_compliance_checker():
    """Get singleton compliance checker instance."""
    from ..services.compliance_checker import get_compliance_checker
    return get_compliance_checker()


class RAGGenerator:
    """Service for generating answers using LLM with retrieved context (local or remote, opt-in)."""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        seed: int = DEFAULT_SEED,
        use_remote: Optional[bool] = None
    ):
        """
        Initialize RAG generator.
        
        Args:
            model_name: Name of LLM model (default: use local model if available)
            device: Device to use ("cpu" or "cuda", None for auto)
            seed: Random seed for reproducibility
            use_remote: Force remote/local mode (None = auto-detect from env)
        """
        self.model_name = model_name or "gpt2"  # Default fallback
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu") if torch else "cpu"
        self.seed = seed
        self._remote_service = None
        self.generator = None
        self.tokenizer = None
        self.model = None
        
        # Check if remote processing is enabled
        remote_enabled, api_url, api_key, remote_model = get_llm_remote_config()
        if use_remote is None:
            use_remote = remote_enabled
        
        if use_remote and api_url:
            # Use remote LLM service
            try:
                from ..services.remote_llm import RemoteLLMService
                self._remote_service = RemoteLLMService(
                    api_url=api_url,
                    api_key=api_key,
                    model_name=model_name or remote_model
                )
                logger.info("rag_generator_remote_initialized", model_name=model_name or remote_model, api_url=api_url)
            except ImportError:
                logger.warning("remote_llm_service_unavailable", fallback="local")
                use_remote = False
        
        if not use_remote:
            # Use local LLM service (default, constitution-compliant)
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
                
                # Set random seed
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
                
                try:
                    # Only try to load if a specific model is requested
                    if model_name and model_name != "gpt2":
                        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                        self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
                        self.model.to(self.device)
                        self.model.eval()
                        
                        # Create text generation pipeline
                        self.generator = pipeline(
                            "text-generation",
                            model=self.model,
                            tokenizer=self.tokenizer,
                            device=0 if self.device == "cuda" else -1
                        )
                        
                        logger.debug(
                            "rag_generator_local_initialized",
                            model_name=self.model_name,
                            device=self.device
                        )
                    else:
                        # Default: use template-based generation (faster, no model loading)
                        self.generator = None
                        logger.debug("rag_generator_using_template", reason="No specific model requested")
                except Exception as e:
                    logger.debug(
                        "model_loading_failed_fallback",
                        model_name=self.model_name,
                        error=str(e)
                    )
                    self.generator = None
            except ImportError:
                logger.debug("transformers_not_available", fallback="template")
                self.generator = None
    
    def generate(
        self,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        max_length: int = 200
    ) -> str:
        """
        Generate answer from query and retrieved context.
        
        Args:
            query: User query text
            retrieved_context: List of retrieved chunks with metadata
            max_length: Maximum length of generated text
        
        Returns:
            Generated answer text
            
        Raises:
            ConstitutionViolation: If compliance violation detected
        """
        # Check compliance before generation
        checker = _get_compliance_checker()
        violations = checker.check_llm_operations()
        if violations:
            # Fail-fast on first violation
            raise violations[0]
        try:
            # Assemble context from retrieved chunks
            context_text = "\n\n".join([
                f"[Meeting: {chunk.get('meeting_id', 'unknown')}]\n{chunk.get('text', '')}"
                for chunk in retrieved_context
            ])
            
            # Create prompt
            prompt = f"""Based on the following meeting records, answer the question.

Meeting Records:
{context_text}

Question: {query}

Answer:"""
            
            # Use remote service if available
            if self._remote_service:
                try:
                    # Temporarily disable network monitoring during remote LLM generation
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
                        answer = self._remote_service.generate(prompt, max_length=max_length)
                    finally:
                        # Re-enable monitoring if it was enabled before
                        if was_enabled:
                            checker.enable_monitoring()
                    
                    logger.info("answer_generated_remote", query=query[:50], answer_length=len(answer))
                    # Check compliance after remote generation
                    violations = checker.check_llm_operations()
                    if violations:
                        raise violations[0]
                    return answer
                except Exception as e:
                    error_str = str(e)
                    # Check for quota errors and log as warning
                    if "429" in error_str or "insufficient_quota" in error_str.lower() or "quota" in error_str.lower():
                        logger.warning(
                            "remote_generation_quota_exceeded",
                            error=error_str,
                            fallback="template",
                            suggestion="OpenAI quota exceeded. Using template-based generation."
                        )
                    else:
                        logger.error("remote_generation_failed", error=error_str, fallback="template")
                    # Fallback to template
                    answer = self._template_generate(query, retrieved_context)
            elif self.generator:
                # Use local LLM generation
                try:
                    outputs = self.generator(
                        prompt,
                        max_length=max_length,
                        num_return_sequences=1,
                        temperature=0.7,
                        do_sample=True,
                        truncation=True,
                        pad_token_id=self.tokenizer.eos_token_id if hasattr(self.tokenizer, 'eos_token_id') else None
                    )
                    answer = outputs[0]["generated_text"].split("Answer:")[-1].strip()
                except Exception as e:
                    logger.debug("generation_failed_fallback", error=str(e))
                    # Fallback to template
                    answer = self._template_generate(query, retrieved_context)
            else:
                # Use template-based generation (default for small datasets)
                answer = self._template_generate(query, retrieved_context)
            
            # Check compliance after generation
            violations = checker.check_llm_operations()
            if violations:
                raise violations[0]
            
            logger.info("answer_generated", query=query[:50], answer_length=len(answer))
            
            return answer
        except ConstitutionViolation:
            raise
        except Exception as e:
            logger.error("generation_failed", query=query[:50], error=str(e))
            raise
    
    def _template_generate(
        self,
        query: str,
        retrieved_context: List[Dict[str, Any]]
    ) -> str:
        """
        Template-based answer generation (fallback).
        
        Args:
            query: User query text
            retrieved_context: List of retrieved chunks
            
        Returns:
            Generated answer text
        """
        if not retrieved_context:
            return "I could not find any relevant information in the meeting records."
        
        # Extract relevant text from chunks and format as answer
        relevant_texts = []
        for chunk in retrieved_context[:3]:  # Use top 3 chunks
            text = chunk.get("text", "").strip()
            if text:
                # Extract key sentences or summarize
                sentences = text.split('. ')
                if len(sentences) > 2:
                    # Take first and last sentences for context
                    relevant_texts.append(sentences[0] + '. ' + sentences[-1] + '.')
                else:
                    relevant_texts.append(text)
        
        if not relevant_texts:
            return "I could not find any relevant information in the meeting records."
        
        # Format as answer
        answer = "Based on the meeting records, " + " ".join(relevant_texts[:2])
        
        return answer


def create_rag_generator(
    model_name: Optional[str] = None,
    device: Optional[str] = None,
    seed: int = DEFAULT_SEED
) -> RAGGenerator:
    """
    Create a RAG generator instance.
    
    Args:
        model_name: Name of LLM model
        device: Device to use
        seed: Random seed for reproducibility
        
    Returns:
        RAGGenerator instance
    """
    return RAGGenerator(model_name, device, seed)


"""RAG generation service using LLM with retrieved context."""

from typing import List, Dict, Any, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

from ..lib.config import DEFAULT_SEED
from ..lib.logging import get_logger

logger = get_logger(__name__)


class RAGGenerator:
    """Service for generating answers using LLM with retrieved context."""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        seed: int = DEFAULT_SEED
    ):
        """
        Initialize RAG generator.
        
        Args:
            model_name: Name of LLM model (default: use local model if available)
            device: Device to use ("cpu" or "cuda", None for auto)
            seed: Random seed for reproducibility
        """
        self.model_name = model_name or "gpt2"  # Default fallback
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.seed = seed
        
        # Set random seed
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        
        try:
            # Try to load model, but don't fail if unavailable
            # For offline/local use, we'll use template-based generation as default
            if model_name and model_name != "gpt2":
                # Only try to load if a specific model is requested
                try:
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
                        "rag_generator_initialized",
                        model_name=self.model_name,
                        device=self.device
                    )
                except Exception as e:
                    logger.debug(
                        "model_loading_failed_fallback",
                        model_name=self.model_name,
                        error=str(e)
                    )
                    self.generator = None
            else:
                # Default: use template-based generation (faster, no model loading)
                self.generator = None
                logger.debug("rag_generator_using_template", reason="No specific model requested")
        except Exception as e:
            logger.debug(
                "rag_generator_init_error",
                error=str(e)
            )
            # Fallback to template-based generation
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
        """
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
        
        if self.generator:
            # Use LLM generation
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
        
        logger.info("answer_generated", query=query[:50], answer_length=len(answer))
        
        return answer
    
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


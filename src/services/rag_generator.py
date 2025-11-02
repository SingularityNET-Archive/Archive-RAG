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
            # Load tokenizer and model
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
            
            logger.info(
                "rag_generator_initialized",
                model_name=self.model_name,
                device=self.device
            )
        except Exception as e:
            logger.warning(
                "model_loading_failed",
                model_name=self.model_name,
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
                    pad_token_id=self.tokenizer.eos_token_id
                )
                answer = outputs[0]["generated_text"].split("Answer:")[-1].strip()
            except Exception as e:
                logger.error("generation_failed", error=str(e))
                # Fallback to template
                answer = self._template_generate(query, retrieved_context)
        else:
            # Use template-based generation
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
        
        # Extract relevant text from chunks
        relevant_texts = [chunk.get("text", "") for chunk in retrieved_context[:3]]
        answer = f"Based on the meeting records:\n\n" + "\n\n".join(relevant_texts[:2])
        
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


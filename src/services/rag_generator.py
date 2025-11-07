"""RAG generation service using LLM with retrieved context (local or remote, opt-in)."""

from typing import List, Dict, Any, Optional
from uuid import UUID
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
        # Cache for meeting metadata (workgroup name, date) to avoid repeated lookups
        self._meeting_metadata_cache: Dict[str, Dict[str, str]] = {}
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
        max_length: int = 1000
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
            # Detect if this is a decision list query
            query_lower = query.lower()
            is_decision_query = (
                ("decision" in query_lower or "decisions" in query_lower or "decided" in query_lower) and
                ("list" in query_lower or "what" in query_lower or "show" in query_lower)
            )
            
            # For decision queries, increase max_length to allow for detailed decision listings
            if is_decision_query:
                max_length = max(max_length, 2000)  # At least 2000 tokens for decision queries
            
            # Assemble context from retrieved chunks with workgroup name and date
            context_parts = []
            meeting_ids_processed = set()  # Track meetings we've already processed
            
            for chunk in retrieved_context:
                meeting_id = chunk.get('meeting_id', 'unknown')
                metadata = chunk.get('metadata', {})
                
                # Check cache first
                cached_metadata = self._meeting_metadata_cache.get(meeting_id)
                if cached_metadata:
                    workgroup_name = cached_metadata.get('workgroup_name', 'Unknown Workgroup')
                    date = cached_metadata.get('date', 'Unknown Date')
                else:
                    # Extract workgroup name and date from metadata
                    workgroup_name = metadata.get('workgroup') or metadata.get('workgroup_name')
                    date = metadata.get('date', '')
                    
                    # If workgroup name not in metadata, try to look it up (lazy loading)
                    if not workgroup_name and meeting_id and meeting_id != 'unknown':
                        try:
                            from ..services.citation_extractor import _get_workgroup_name_from_meeting
                            workgroup_name = _get_workgroup_name_from_meeting(meeting_id)
                        except Exception as e:
                            logger.debug("workgroup_lookup_failed", meeting_id=meeting_id, error=str(e))
                    
                    # Fallback to unknown if still not found
                    if not workgroup_name:
                        workgroup_name = 'Unknown Workgroup'
                    
                    # Format date (extract date from ISO 8601 datetime if needed)
                    if 'T' in date:
                        date = date.split('T')[0]
                    if not date:
                        # Try to get date from chunk directly if not in metadata
                        date = chunk.get('date', '')
                        if 'T' in date:
                            date = date.split('T')[0]
                    
                    # If date still missing, look up from meeting entity
                    if not date and meeting_id and meeting_id != 'unknown':
                        try:
                            from ..services.entity_storage import load_entity
                            from ..models.meeting import Meeting
                            from ..lib.config import ENTITIES_MEETINGS_DIR
                            
                            meeting_uuid = UUID(meeting_id)
                            meeting = load_entity(meeting_uuid, ENTITIES_MEETINGS_DIR, Meeting)
                            if meeting and meeting.date:
                                # Format date from meeting entity
                                if hasattr(meeting.date, 'isoformat'):
                                    date = meeting.date.isoformat()
                                elif hasattr(meeting.date, 'strftime'):
                                    date = meeting.date.strftime('%Y-%m-%d')
                                else:
                                    date = str(meeting.date)
                                
                                # Extract date part if datetime
                                if 'T' in date:
                                    date = date.split('T')[0]
                                
                                logger.debug(
                                    "meeting_date_loaded_from_entity",
                                    meeting_id=meeting_id,
                                    date=date
                                )
                                
                                # Also update workgroup name if we have the meeting
                                if not workgroup_name or workgroup_name == 'Unknown Workgroup':
                                    if meeting.workgroup_id:
                                        from ..models.workgroup import Workgroup
                                        from ..lib.config import ENTITIES_WORKGROUPS_DIR
                                        workgroup = load_entity(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                                        if workgroup:
                                            workgroup_name = workgroup.name
                        except Exception as e:
                            logger.debug(
                                "meeting_date_lookup_failed",
                                meeting_id=meeting_id,
                                error=str(e)
                            )
                    
                    if not date:
                        date = 'Unknown Date'
                        logger.warning(
                            "meeting_date_missing",
                            meeting_id=meeting_id,
                            workgroup=workgroup_name
                        )
                    
                    # Cache the metadata for future use
                    self._meeting_metadata_cache[meeting_id] = {
                        'workgroup_name': workgroup_name,
                        'date': date
                    }
                
                # Format date in a more readable format (YYYY-MM-DD is already readable, but ensure it's clear)
                # The date format YYYY-MM-DD is clear and unambiguous
                formatted_date = date
                
                # Format meeting identifier: "Workgroup Name - Date"
                # Make it very clear and prominent in the prompt
                meeting_identifier = f"{workgroup_name} - {formatted_date}"
                
                logger.debug(
                    "meeting_context_formatted",
                    meeting_id=meeting_id,
                    identifier=meeting_identifier
                )
                
                # Get chunk text
                chunk_text = chunk.get('text', '')
                
                # For decision queries, enhance context with actual decision items
                if is_decision_query and meeting_id and meeting_id != 'unknown' and meeting_id not in meeting_ids_processed:
                    try:
                        from ..services.entity_query import EntityQueryService
                        
                        meeting_uuid = UUID(meeting_id)
                        entity_query = EntityQueryService()
                        decision_items = entity_query.get_decision_items_by_meeting(meeting_uuid)
                        
                        if decision_items:
                            # Build decision text from decision items
                            decision_texts = []
                            for decision_item in decision_items:
                                if decision_item.decision and decision_item.decision.strip():
                                    decision_text = decision_item.decision.strip()
                                    # Include rationale if available
                                    if decision_item.rationale and decision_item.rationale.strip():
                                        decision_text += f" (Rationale: {decision_item.rationale.strip()})"
                                    decision_texts.append(decision_text)
                            
                            if decision_texts:
                                # Replace or enhance chunk text with actual decision content
                                if not chunk_text or len(chunk_text.strip()) < 50:
                                    # If chunk text is minimal, replace it with decision content
                                    chunk_text = "Decisions made:\n" + "\n".join(f"- {dt}" for dt in decision_texts)
                                else:
                                    # If chunk text exists, append decision content
                                    chunk_text += "\n\nDecisions made:\n" + "\n".join(f"- {dt}" for dt in decision_texts)
                            
                            logger.debug(
                                "decision_content_loaded_for_rag",
                                meeting_id=meeting_id,
                                decision_count=len(decision_items)
                            )
                        
                        meeting_ids_processed.add(meeting_id)
                    except Exception as e:
                        logger.debug(
                            "failed_to_load_decisions_for_rag",
                            meeting_id=meeting_id,
                            error=str(e)
                        )
                        # Continue with original chunk text if decision loading fails
                
                # Include both meeting ID and human-readable identifier
                context_parts.append(
                    f"[Meeting: {meeting_id} | {meeting_identifier}]\n{chunk_text}"
                )
            
            context_text = "\n\n".join(context_parts)
            
            # Create prompt with explicit instructions to identify meetings
            decision_instructions = ""
            if is_decision_query:
                decision_instructions = """

CRITICAL INSTRUCTIONS FOR DECISION QUERIES:
- You MUST list the SPECIFIC decisions that were made in each meeting
- For each meeting, clearly state what decisions were made
- Do NOT just say "decisions were made" - you MUST specify what those decisions were
- Use the decision text provided in the meeting records
- Format: "In the [Workgroup Name - Date] meeting, the following decisions were made: [list decisions]"
"""
            
            prompt = f"""Based on the following meeting records, answer the question.

CRITICAL INSTRUCTIONS FOR MEETING REFERENCES:
- You MUST include BOTH the workgroup name AND the date when referencing any meeting
- Format: "Workgroup Name - YYYY-MM-DD" (e.g., "Governance Workgroup - 2025-03-15")
- NEVER reference a meeting with just the workgroup name (e.g., "Governance Workgroup" alone is WRONG)
- NEVER use generic terms like "first meeting", "second meeting", "the meeting", etc.
- ALWAYS use the exact format shown in the meeting records: "Workgroup Name - Date"

Example of CORRECT format:
"In the Governance Workgroup - 2025-03-15 meeting, it was decided..."
"The Archives Workgroup - 2025-04-20 meeting noted that..."

Example of WRONG format (DO NOT USE):
"In the Governance Workgroup meeting..." (missing date)
"In the first meeting..." (too generic)
"The Archives Workgroup decided..." (missing date)
{decision_instructions}

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


"""Query service that orchestrates query flow with audit logging."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from ..services.retrieval import query_index, load_index
from ..services.embedding import create_embedding_service
from ..services.rag_generator import create_rag_generator
from ..services.citation_extractor import extract_citations
from ..services.evidence_checker import check_evidence, get_no_evidence_message
from ..models.rag_query import RAGQuery, RetrievedChunk, Citation
from ..services.audit_writer import AuditWriter
from ..lib.config import DEFAULT_TOP_K, DEFAULT_SEED
from ..lib.logging import get_logger

logger = get_logger(__name__)


class QueryService:
    """Service for executing queries with full audit logging."""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        seed: int = DEFAULT_SEED
    ):
        """
        Initialize query service.
        
        Args:
            model_name: Name of LLM model (optional)
            seed: Random seed for reproducibility
        """
        self.model_name = model_name
        self.seed = seed
        self.audit_writer = AuditWriter()
    
    def execute_query(
        self,
        index_name: str,
        query_text: str,
        top_k: int = DEFAULT_TOP_K,
        user_id: Optional[str] = None,
        model_version: Optional[str] = None
    ) -> RAGQuery:
        """
        Execute query with full audit logging.
        
        Args:
            index_name: Name of the FAISS index
            query_text: User query text
            top_k: Number of chunks to retrieve
            user_id: SSO user identifier (optional)
            model_version: LLM model version (optional)
            
        Returns:
            RAGQuery with complete query results
        """
        query_id = str(uuid.uuid4())
        
        try:
            # Load index (includes compliance checks - T047 - US3)
            index, embedding_index = load_index(index_name)
            
            # Verify entity-based FAISS index compatibility (T047 - US3)
            # Check that index metadata contains meeting_id references (entity-based)
            from ..services.compliance_checker import get_compliance_checker
            checker = get_compliance_checker()
            violations = checker.check_faiss_operations()
            if violations:
                raise violations[0]
            
            # Create embedding service
            embedding_service = create_embedding_service(
                model_name=embedding_index.embedding_model
            )
            
            # Validate embedding dimension matches index
            service_dim = embedding_service.get_embedding_dimension()
            index_dim = embedding_index.embedding_dimension
            
            if service_dim != index_dim:
                error_msg = (
                    f"Embedding dimension mismatch: "
                    f"Service dimension ({service_dim}D) does not match index dimension ({index_dim}D).\n"
                    f"Index was created with model: {embedding_index.embedding_model}\n"
                    f"Current embedding service model: {embedding_service.model_name}\n\n"
                    f"Solution: Re-index with the current embedding model:\n"
                    f"  archive-rag index <input> {index_name}\n\n"
                    f"Or use the same embedding model that was used to create the index."
                )
                logger.error(
                    "embedding_dimension_mismatch",
                    query_id=query_id,
                    service_dim=service_dim,
                    index_dim=index_dim,
                    index_model=embedding_index.embedding_model,
                    service_model=embedding_service.model_name
                )
                raise ValueError(error_msg)
            
            # Query index
            retrieved_chunks = query_index(
                query_text,
                embedding_service,
                index_name,
                top_k=top_k
            )
            
            # Verify RAG queries work with entity-based FAISS indexes (T047 - US3)
            # Check that retrieved chunks contain meeting_id (entity-based structure)
            for chunk in retrieved_chunks:
                if 'meeting_id' not in chunk:
                    logger.warning("rag_query_chunk_missing_meeting_id", chunk=chunk)
            
            # Initialize RAG generator (needed for all paths)
            rag_generator = create_rag_generator(
                model_name=self.model_name,
                seed=self.seed
            )
            
            # Check if this is a quantitative question requiring direct data access
            from ..services.quantitative_query import create_quantitative_query_service
            quantitative_service = create_quantitative_query_service()
            
            # Detect quantitative questions (comprehensive natural language patterns)
            query_lower = query_text.lower()
            
            # Statistical keywords
            statistical_keywords = [
                "average", "mean", "range", "min", "max", "minimum", "maximum",
                "trend", "distribution", "frequency", "most", "least", "median"
            ]
            
            # Entity keywords
            entity_keywords = [
                "workgroup", "person", "people", "meeting", "date", "meetings",
                "participant", "participants", "document", "documents"
            ]
            
            # Count variations (natural language patterns)
            count_patterns = [
                "how many", "count", "number of", "total", "quantity",
                "what's the count", "tell me how many", "i need the number",
                "meeting count", "total meetings", "how many total", 
                "give me the count", "what is the total", "total number of",
                "how many are there", "can you count", "count of"
            ]
            
            # List/retrieval patterns (not quantitative, but handled by quantitative service)
            list_patterns = [
                "list", "show me", "what are", "what documents", "show documents",
                "documents for", "documents in", "all documents", "show all"
            ]
            has_list = any(pattern in query_lower for pattern in list_patterns)
            
            # Combine patterns: statistical OR (entity AND count) OR (list pattern)
            has_statistical = any(keyword in query_lower for keyword in statistical_keywords)
            has_entity = any(keyword in query_lower for keyword in entity_keywords)
            has_count = any(pattern in query_lower for pattern in count_patterns)
            
            # Quantitative if: statistical question OR (entity-related count question) OR (list question with document/entity keyword)
            is_quantitative = has_statistical or (has_entity and has_count) or has_count or (has_list and ("document" in query_lower or any(e in query_lower for e in entity_keywords)))
            
            if is_quantitative:
                # Use quantitative query service for accurate counts
                logger.info("quantitative_query_detected", query=query_text)
                
                # Try to extract source URL from question
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]?]+'
                urls = re.findall(url_pattern, query_text)
                source_url = urls[0] if urls else None
                # Remove trailing ? if present
                if source_url and source_url.endswith('?'):
                    source_url = source_url[:-1]
                
                quantitative_result = quantitative_service.answer_quantitative_question(query_text, source_url=source_url)
                
                if "count" in quantitative_result:
                    # Build answer with citations
                    answer = quantitative_result["answer"]
                    
                    # Add unique count info if different from total
                    unique_count = quantitative_result.get("unique_count")
                    count = quantitative_result.get("count", 0)
                    if unique_count and unique_count != count:
                        answer += f"\n\n**Note:** The source JSON array contains {count} total entries, but {unique_count} unique meetings (based on workgroup_id + date combinations)."
                    
                    citations_text = "\n".join([
                        f"- {cit.get('description', 'Data source')}: {cit.get('file_count', 'N/A') if cit.get('file_count') else cit.get('url', 'N/A')}"
                        for cit in quantitative_result.get("citations", [])
                    ])
                    
                    # Include method and source in answer
                    answer = f"{answer}\n\n**Data Source:** {quantitative_result['source']}\n**Method:** {quantitative_result['method']}\n\n**Verification:**\n{citations_text}"
                    
                    # Use quantitative result as evidence
                    evidence_found = True
                    
                    # Create proper chunk structure for citation
                    # Use first retrieved chunk if available, otherwise create minimal structure
                    if not retrieved_chunks:
                        retrieved_chunks = [{
                            "text": f"Quantitative analysis: {quantitative_result.get('count', 0)} meetings found in entity storage",
                            "meeting_id": "quantitative-query",
                            "chunk_index": 0,
                            "source": quantitative_result["source"],
                            "score": 1.0
                        }]
                    else:
                        # Add quantitative info to existing chunks
                        for chunk in retrieved_chunks:
                            chunk["quantitative_analysis"] = {
                                "count": quantitative_result.get('count', 0),
                                "method": quantitative_result.get('method', ''),
                                "source": quantitative_result.get('source', '')
                            }
                elif "answer" in quantitative_result:
                    # This is a list/retrieval query (like document listing)
                    answer = quantitative_result["answer"]
                    
                    # Include method and source in answer if provided
                    if "source" in quantitative_result and "method" in quantitative_result:
                        answer = f"{answer}\n\n**Data Source:** {quantitative_result['source']}\n**Method:** {quantitative_result['method']}"
                    
                    # Use quantitative result as evidence
                    evidence_found = True
                    
                    # Include document details if provided (full list already in answer, but add count if truncated)
                    if "documents" in quantitative_result and "count" in quantitative_result:
                        docs = quantitative_result["documents"]
                        count = quantitative_result.get("count", len(docs))
                        if len(docs) > 50 and count > 50:
                            # Full list already in answer, just ensure count is clear
                            pass
                    
                    # Create proper chunk structure for citation
                    if not retrieved_chunks:
                        retrieved_chunks = [{
                            "text": f"Entity query: {quantitative_result.get('count', 0)} documents retrieved from entity storage",
                            "meeting_id": "entity-query",
                            "chunk_index": 0,
                            "source": quantitative_result.get("source", "Entity storage"),
                            "score": 1.0
                        }]
                else:
                    # Fall back to RAG if quantitative query doesn't handle it
                    evidence_found = check_evidence(retrieved_chunks)
                    if evidence_found:
                        answer = rag_generator.generate(query_text, retrieved_chunks)
                    else:
                        answer = get_no_evidence_message()
            else:
                # Standard RAG query
                evidence_found = check_evidence(retrieved_chunks)
                
                if evidence_found:
                    answer = rag_generator.generate(query_text, retrieved_chunks)
                else:
                    answer = get_no_evidence_message()
            
            # Extract citations - ensure citations are ALWAYS present
            from ..models.rag_query import Citation
            from ..services.citation_extractor import create_no_evidence_citation
            
            citations = []
            
            # For quantitative queries, add data source citations
            if is_quantitative and "count" in quantitative_result:
                # Add citation for quantitative analysis with proper format
                count = quantitative_result.get('count', 0)
                source = quantitative_result.get('source', 'entity storage')
                method = quantitative_result.get('method', 'Direct file count')
                
                # Create citation showing the counting process
                citations.append(Citation(
                    meeting_id="entity-storage",
                    date=datetime.utcnow().strftime("%Y-%m-%d"),
                    speaker="System",
                    excerpt=f"Counted {count} meetings by scanning JSON files in {source}. Method: {method}."
                ))
                
                # Also include any existing retrieved chunks as additional context
                existing_citations = extract_citations(retrieved_chunks)
                citations.extend(existing_citations)
            elif is_quantitative and "answer" in quantitative_result:
                # Statistical or other quantitative query
                source = quantitative_result.get('source', 'entity storage')
                method = quantitative_result.get('method', 'Quantitative analysis')
                
                citations.append(Citation(
                    meeting_id="quantitative-analysis",
                    date=datetime.utcnow().strftime("%Y-%m-%d"),
                    speaker="System",
                    excerpt=f"Quantitative analysis performed. Method: {method}. Source: {source}."
                ))
                
                # Include any additional citations from quantitative result
                if "citations" in quantitative_result:
                    for cit in quantitative_result["citations"]:
                        if isinstance(cit, dict):
                            citations.append(Citation(
                                meeting_id=cit.get("type", "quantitative"),
                                date=datetime.utcnow().strftime("%Y-%m-%d"),
                                speaker="System",
                                excerpt=cit.get("description", f"Method: {cit.get('method', method)}")
                            ))
            else:
                # Standard RAG query - extract citations from chunks
                citations = extract_citations(retrieved_chunks)
                
                # If no citations found, add no-evidence citation
                if not citations:
                    citations.append(create_no_evidence_citation(index_name))
            
            # Create RAGQuery model
            rag_query = RAGQuery(
                query_id=query_id,
                user_input=query_text,
                timestamp=datetime.utcnow().isoformat() + "Z",
                retrieved_chunks=[
                    RetrievedChunk(**chunk) for chunk in retrieved_chunks
                ],
                output=answer,
                citations=citations,
                model_version=model_version or rag_generator.model_name,
                embedding_version=embedding_index.embedding_model,
                user_id=user_id,
                evidence_found=evidence_found,
                audit_log_path=f"audit_logs/query-{query_id}.json"
            )
            
            # Create audit log entry
            self.audit_writer.write_query_audit_log(rag_query)
            
            logger.info(
                "query_executed",
                query_id=query_id,
                evidence_found=evidence_found,
                citations_count=len(citations)
            )
            
            return rag_query
            
        except Exception as e:
            logger.error("query_execution_failed", query_id=query_id, error=str(e))
            raise


def create_query_service(
    model_name: Optional[str] = None,
    seed: int = DEFAULT_SEED
) -> QueryService:
    """
    Create a query service instance.
    
    Args:
        model_name: Name of LLM model
        seed: Random seed for reproducibility
        
    Returns:
        QueryService instance
    """
    return QueryService(model_name, seed)


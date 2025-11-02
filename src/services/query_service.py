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
            # Load index
            index, embedding_index = load_index(index_name)
            
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
            
            # Check evidence
            evidence_found = check_evidence(retrieved_chunks)
            
            # Generate answer
            rag_generator = create_rag_generator(
                model_name=self.model_name,
                seed=self.seed
            )
            
            if evidence_found:
                answer = rag_generator.generate(query_text, retrieved_chunks)
            else:
                answer = get_no_evidence_message()
            
            # Extract citations
            citations = extract_citations(retrieved_chunks)
            
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


"""Audit log writer service for immutable JSON logs."""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from ..models.rag_query import RAGQuery
from ..lib.audit import write_audit_log, ensure_audit_logs_directory
from ..lib.config import AUDIT_LOGS_DIR
from ..lib.logging import get_logger

logger = get_logger(__name__)


class AuditWriter:
    """Service for writing immutable audit log entries."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize audit writer.
        
        Args:
            log_dir: Directory for audit logs (default: AUDIT_LOGS_DIR)
        """
        self.log_dir = log_dir or ensure_audit_logs_directory()
    
    def write_query_audit_log(self, rag_query: RAGQuery) -> Path:
        """
        Write audit log entry for a query.
        
        Args:
            rag_query: RAGQuery model with query results
            
        Returns:
            Path to written audit log file
        """
        audit_data = {
            "query_id": rag_query.query_id,
            "timestamp": rag_query.timestamp,
            "user_input": rag_query.user_input,
            "user_id": rag_query.user_id,
            "retrieved_chunks": [
                {
                    "meeting_id": chunk.meeting_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "score": chunk.score
                }
                for chunk in rag_query.retrieved_chunks
            ],
            "output": rag_query.output,
            "citations": [
                {
                    "meeting_id": citation.meeting_id,
                    "date": citation.date,
                    "speaker": citation.speaker,
                    "excerpt": citation.excerpt
                }
                for citation in rag_query.citations
            ],
            "model_version": rag_query.model_version,
            "embedding_version": rag_query.embedding_version,
            "evidence_found": rag_query.evidence_found
        }
        
        log_path = write_audit_log(rag_query.query_id, audit_data, self.log_dir)
        
        logger.info(
            "audit_log_written",
            query_id=rag_query.query_id,
            log_path=str(log_path)
        )
        
        return log_path
    
    def write_index_audit_log(
        self,
        operation: str,
        input_dir: str,
        output_index: str,
        metadata: Dict[str, Any]
    ) -> Path:
        """
        Write audit log entry for an indexing operation.
        
        Args:
            operation: Operation type (e.g., "index")
            input_dir: Input directory path
            output_index: Output index path
            metadata: Additional metadata dictionary
            
        Returns:
            Path to written audit log file
        """
        import uuid
        query_id = str(uuid.uuid4())
        
        audit_data = {
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "input_dir": input_dir,
            "output_index": output_index,
            **metadata
        }
        
        log_path = write_audit_log(query_id, audit_data, self.log_dir)
        
        logger.info(
            "index_audit_log_written",
            operation=operation,
            log_path=str(log_path)
        )
        
        return log_path


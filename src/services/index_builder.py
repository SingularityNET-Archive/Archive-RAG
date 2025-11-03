"""FAISS index builder service."""

import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ..models.embedding_index import EmbeddingIndex
from ..services.chunking import DocumentChunk
from ..services.embedding import EmbeddingService
from ..lib.config import get_index_path, get_index_metadata_path
from ..lib.hashing import compute_bytes_hash, compute_string_hash
from ..lib.logging import get_logger
from ..lib.compliance import ConstitutionViolation

logger = get_logger(__name__)

# Global compliance checker instance
_compliance_checker = None


def _get_compliance_checker():
    """Get or create compliance checker instance."""
    global _compliance_checker
    if _compliance_checker is None:
        from ..services.compliance_checker import ComplianceChecker
        _compliance_checker = ComplianceChecker()
        # Enable monitoring by default for compliance checking
        _compliance_checker.enable_monitoring()
    return _compliance_checker


def build_faiss_index(
    chunks: List[DocumentChunk],
    embedding_service: EmbeddingService,
    index_type: str = "IndexFlatIP",
    index_name: str = "index"
) -> tuple[faiss.Index, EmbeddingIndex]:
    """
    Build FAISS index from document chunks.
    
    Args:
        chunks: List of DocumentChunk objects
        embedding_service: EmbeddingService instance
        index_type: FAISS index type (default: IndexFlatIP)
        index_name: Name for the index
        
    Returns:
        Tuple of (FAISS index, EmbeddingIndex metadata)
    """
    if not chunks:
        raise ValueError("No chunks provided for indexing")
    
    # Generate embeddings for all chunks
    texts = [chunk.text for chunk in chunks]
    logger.info("generating_embeddings", num_chunks=len(texts))
    embeddings = embedding_service.embed_texts(texts, batch_size=32)
    logger.info("embeddings_generated", shape=embeddings.shape)
    
    # Get embedding dimension
    embedding_dim = embedding_service.get_embedding_dimension()
    
    # Normalize embeddings for cosine similarity (Inner Product)
    faiss.normalize_L2(embeddings)
    
    # Create FAISS index
    if index_type == "IndexFlatIP":
        index = faiss.IndexFlatIP(embedding_dim)
    elif index_type == "IndexIVFFlat":
        # Use IVF for larger datasets (requires training)
        quantizer = faiss.IndexFlatIP(embedding_dim)
        nlist = min(100, max(10, len(chunks) // 10))  # Number of clusters
        index = faiss.IndexIVFFlat(quantizer, embedding_dim, nlist)
        index.train(embeddings)
    else:
        raise ValueError(f"Unsupported index type: {index_type}")
    
    # Add embeddings to index
    index.add(embeddings)
    
    # Build metadata mapping (vector_index -> document metadata)
    metadata = {}
    for i, chunk in enumerate(chunks):
        metadata[i] = {
            "meeting_id": chunk.meeting_id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "start_idx": chunk.start_idx,
            "end_idx": chunk.end_idx,
            **chunk.metadata
        }
    
    # Compute version hash (index configuration + model version)
    version_data = {
        "embedding_model": embedding_service.model_name,
        "embedding_dimension": embedding_dim,
        "index_type": index_type,
        "total_documents": len(chunks)
    }
    version_hash = compute_string_hash(json.dumps(version_data, sort_keys=True))
    
    # Determine actual index path (handle full paths vs names)
    from pathlib import Path
    if '/' in index_name or '\\' in index_name:
        actual_index_path = Path(index_name)
        if not actual_index_path.suffix:
            actual_index_path = Path(str(actual_index_path) + ".faiss")
    else:
        actual_index_path = get_index_path(index_name)
    
    # Check compliance for FAISS operations (T044 - US3)
    checker = _get_compliance_checker()
    violations = checker.check_faiss_operations()
    if violations:
        raise violations[0]
    
    # Verify FAISS index is stored locally (T043 - US3)
    local_violations = checker.verify_faiss_index_local_only(str(actual_index_path))
    if local_violations:
        raise local_violations[0]
    
    # Create EmbeddingIndex metadata
    embedding_index = EmbeddingIndex(
        index_id=index_name,
        version_hash=version_hash,
        embedding_model=embedding_service.model_name,
        embedding_dimension=embedding_dim,
        index_type=index_type,
        metadata=metadata,
        total_documents=len(chunks),
        created_at=datetime.utcnow().isoformat() + "Z",
        index_path=str(actual_index_path)
    )
    
    logger.info(
        "faiss_index_built",
        index_id=index_name,
        total_documents=len(chunks),
        embedding_dim=embedding_dim,
        index_type=index_type
    )
    
    return index, embedding_index


def save_index(
    index: faiss.Index,
    embedding_index: EmbeddingIndex,
    index_name: str
) -> None:
    """
    Save FAISS index and metadata to disk.
    
    Args:
        index: FAISS index object
        embedding_index: EmbeddingIndex metadata
        index_name: Name or full path for the index (if contains '/', treated as full path)
        
    Raises:
        ConstitutionViolation: If compliance violation detected
    """
    from pathlib import Path
    
    # Handle full paths vs just index names
    if '/' in index_name or '\\' in index_name:
        # Full path provided - use as is
        index_path = Path(index_name)
        if not index_path.suffix:
            index_path = Path(str(index_path) + ".faiss")
        metadata_path = Path(str(index_path) + ".metadata.json")
    else:
        # Just index name - use get_index_path helper
        index_path = get_index_path(index_name)
        metadata_path = get_index_metadata_path(index_name)
    
    # Check compliance for FAISS operations (T044 - US3)
    checker = _get_compliance_checker()
    violations = checker.check_faiss_operations()
    if violations:
        raise violations[0]
    
    # Verify FAISS index is stored locally (T043 - US3)
    local_violations = checker.verify_faiss_index_local_only(str(index_path))
    if local_violations:
        raise local_violations[0]
    
    # Ensure parent directory exists
    index_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save FAISS index
    faiss.write_index(index, str(index_path))
    
    # Save metadata
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(embedding_index.to_dict(), f, indent=2, ensure_ascii=False)
    
    logger.info(
        "index_saved",
        index_path=str(index_path),
        metadata_path=str(metadata_path)
    )


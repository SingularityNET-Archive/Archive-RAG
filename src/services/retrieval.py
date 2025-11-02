"""FAISS retrieval service for similarity search."""

import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any

from ..models.embedding_index import EmbeddingIndex
from ..services.embedding import EmbeddingService
from ..lib.config import get_index_path, get_index_metadata_path
from ..lib.logging import get_logger

logger = get_logger(__name__)


def load_index(index_name: str) -> tuple[faiss.Index, EmbeddingIndex]:
    """
    Load FAISS index and metadata from disk.
    
    Args:
        index_name: Name of the index
        
    Returns:
        Tuple of (FAISS index, EmbeddingIndex metadata)
        
    Raises:
        FileNotFoundError: If index or metadata file not found
    """
    index_path = get_index_path(index_name)
    metadata_path = get_index_metadata_path(index_name)
    
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")
    
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    
    # Load FAISS index
    index = faiss.read_index(str(index_path))
    
    # Load metadata
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata_dict = json.load(f)
    
    embedding_index = EmbeddingIndex.from_dict(metadata_dict)
    
    logger.info(
        "index_loaded",
        index_name=index_name,
        total_documents=embedding_index.total_documents
    )
    
    return index, embedding_index


def retrieve_similar_chunks(
    query_embedding: np.ndarray,
    index: faiss.Index,
    embedding_index: EmbeddingIndex,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve top-k similar chunks from FAISS index.
    
    Args:
        query_embedding: Query embedding vector
        embedding_service: EmbeddingService instance
        index: FAISS index
        embedding_index: EmbeddingIndex metadata
        top_k: Number of chunks to retrieve
        
    Returns:
        List of retrieved chunk dictionaries with metadata and scores
    """
    # Normalize query embedding
    query_embedding = query_embedding.reshape(1, -1)
    faiss.normalize_L2(query_embedding)
    
    # Search index
    scores, indices = index.search(query_embedding, top_k)
    
    # Retrieve chunks with metadata
    retrieved_chunks = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:  # Invalid index
            continue
        
        chunk_metadata = embedding_index.metadata.get(int(idx), {})
        retrieved_chunk = {
            "meeting_id": chunk_metadata.get("meeting_id", ""),
            "chunk_index": chunk_metadata.get("chunk_index", 0),
            "text": chunk_metadata.get("text", ""),
            "score": float(score),
            "metadata": chunk_metadata
        }
        retrieved_chunks.append(retrieved_chunk)
    
    logger.info(
        "chunks_retrieved",
        top_k=top_k,
        retrieved=len(retrieved_chunks)
    )
    
    return retrieved_chunks


def query_index(
    query_text: str,
    embedding_service: EmbeddingService,
    index_name: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Query FAISS index with text query.
    
    Args:
        query_text: User query text
        embedding_service: EmbeddingService instance
        index_name: Name of the index
        top_k: Number of chunks to retrieve
        
    Returns:
        List of retrieved chunk dictionaries
    """
    # Load index
    index, embedding_index = load_index(index_name)
    
    # Generate query embedding
    query_embedding = embedding_service.embed_text(query_text)
    
    # Retrieve similar chunks
    retrieved_chunks = retrieve_similar_chunks(
        query_embedding,
        index,
        embedding_index,
        top_k
    )
    
    return retrieved_chunks


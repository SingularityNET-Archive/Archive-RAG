"""Decision query service for searching decisions using free text."""

from typing import List, Dict, Any, Optional
from uuid import UUID
import logging

from ..services.retrieval import query_index
from ..services.embedding import create_embedding_service
from ..services.entity_query import EntityQueryService
from ..models.decision_item import DecisionItem
from ..lib.logging import get_logger

logger = get_logger(__name__)


def query_decisions_by_text(
    query_text: str,
    index_name: str,
    top_k: int = 10,
    min_score: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Query decisions using free text search via RAG index.
    
    Uses the existing FAISS index to find meeting chunks that match the query,
    then maps those chunks back to DecisionItem entities for those meetings.
    
    Args:
        query_text: Free text query (e.g., "budget decisions" or "what were the decisions about funding?")
        index_name: Name of the FAISS index file
        top_k: Number of top results to retrieve
        min_score: Minimum similarity score threshold (0.0 to 1.0)
    
    Returns:
        List of dictionaries containing DecisionItem data with query metadata:
        {
            "decision": DecisionItem object,
            "meeting_id": UUID of meeting,
            "relevance_score": float similarity score,
            "chunk_text": str text from retrieved chunk
        }
    """
    logger.info("query_decisions_by_text_start", query_text=query_text[:50], top_k=top_k)
    
    try:
        # Step 1: Query the FAISS index for relevant chunks
        embedding_service = create_embedding_service()
        retrieved_chunks = query_index(
            query_text=query_text,
            embedding_service=embedding_service,
            index_name=index_name,
            top_k=top_k * 2  # Get more chunks to filter down to decisions
        )
        
        # Step 2: Extract unique meeting IDs from retrieved chunks
        meeting_ids = set()
        chunk_metadata = {}
        for chunk in retrieved_chunks:
            score = chunk.get("score", 0.0)
            if score >= min_score:
                meeting_id_str = chunk.get("meeting_id", "")
                if meeting_id_str:
                    try:
                        meeting_id = UUID(meeting_id_str)
                        meeting_ids.add(meeting_id)
                        # Store chunk text for this meeting (highest score wins if multiple chunks)
                        if meeting_id not in chunk_metadata or chunk_metadata[meeting_id]["score"] < score:
                            chunk_metadata[meeting_id] = {
                                "score": score,
                                "text": chunk.get("text", ""),
                                "chunk": chunk
                            }
                    except ValueError:
                        logger.warning("invalid_meeting_id_in_chunk", meeting_id=meeting_id_str)
                        continue
        
        logger.debug("query_decisions_meeting_ids_found", meeting_count=len(meeting_ids))
        
        # Step 3: Query DecisionItem entities for each meeting
        entity_query_service = EntityQueryService()
        decision_results = []
        
        for meeting_id in meeting_ids:
            try:
                # Get all decisions for this meeting
                decisions = entity_query_service.get_decision_items_by_meeting(meeting_id)
                
                # Combine with query metadata
                chunk_info = chunk_metadata.get(meeting_id, {})
                relevance_score = chunk_info.get("score", 0.0)
                
                for decision in decisions:
                    decision_results.append({
                        "decision": decision,
                        "meeting_id": meeting_id,
                        "relevance_score": float(relevance_score),
                        "chunk_text": chunk_info.get("text", ""),
                        "matched_chunk": chunk_info.get("chunk")
                    })
            except Exception as e:
                logger.warning("query_decisions_meeting_failed", meeting_id=str(meeting_id), error=str(e))
                continue
        
        # Step 4: Sort by relevance score (highest first)
        decision_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Step 5: Limit to top_k results
        decision_results = decision_results[:top_k]
        
        logger.info(
            "query_decisions_by_text_success",
            query_text=query_text[:50],
            results_count=len(decision_results),
            meetings_searched=len(meeting_ids)
        )
        
        return decision_results
        
    except Exception as e:
        logger.error("query_decisions_by_text_failed", query_text=query_text[:50], error=str(e))
        raise


def format_decision_results(
    results: List[Dict[str, Any]],
    include_rationale: bool = True,
    include_effect: bool = True,
    include_score: bool = False
) -> str:
    """
    Format decision query results as text.
    
    Args:
        results: List of decision result dictionaries from query_decisions_by_text
        include_rationale: Whether to include rationale in output
        include_effect: Whether to include effect in output
        include_score: Whether to include relevance score in output
    
    Returns:
        Formatted text string
    """
    if not results:
        return "No decisions found matching your query."
    
    lines = []
    lines.append(f"Found {len(results)} decision(s) matching your query:\n")
    
    for i, result in enumerate(results, 1):
        decision = result["decision"]
        lines.append(f"{i}. {decision.decision}")
        
        if include_rationale and decision.rationale:
            lines.append(f"   Rationale: {decision.rationale}")
        
        if include_effect and decision.effect:
            lines.append(f"   Effect: {decision.effect.value}")
        
        if include_score:
            lines.append(f"   Relevance Score: {result['relevance_score']:.3f}")
        
        lines.append(f"   Meeting ID: {result['meeting_id']}")
        lines.append(f"   Created: {decision.created_at}")
        lines.append("")
    
    return "\n".join(lines)


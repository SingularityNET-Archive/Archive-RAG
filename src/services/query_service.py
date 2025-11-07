"""Query service that orchestrates query flow with audit logging."""

import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import UUID

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
            
            # Extract meeting ID from query if specified
            # This ensures queries like "What did meeting X say about Y?" only return citations from meeting X
            from ..services.query_filter import (
                should_apply_whole_word_filtering,
                extract_entity_names_from_query,
                filter_chunks_by_whole_word_match,
                extract_meeting_id_from_query,
                filter_chunks_by_meeting_id,
                extract_date_from_query,
                filter_chunks_by_date_range
            )
            
            meeting_id_from_query = extract_meeting_id_from_query(query_text)
            if meeting_id_from_query:
                original_count = len(retrieved_chunks)
                retrieved_chunks = filter_chunks_by_meeting_id(
                    retrieved_chunks,
                    meeting_id_from_query
                )
                if len(retrieved_chunks) < original_count:
                    logger.info(
                        "chunks_filtered_by_meeting_id_from_query",
                        meeting_id=meeting_id_from_query,
                        original_chunks=original_count,
                        filtered_chunks=len(retrieved_chunks)
                    )
            
            # Apply whole-word filtering for entity name queries
            # This ensures "AGI" doesn't match "AGIX" (whole-word boundaries required)
            if should_apply_whole_word_filtering(query_text):
                entity_names = extract_entity_names_from_query(query_text)
                if entity_names:
                    original_count = len(retrieved_chunks)
                    retrieved_chunks = filter_chunks_by_whole_word_match(
                        retrieved_chunks,
                        entity_names,
                        query_text
                    )
                    if len(retrieved_chunks) < original_count:
                        logger.info(
                            "whole_word_filtering_applied",
                            entity_names=entity_names,
                            original_chunks=original_count,
                            filtered_chunks=len(retrieved_chunks)
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
            
            # Detect topic queries (e.g., "What topics has X workgroup discussed?" or "what topics were discussed in March 2025")
            topic_keywords = ["topic", "topics", "discussed", "discuss", "covered", "tag", "tags"]
            # Topic query if: (topic keywords AND workgroup) OR (topic keywords AND date/time reference)
            has_topic_keywords = any(keyword in query_lower for keyword in topic_keywords)
            has_workgroup = "workgroup" in query_lower
            # Check for date/time references (month names, year patterns, date keywords)
            date_keywords = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
                           "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
                           "2024", "2025", "2026", "in march", "in april", "in may", "during"]
            has_date_reference = any(keyword in query_lower for keyword in date_keywords) or re.search(r'\b(19|20)\d{2}\b', query_text)
            has_topic_query = has_topic_keywords and (has_workgroup or has_date_reference)
            
            # Detect decision list queries (e.g., "List decisions made by workgroup in March 2025")
            # These should use RAG, not quantitative service
            decision_keywords = ["decision", "decisions", "decided", "decide"]
            has_decision_keywords = any(keyword in query_lower for keyword in decision_keywords)
            is_decision_list_query = has_decision_keywords and has_list and (has_workgroup or has_date_reference)
            
            # Quantitative if: statistical question OR (entity-related count question) OR (list question with document/entity keyword)
            # BUT NOT if it's a decision list query (those should use RAG)
            is_quantitative = (has_statistical or (has_entity and has_count) or has_count or (has_list and ("document" in query_lower or any(e in query_lower for e in entity_keywords)))) and not is_decision_list_query
            
            # Handle topic queries separately (use entity query service, not RAG)
            if has_topic_query:
                from ..services.entity_query import EntityQueryService
                from ..services.entity_normalization import EntityNormalizationService
                from ..services.entity_storage import load_entity
                from ..models.workgroup import Workgroup
                from ..lib.config import ENTITIES_WORKGROUPS_DIR
                
                entity_query = EntityQueryService()
                normalization_service = EntityNormalizationService()
                
                # Extract workgroup name and year from query
                workgroup_keywords = [
                    "governance", "archives", "education", "gamers", "github", 
                    "treasury", "knowledge", "latam", "moderators", "onboarding",
                    "process", "strategy", "pbl", "ethics", "ai", "archive"
                ]
                
                workgroup_id = None
                workgroup_name = None
                year = None
                
                # Find workgroup - optimized: try direct file search first (faster than loading all)
                # Use ENTITIES_WORKGROUPS_DIR directly (Path object from config)
                workgroups_dir = ENTITIES_WORKGROUPS_DIR
                
                # Try to extract workgroup name from query (look for "Archive Workgroup", "Governance Workgroup", etc.)
                workgroup_name_pattern = re.search(r'(\w+)\s+workgroup', query_lower)
                extracted_name = None
                if workgroup_name_pattern:
                    extracted_name = workgroup_name_pattern.group(1).lower()
                    logger.info("topic_query_extracted_name", extracted_name=extracted_name, query=query_lower[:100])
                
                # Optimized: Direct file search first (faster)
                # Try exact match with extracted name, then try with 's' suffix (Archive -> Archives)
                search_names = []
                if extracted_name:
                    search_names.append(extracted_name)
                    # Handle singular/plural variations
                    if not extracted_name.endswith('s'):
                        search_names.append(extracted_name + 's')
                    elif extracted_name.endswith('s') and len(extracted_name) > 1:
                        search_names.append(extracted_name[:-1])
                
                # Also check keywords from query
                for keyword in workgroup_keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in query_lower and keyword_lower not in search_names:
                        search_names.append(keyword_lower)
                
                logger.info("topic_query_search_names", search_names=search_names, query=query_lower[:100], search_count=len(search_names))
                
                # Search workgroup files directly (more efficient: single pass through files)
                # Check all search names in one iteration
                if not search_names:
                    logger.warning("topic_query_no_search_names", extracted_name=extracted_name, query=query_lower[:100])
                
                if search_names:  # Only search if we have search names
                    files_checked = 0
                    workgroup_files = list(workgroups_dir.glob("*.json"))
                    # Sort files for consistent processing
                    workgroup_files.sort(key=lambda x: x.name)
                    logger.debug("topic_query_workgroup_search_start", 
                               workgroups_dir=str(workgroups_dir),
                               file_count=len(workgroup_files),
                               search_names=search_names)
                    
                    for wg_file in workgroup_files:
                        if workgroup_id:  # Early exit if found
                            break
                        files_checked += 1
                        
                        try:
                            wg_uuid = UUID(wg_file.stem)
                            workgroup = load_entity(wg_uuid, workgroups_dir, Workgroup)
                            
                            if not workgroup:
                                continue
                            
                            if not hasattr(workgroup, 'name') or not workgroup.name:
                                continue
                            
                            workgroup_name_lower = workgroup.name.lower()
                            # Check all search names against this workgroup
                            for search_name in search_names:
                                # Improved matching: check if search name is in workgroup name
                                # Handle both "archive" matching "archives" and vice versa
                                workgroup_words = workgroup_name_lower.split()
                                # Check multiple matching strategies - "archive" should match "archives"
                                matched = False
                                # First check: simple substring match (most common case)
                                if search_name in workgroup_name_lower:
                                    matched = True
                                # Second check: check if search_name matches any word in workgroup name
                                elif search_name in workgroup_words:
                                    matched = True
                                # Third check: check if search_name is a substring of any word (e.g., "archive" in "archives")
                                else:
                                    for word in workgroup_words:
                                        if search_name in word or word.startswith(search_name) or search_name.startswith(word):
                                            matched = True
                                            break
                                
                                if matched:
                                    # Ensure we set both variables
                                    workgroup_id = workgroup.id
                                    workgroup_name = workgroup.name
                                    logger.info("workgroup_found_by_name", 
                                               search_name=search_name, 
                                               workgroup_name=workgroup.name,
                                               workgroup_id=str(workgroup_id),
                                               files_checked=files_checked)
                                    # Break inner loop
                                    break
                            
                            # Break outer loop when found (check after inner loop completes)
                            if workgroup_id is not None:
                                break
                        except Exception as e:
                            # Log errors at warning level to help debug issues
                            logger.warning("workgroup_load_error", 
                                         file=str(wg_file.name), 
                                         error=str(e),
                                         error_type=type(e).__name__)
                            continue
                    
                    if not workgroup_id:
                        logger.warning("topic_query_workgroup_search_failed", 
                                     search_names=search_names,
                                     files_checked=files_checked)
                
                # Fallback: Try normalization if direct search failed
                if not workgroup_id and extracted_name:
                    try:
                        all_workgroups = entity_query.find_all(workgroups_dir, Workgroup)
                        normalized_id, normalized_name = normalization_service.normalize_entity_name(
                            extracted_name,
                            existing_entities=all_workgroups,
                            context={}
                        )
                        if normalized_id.int != 0:
                            workgroup = entity_query.get_by_id(normalized_id, workgroups_dir, Workgroup)
                            if workgroup:
                                workgroup_id = workgroup.id
                                workgroup_name = workgroup.name
                    except Exception:
                        pass
                
                # Extract year and month from query
                year_match = re.search(r'\b(19|20)\d{2}\b', query_text)
                if year_match:
                    year = int(year_match.group())
                
                # Extract month if mentioned
                month = None
                month_names = {
                    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
                    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
                    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
                }
                for month_name, month_num in month_names.items():
                    if month_name in query_lower:
                        month = month_num
                        break
                
                if workgroup_id:
                    # Get topics for workgroup
                    topics = entity_query.get_topics_by_workgroup(workgroup_id, year=year)
                    
                    # Get meetings for this workgroup to create citations
                    meetings = entity_query.get_meetings_by_workgroup(workgroup_id)
                    if year is not None:
                        from datetime import date
                        start_date = date(year, 1, 1)
                        end_date = date(year + 1, 1, 1)
                        meetings = [m for m in meetings if start_date <= m.date < end_date]
                    
                    # Create citations from meetings (limit to avoid too many)
                    # Try to load chunk metadata from FAISS index for semantic chunk context (Phase 7)
                    citations = []
                    chunk_metadata_cache = {}  # Cache chunk metadata by meeting_id
                    
                    # Try to load index to get chunk metadata (Phase 7: semantic chunk context)
                    try:
                        index, embedding_index = load_index(index_name)
                        # Build cache of chunk metadata by meeting_id
                        # Use first chunk found for each meeting (or could aggregate)
                        for idx, chunk_meta in embedding_index.metadata.items():
                            chunk_meeting_id = chunk_meta.get("meeting_id", "")
                            if chunk_meeting_id:
                                # Normalize meeting_id to string format (handle both UUID and string)
                                try:
                                    # Try to convert to UUID and back to string for consistency
                                    chunk_meeting_id_uuid = UUID(str(chunk_meeting_id))
                                    chunk_meeting_id_normalized = str(chunk_meeting_id_uuid)
                                except (ValueError, AttributeError):
                                    chunk_meeting_id_normalized = str(chunk_meeting_id)
                                
                                # Store first chunk metadata for each meeting
                                # Store under multiple key formats for lookup flexibility
                                if chunk_meeting_id_normalized not in chunk_metadata_cache:
                                    # Try to get semantic chunking metadata (Phase 7)
                                    # If not available, infer from available metadata
                                    chunk_type = chunk_meta.get("chunk_type")
                                    entities = chunk_meta.get("entities")
                                    relationships = chunk_meta.get("relationships")
                                    
                                    # If semantic chunking metadata not available, try to infer from tags
                                    if not chunk_type and chunk_meta.get("tags"):
                                        tags = chunk_meta.get("tags", {})
                                        topics_covered_str = tags.get("topicsCovered", "")
                                        # Infer chunk type from content - if it has decisions, it might be a decision record
                                        if chunk_meta.get("decisions"):
                                            chunk_type = "decision_record"
                                        else:
                                            chunk_type = "meeting_summary"
                                    
                                    # Extract entities from tags if available
                                    if not entities and chunk_meta.get("tags"):
                                        tags = chunk_meta.get("tags", {})
                                        topics_covered_str = tags.get("topicsCovered", "")
                                        if topics_covered_str:
                                            # Create simple entity entries from topics
                                            topic_list = [t.strip() for t in topics_covered_str.split(",") if t.strip()]
                                            entities = [
                                                {"normalized_name": topic, "entity_type": "TOPIC"}
                                                for topic in topic_list[:5]  # Limit to 5 topics
                                            ]
                                    
                                    metadata_entry = {
                                        "chunk_type": chunk_type,
                                        "entities": entities,
                                        "relationships": relationships
                                    }
                                    # Store under normalized key
                                    chunk_metadata_cache[chunk_meeting_id_normalized] = metadata_entry
                                    # Also store under original key if different
                                    if chunk_meeting_id_normalized != str(chunk_meeting_id):
                                        chunk_metadata_cache[str(chunk_meeting_id)] = metadata_entry
                        logger.info("topic_query_chunk_metadata_loaded", 
                                   cache_size=len(chunk_metadata_cache),
                                   meetings_count=len(meetings),
                                   sample_meeting_ids=list(chunk_metadata_cache.keys())[:3] if chunk_metadata_cache else [])
                    except Exception as e:
                        logger.warning("topic_query_chunk_metadata_load_failed", error=str(e), index_name=index_name)
                        # Continue without chunk metadata if index load fails
                    
                    for meeting in meetings[:10]:  # Limit to 10 meetings for citations
                        # Format date as YYYY-MM-DD
                        if hasattr(meeting.date, 'isoformat'):
                            date_str = meeting.date.isoformat()
                        elif hasattr(meeting.date, 'strftime'):
                            date_str = meeting.date.strftime('%Y-%m-%d')
                        else:
                            date_str = str(meeting.date)
                        
                        # Extract just the date part if it's a datetime
                        if 'T' in date_str:
                            date_str = date_str.split('T')[0]
                        
                        # Try to get chunk metadata for this meeting
                        # Try both UUID string formats (with and without dashes)
                        meeting_id_str = str(meeting.id)
                        meeting_id_str_no_dash = meeting_id_str.replace('-', '')
                        chunk_meta = chunk_metadata_cache.get(meeting_id_str, {})
                        if not chunk_meta:
                            # Try without dashes
                            chunk_meta = chunk_metadata_cache.get(meeting_id_str_no_dash, {})
                        if not chunk_meta:
                            # Try with lowercase
                            chunk_meta = chunk_metadata_cache.get(meeting_id_str.lower(), {})
                        if not chunk_meta:
                            # Try with uppercase
                            chunk_meta = chunk_metadata_cache.get(meeting_id_str.upper(), {})
                        
                        # Log if we found chunk metadata
                        if chunk_meta and chunk_meta.get("chunk_type"):
                            logger.debug("topic_query_citation_with_chunk_metadata",
                                       meeting_id=meeting_id_str,
                                       chunk_type=chunk_meta.get("chunk_type"),
                                       has_entities=bool(chunk_meta.get("entities")),
                                       has_relationships=bool(chunk_meta.get("relationships")))
                        elif not chunk_meta:
                            logger.debug("topic_query_citation_no_chunk_metadata",
                                       meeting_id=meeting_id_str,
                                       cache_size=len(chunk_metadata_cache),
                                       sample_keys=list(chunk_metadata_cache.keys())[:3] if chunk_metadata_cache else [])
                        
                        citations.append(Citation(
                            meeting_id=meeting_id_str,
                            date=date_str,
                            workgroup_name=workgroup_name,
                            excerpt=f"Meeting on {date_str}",
                            chunk_type=chunk_meta.get("chunk_type") if chunk_meta else None,
                            chunk_entities=chunk_meta.get("entities") if chunk_meta else None,
                            chunk_relationships=chunk_meta.get("relationships") if chunk_meta else None
                        ))
                    
                    # Format response
                    if topics:
                        year_context = f" in {year}" if year else ""
                        response_lines = [f"The {workgroup_name} has discussed the following topics{year_context}:\n"]
                        for topic in topics:
                            response_lines.append(f"- {topic}")
                        answer_text = "\n".join(response_lines)
                    else:
                        year_context = f" in {year}" if year else ""
                        answer_text = f"The {workgroup_name} has no topics recorded{year_context}."
                    
                    # Create RAGQuery response with citations from this workgroup only
                    rag_query = RAGQuery(
                        query_id=str(uuid.uuid4()),
                        user_input=query_text,
                        timestamp=datetime.utcnow().isoformat(),
                        retrieved_chunks=[],
                        output=answer_text,
                        citations=citations,  # Citations from this workgroup only
                        model_version="entity-query",
                        embedding_version="N/A",
                        user_id=user_id,
                        evidence_found=len(topics) > 0,
                        audit_log_path=""
                    )
                    return rag_query
                elif has_date_reference and not has_workgroup:
                    # Date-based topic query without workgroup - get topics from all meetings in that time period
                    from ..models.meeting import Meeting
                    from ..models.tag import Tag
                    from ..lib.config import ENTITIES_MEETINGS_DIR, ENTITIES_TAGS_DIR
                    from ..services.entity_storage import load_entity
                    from datetime import date
                    
                    # Get all meetings in the specified time period
                    all_meetings = entity_query.find_all(ENTITIES_MEETINGS_DIR, Meeting)
                    
                    # Filter by date
                    filtered_meetings = []
                    for meeting in all_meetings:
                        if not meeting.date:
                            continue
                        
                        meeting_date = meeting.date
                        if isinstance(meeting_date, str):
                            try:
                                meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00')).date()
                            except:
                                continue
                        elif isinstance(meeting_date, datetime):
                            meeting_date = meeting_date.date()
                        
                        # Filter by year
                        if year and meeting_date.year != year:
                            continue
                        
                        # Filter by month if specified
                        if month and meeting_date.month != month:
                            continue
                        
                        filtered_meetings.append(meeting)
                    
                    # Get all topics from tags for these meetings
                    topics_set = set()
                    meeting_topics_map = {}  # Map meeting_id to list of topics
                    
                    for tag_file in ENTITIES_TAGS_DIR.glob("*.json"):
                        try:
                            tag_id = UUID(tag_file.stem)
                            tag = load_entity(tag_id, ENTITIES_TAGS_DIR, Tag)
                            if not tag or not tag.topics_covered:
                                continue
                            
                            # Check if this tag belongs to one of our filtered meetings
                            if tag.meeting_id not in [m.id for m in filtered_meetings]:
                                continue
                            
                            # Extract topics
                            meeting_topics = []
                            if isinstance(tag.topics_covered, list):
                                for topic in tag.topics_covered:
                                    if topic:
                                        topic_str = str(topic).strip()
                                        topics_set.add(topic_str)
                                        meeting_topics.append(topic_str)
                            elif isinstance(tag.topics_covered, str):
                                for topic in tag.topics_covered.split(","):
                                    topic = topic.strip()
                                    if topic:
                                        topics_set.add(topic)
                                        meeting_topics.append(topic)
                            
                            if meeting_topics:
                                meeting_topics_map[tag.meeting_id] = meeting_topics
                        except (ValueError, AttributeError):
                            continue
                    
                    topics = sorted(list(topics_set))
                    
                    # Create citations from meetings that have topics
                    citations = []
                    for meeting in filtered_meetings:
                        if meeting.id in meeting_topics_map:
                            # Format date
                            if hasattr(meeting.date, 'isoformat'):
                                date_str = meeting.date.isoformat()
                            elif hasattr(meeting.date, 'strftime'):
                                date_str = meeting.date.strftime('%Y-%m-%d')
                            else:
                                date_str = str(meeting.date)
                            
                            if 'T' in date_str:
                                date_str = date_str.split('T')[0]
                            
                            # Get workgroup name
                            workgroup_name = "Unknown"
                            if meeting.workgroup_id:
                                from ..models.workgroup import Workgroup
                                from ..lib.config import ENTITIES_WORKGROUPS_DIR
                                workgroup = entity_query.get_by_id(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                                if workgroup:
                                    workgroup_name = workgroup.name
                            
                            citations.append(Citation(
                                meeting_id=str(meeting.id),
                                date=date_str,
                                workgroup_name=workgroup_name,
                                excerpt=f"Topics: {', '.join(meeting_topics_map[meeting.id][:3])}",
                                chunk_type="meeting_summary",
                                chunk_entities=[{"normalized_name": t, "entity_type": "TOPIC"} for t in meeting_topics_map[meeting.id][:5]],
                                chunk_relationships=None
                            ))
                    
                    # Format response
                    if topics:
                        time_context = ""
                        if month and year:
                            month_name = ["January", "February", "March", "April", "May", "June",
                                        "July", "August", "September", "October", "November", "December"][month - 1]
                            time_context = f" in {month_name} {year}"
                        elif year:
                            time_context = f" in {year}"
                        elif month:
                            month_name = ["January", "February", "March", "April", "May", "June",
                                        "July", "August", "September", "October", "November", "December"][month - 1]
                            time_context = f" in {month_name}"
                        
                        response_lines = [f"The following topics were discussed{time_context}:\n"]
                        for topic in topics:
                            response_lines.append(f"- {topic}")
                        answer_text = "\n".join(response_lines)
                    else:
                        time_context = ""
                        if month and year:
                            month_name = ["January", "February", "March", "April", "May", "June",
                                        "July", "August", "September", "October", "November", "December"][month - 1]
                            time_context = f" in {month_name} {year}"
                        elif year:
                            time_context = f" in {year}"
                        answer_text = f"No topics were recorded{time_context}."
                    
                    # Create RAGQuery response
                    rag_query = RAGQuery(
                        query_id=str(uuid.uuid4()),
                        user_input=query_text,
                        timestamp=datetime.utcnow().isoformat(),
                        retrieved_chunks=[],
                        output=answer_text,
                        citations=citations[:10],  # Limit citations
                        model_version="entity-query",
                        embedding_version="N/A",
                        user_id=user_id,
                        evidence_found=len(topics) > 0,
                        audit_log_path=""
                    )
                    return rag_query
                else:
                    # Workgroup not found and no date - fall through to RAG
                    logger.warning("topic_query_workgroup_not_found", query=query_text)
            
            if is_quantitative:
                # Use quantitative query service for accurate counts
                logger.info("quantitative_query_detected", query=query_text)
                
                # Try to extract source URL from question
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
                    
                    # If this is a workgroup-specific query, filter citations by workgroup
                    workgroup_id = quantitative_result.get("workgroup_id")
                    workgroup_name = quantitative_result.get("workgroup_name")
                    
                    if workgroup_id and workgroup_name and retrieved_chunks:
                        # Filter retrieved chunks to only include meetings from this workgroup
                        from ..services.entity_storage import load_entity
                        from ..models.meeting import Meeting
                        from ..lib.config import ENTITIES_MEETINGS_DIR
                        
                        filtered_chunks = []
                        for chunk in retrieved_chunks:
                            metadata = chunk.get("metadata", {})
                            meeting_id = metadata.get("meeting_id", chunk.get("meeting_id", ""))
                            
                            # Check if this meeting belongs to the target workgroup
                            try:
                                meeting_uuid = UUID(meeting_id)
                                meeting = load_entity(meeting_uuid, ENTITIES_MEETINGS_DIR, Meeting)
                                if meeting and meeting.workgroup_id:
                                    if str(meeting.workgroup_id) == workgroup_id:
                                        filtered_chunks.append(chunk)
                            except (ValueError, AttributeError, Exception):
                                # Skip chunks with invalid meeting IDs
                                continue
                        
                        # Use filtered chunks for citations
                        retrieved_chunks = filtered_chunks
                    
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
                    
                    # Citations will be extracted later in the general citation extraction section
                    # (after line 302 where citations is initialized)
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
                    # Apply date filtering for queries with date references before RAG generation
                    if has_date_reference:
                        year, month = extract_date_from_query(query_text)
                        if year is not None or month is not None:
                            original_count = len(retrieved_chunks)
                            retrieved_chunks = filter_chunks_by_date_range(
                                retrieved_chunks,
                                year=year,
                                month=month
                            )
                            if len(retrieved_chunks) < original_count:
                                logger.info(
                                    "chunks_filtered_by_date_from_query",
                                    year=year,
                                    month=month,
                                    original_chunks=original_count,
                                    filtered_chunks=len(retrieved_chunks)
                                )
                    
                    evidence_found = check_evidence(retrieved_chunks)
                    if evidence_found:
                        answer = rag_generator.generate(query_text, retrieved_chunks)
                    else:
                        answer = get_no_evidence_message()
            else:
                # Standard RAG query
                # Apply date filtering for queries with date references before RAG generation
                if has_date_reference:
                    year, month = extract_date_from_query(query_text)
                    if year is not None or month is not None:
                        original_count = len(retrieved_chunks)
                        retrieved_chunks = filter_chunks_by_date_range(
                            retrieved_chunks,
                            year=year,
                            month=month
                        )
                        if len(retrieved_chunks) < original_count:
                            logger.info(
                                "chunks_filtered_by_date_from_query",
                                year=year,
                                month=month,
                                original_chunks=original_count,
                                filtered_chunks=len(retrieved_chunks)
                            )
                        # If all chunks were filtered out, try to get meetings from entity storage
                        # This ensures we have valid citations even if FAISS chunks don't match
                        if len(retrieved_chunks) == 0 and original_count > 0:
                            logger.warning(
                                "all_chunks_filtered_by_date_in_rag_query",
                                year=year,
                                month=month,
                                original_chunks=original_count,
                                query=query_text[:100]
                            )
                            
                            # Try to get meetings from entity storage for this date range
                            try:
                                from ..services.entity_query import EntityQueryService
                                entity_query = EntityQueryService()
                                meetings = entity_query.get_meetings_by_date_range(year=year, month=month)
                                
                                if meetings:
                                    logger.info(
                                        "found_meetings_in_entity_storage_after_date_filter",
                                        year=year,
                                        month=month,
                                        meeting_count=len(meetings)
                                    )
                                    # Create chunks from these meetings for RAG
                                    # Use meeting summaries or decision items if available
                                    for meeting in meetings[:10]:  # Limit to 10 meetings
                                        # Create a minimal chunk structure from meeting
                                        meeting_id_str = str(meeting.id)
                                        date_str = meeting.date.isoformat() if hasattr(meeting.date, 'isoformat') else str(meeting.date)
                                        if 'T' in date_str:
                                            date_str = date_str.split('T')[0]
                                        
                                        # Get workgroup name
                                        workgroup_name = None
                                        if meeting.workgroup_id:
                                            from ..models.workgroup import Workgroup
                                            from ..lib.config import ENTITIES_WORKGROUPS_DIR
                                            workgroup = entity_query.get_by_id(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                                            if workgroup:
                                                workgroup_name = workgroup.name
                                        
                                        # Create chunk with meeting info
                                        chunk_text = f"Meeting on {date_str}"
                                        if workgroup_name:
                                            chunk_text += f" for {workgroup_name}"
                                        
                                        retrieved_chunks.append({
                                            "text": chunk_text,
                                            "meeting_id": meeting_id_str,
                                            "metadata": {
                                                "meeting_id": meeting_id_str,
                                                "date": date_str,
                                                "workgroup": workgroup_name
                                            },
                                            "score": 0.5,  # Lower score since not from semantic search
                                            "chunk_index": 0
                                        })
                            except Exception as e:
                                logger.warning(
                                    "failed_to_get_meetings_from_entity_storage",
                                    year=year,
                                    month=month,
                                    error=str(e)
                                )
                
                evidence_found = check_evidence(retrieved_chunks)
                
                if evidence_found:
                    answer = rag_generator.generate(query_text, retrieved_chunks)
                else:
                    answer = get_no_evidence_message()
            
            # Extract citations - ensure citations are ALWAYS present
            from ..services.citation_extractor import create_no_evidence_citation
            from ..services.answer_analyzer import filter_citations_for_negative_response, is_negative_response
            
            citations = []
            
            # For quantitative queries, add data source citations
            if is_quantitative and "count" in quantitative_result:
                # Add citation for quantitative analysis with proper format
                count = quantitative_result.get('count', 0)
                source = quantitative_result.get('source', 'entity storage')
                method = quantitative_result.get('method', 'Direct file count')
                
                # Check if this is a workgroup-specific query
                workgroup_id = quantitative_result.get("workgroup_id")
                workgroup_name = quantitative_result.get("workgroup_name")
                meetings = quantitative_result.get("meetings", [])  # List of Meeting objects
                
                # If we have the actual meetings list, create citations for each meeting
                if meetings and len(meetings) > 0:
                    # Try to load chunk metadata from FAISS index for semantic chunk context (Phase 7)
                    chunk_metadata_cache = {}  # Cache chunk metadata by meeting_id
                    
                    # Try to load index to get chunk metadata (Phase 7: semantic chunk context)
                    try:
                        index, embedding_index = load_index(index_name)
                        # Build cache of chunk metadata by meeting_id
                        # Use first chunk found for each meeting (or could aggregate)
                        for idx, chunk_meta in embedding_index.metadata.items():
                            chunk_meeting_id = chunk_meta.get("meeting_id", "")
                            if chunk_meeting_id:
                                # Normalize meeting_id to string format (handle both UUID and string)
                                chunk_meeting_id_normalized = str(chunk_meeting_id)
                                
                                # Store under multiple key formats for lookup flexibility
                                if chunk_meeting_id_normalized not in chunk_metadata_cache:
                                    # Try to get semantic chunking metadata (Phase 7)
                                    # If not available, infer from available metadata
                                    chunk_type = chunk_meta.get("chunk_type")
                                    entities = chunk_meta.get("entities")
                                    relationships = chunk_meta.get("relationships")
                                    
                                    # If semantic chunking metadata not available, try to infer from tags
                                    if not chunk_type and chunk_meta.get("tags"):
                                        tags = chunk_meta.get("tags", {})
                                        topics_covered_str = tags.get("topicsCovered", "")
                                        # Infer chunk type from content - if it has decisions, it might be a decision record
                                        if chunk_meta.get("decisions"):
                                            chunk_type = "decision_record"
                                        else:
                                            chunk_type = "meeting_summary"
                                    
                                    # Extract entities from tags if available
                                    if not entities and chunk_meta.get("tags"):
                                        tags = chunk_meta.get("tags", {})
                                        topics_covered_str = tags.get("topicsCovered", "")
                                        if topics_covered_str:
                                            # Create simple entity entries from topics
                                            topic_list = [t.strip() for t in topics_covered_str.split(",") if t.strip()]
                                            entities = [
                                                {"normalized_name": topic, "entity_type": "TOPIC"}
                                                for topic in topic_list[:5]  # Limit to 5 topics
                                            ]
                                    
                                    metadata_entry = {
                                        "chunk_type": chunk_type,
                                        "entities": entities,
                                        "relationships": relationships
                                    }
                                    # Store under normalized key
                                    chunk_metadata_cache[chunk_meeting_id_normalized] = metadata_entry
                                    # Also store under original key if different
                                    if chunk_meeting_id_normalized != str(chunk_meeting_id):
                                        chunk_metadata_cache[str(chunk_meeting_id)] = metadata_entry
                        logger.info("quantitative_query_chunk_metadata_loaded", 
                                   cache_size=len(chunk_metadata_cache),
                                   meetings_count=len(meetings),
                                   sample_meeting_ids=list(chunk_metadata_cache.keys())[:3] if chunk_metadata_cache else [])
                    except Exception as e:
                        logger.warning("quantitative_query_chunk_metadata_load_failed", error=str(e), index_name=index_name)
                        # Continue without chunk metadata if index load fails
                    
                    # Create citations directly from Meeting objects with chunk metadata
                    for meeting in meetings:
                        # Format date as YYYY-MM-DD
                        if hasattr(meeting.date, 'isoformat'):
                            date_str = meeting.date.isoformat()
                        elif hasattr(meeting.date, 'strftime'):
                            date_str = meeting.date.strftime('%Y-%m-%d')
                        else:
                            date_str = str(meeting.date)
                        
                        # Extract just the date part if it's a datetime
                        if 'T' in date_str:
                            date_str = date_str.split('T')[0]
                        
                        # Try to get chunk metadata for this meeting
                        # Try both UUID string formats (with and without dashes)
                        meeting_id_str = str(meeting.id)
                        meeting_id_str_no_dash = meeting_id_str.replace('-', '')
                        chunk_meta = chunk_metadata_cache.get(meeting_id_str, {})
                        if not chunk_meta:
                            # Try without dashes
                            chunk_meta = chunk_metadata_cache.get(meeting_id_str_no_dash, {})
                        if not chunk_meta:
                            # Try with lowercase
                            chunk_meta = chunk_metadata_cache.get(meeting_id_str.lower(), {})
                        if not chunk_meta:
                            # Try with uppercase
                            chunk_meta = chunk_metadata_cache.get(meeting_id_str.upper(), {})
                        
                        # Log if we found chunk metadata
                        if chunk_meta and chunk_meta.get("chunk_type"):
                            logger.debug("quantitative_query_citation_with_chunk_metadata",
                                       meeting_id=meeting_id_str,
                                       chunk_type=chunk_meta.get("chunk_type"),
                                       has_entities=bool(chunk_meta.get("entities")),
                                       has_relationships=bool(chunk_meta.get("relationships")))
                        elif not chunk_meta:
                            logger.debug("quantitative_query_citation_no_chunk_metadata",
                                       meeting_id=meeting_id_str,
                                       cache_size=len(chunk_metadata_cache),
                                       sample_keys=list(chunk_metadata_cache.keys())[:3] if chunk_metadata_cache else [])
                        
                        citations.append(Citation(
                            meeting_id=meeting_id_str,
                            date=date_str,
                            workgroup_name=workgroup_name,
                            excerpt=f"Meeting on {date_str}",
                            chunk_type=chunk_meta.get("chunk_type") if chunk_meta else None,
                            chunk_entities=chunk_meta.get("entities") if chunk_meta else None,
                            chunk_relationships=chunk_meta.get("relationships") if chunk_meta else None
                        ))
                else:
                    # Fallback: Create citation showing the counting process
                    # Include workgroup name if this is a workgroup-specific query
                    citations.append(Citation(
                        meeting_id="entity-storage",
                        date=datetime.utcnow().strftime("%Y-%m-%d"),
                        workgroup_name=workgroup_name,  # Use workgroup name if available
                        excerpt=f"Counted {count} meetings by scanning JSON files in {source}. Method: {method}."
                    ))
                
                # Also include any existing retrieved chunks as additional context
                # But filter by workgroup if this is a workgroup-specific query
                if workgroup_id and workgroup_name and retrieved_chunks:
                    # Filter chunks by workgroup before extracting citations
                    # Optimize: Use workgroup from metadata if available, only load meeting if needed
                    from ..services.entity_storage import load_entity
                    from ..models.meeting import Meeting
                    from ..lib.config import ENTITIES_MEETINGS_DIR
                    
                    filtered_chunks = []
                    workgroup_id_str = str(workgroup_id)
                    
                    for chunk in retrieved_chunks:
                        metadata = chunk.get("metadata", {})
                        meeting_id = metadata.get("meeting_id", chunk.get("meeting_id", ""))
                        
                        # Try to get workgroup from metadata first (faster)
                        chunk_workgroup_id = metadata.get("workgroup_id")
                        if chunk_workgroup_id and str(chunk_workgroup_id) == workgroup_id_str:
                            filtered_chunks.append(chunk)
                            continue
                        
                        # Fallback: Load meeting to check workgroup_id (slower)
                        try:
                            meeting_uuid = UUID(meeting_id)
                            meeting = load_entity(meeting_uuid, ENTITIES_MEETINGS_DIR, Meeting)
                            if meeting and meeting.workgroup_id:
                                if str(meeting.workgroup_id) == workgroup_id_str:
                                    filtered_chunks.append(chunk)
                        except (ValueError, AttributeError, Exception):
                            # Skip chunks with invalid meeting IDs
                            continue
                    
                    # Extract citations only from filtered chunks (with relevance filtering)
                    existing_citations = extract_citations(
                        filtered_chunks,
                        min_score=0.0,
                        filter_by_relevance=True
                    )
                else:
                    # Extract citations from all retrieved chunks (no workgroup filter, but with relevance filtering)
                    existing_citations = extract_citations(
                        retrieved_chunks,
                        min_score=0.0,
                        filter_by_relevance=True
                    )
                
                citations.extend(existing_citations)
            elif is_quantitative and "answer" in quantitative_result:
                # Statistical or other quantitative query
                source = quantitative_result.get('source', 'entity storage')
                method = quantitative_result.get('method', 'Quantitative analysis')
                
                # If quantitative result includes actual meetings, create citations from them
                meetings = quantitative_result.get("meetings", [])
                if meetings and len(meetings) > 0:
                    # Create citations from actual meetings (valid meeting IDs)
                    from ..models.workgroup import Workgroup
                    from ..lib.config import ENTITIES_WORKGROUPS_DIR
                    from ..services.entity_storage import load_entity
                    
                    for meeting in meetings:
                        # Format date
                        if hasattr(meeting.date, 'isoformat'):
                            date_str = meeting.date.isoformat()
                        elif hasattr(meeting.date, 'strftime'):
                            date_str = meeting.date.strftime('%Y-%m-%d')
                        else:
                            date_str = str(meeting.date)
                        
                        if 'T' in date_str:
                            date_str = date_str.split('T')[0]
                        
                        # Get workgroup name
                        workgroup_name = None
                        if meeting.workgroup_id:
                            workgroup = load_entity(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                            if workgroup:
                                workgroup_name = workgroup.name
                        
                        citations.append(Citation(
                            meeting_id=str(meeting.id),
                            date=date_str,
                            workgroup_name=workgroup_name,
                            excerpt=f"Meeting included in quantitative analysis: {method}"
                        ))
                else:
                    # No meetings available, create a system citation (will be filtered but at least documented)
                    citations.append(Citation(
                        meeting_id="quantitative-analysis",
                        date=datetime.utcnow().strftime("%Y-%m-%d"),
                        workgroup_name=None,
                        excerpt=f"Quantitative analysis performed. Method: {method}. Source: {source}."
                    ))
                
                # Include any additional citations from quantitative result
                if "citations" in quantitative_result:
                    for cit in quantitative_result["citations"]:
                        if isinstance(cit, dict):
                            # Only add if it's not a duplicate of meeting citations we already added
                            cit_type = cit.get("type", "quantitative")
                            if cit_type not in ("quantitative", "data_source", "info"):
                                citations.append(Citation(
                                    meeting_id=cit_type,
                                    date=datetime.utcnow().strftime("%Y-%m-%d"),
                                    workgroup_name=None,
                                    excerpt=cit.get("description", f"Method: {cit.get('method', method)}")
                                ))
            else:
                # Standard RAG query - extract citations from chunks (with relevance filtering)
                citations = extract_citations(
                    retrieved_chunks,
                    min_score=0.0,
                    filter_by_relevance=True
                )
                
                # If meeting ID was specified in query, filter citations to only that meeting
                # This ensures queries like "What did meeting X say about Y?" only return citations from meeting X
                if meeting_id_from_query:
                    filtered_citations = []
                    meeting_id_normalized = str(meeting_id_from_query).lower()
                    
                    for citation in citations:
                        citation_meeting_id = str(citation.meeting_id).lower()
                        
                        # Try exact match
                        if citation_meeting_id == meeting_id_normalized:
                            filtered_citations.append(citation)
                            continue
                        
                        # Try UUID comparison (handles different string formats)
                        try:
                            citation_uuid = UUID(citation_meeting_id)
                            query_uuid = UUID(meeting_id_normalized)
                            if citation_uuid == query_uuid:
                                filtered_citations.append(citation)
                        except (ValueError, AttributeError):
                            # Skip citations with invalid meeting IDs
                            continue
                    
                    if len(filtered_citations) < len(citations):
                        logger.info(
                            "citations_filtered_by_meeting_id",
                            meeting_id=meeting_id_from_query,
                            original_citations=len(citations),
                            filtered_citations=len(filtered_citations)
                        )
                    citations = filtered_citations
                
                # If no citations found and we have a date filter, try to get citations from entity storage
                if not citations and has_date_reference:
                    year, month = extract_date_from_query(query_text)
                    if year is not None or month is not None:
                        try:
                            from ..services.entity_query import EntityQueryService
                            entity_query = EntityQueryService()
                            meetings = entity_query.get_meetings_by_date_range(year=year, month=month)
                            
                            if meetings:
                                logger.info(
                                    "creating_citations_from_entity_storage_after_date_filter",
                                    year=year,
                                    month=month,
                                    meeting_count=len(meetings)
                                )
                                
                                # Try to load chunk metadata from FAISS index for entity extraction metadata
                                chunk_metadata_cache = {}
                                try:
                                    index, embedding_index = load_index(index_name)
                                    # Build cache of chunk metadata by meeting_id
                                    for idx, chunk_meta in embedding_index.metadata.items():
                                        chunk_meeting_id = chunk_meta.get("meeting_id", "")
                                        if chunk_meeting_id:
                                            chunk_meeting_id_str = str(chunk_meeting_id)
                                            if chunk_meeting_id_str not in chunk_metadata_cache:
                                                chunk_metadata_cache[chunk_meeting_id_str] = {
                                                    "chunk_type": chunk_meta.get("chunk_type"),
                                                    "entities": chunk_meta.get("entities"),
                                                    "relationships": chunk_meta.get("relationships")
                                                }
                                except Exception as e:
                                    logger.debug("chunk_metadata_cache_load_failed_for_entity_storage_citations", error=str(e))
                                
                                # Create citations directly from meetings with chunk metadata if available
                                for meeting in meetings[:10]:  # Limit to 10 meetings
                                    meeting_id_str = str(meeting.id)
                                    date_str = meeting.date.isoformat() if hasattr(meeting.date, 'isoformat') else str(meeting.date)
                                    if 'T' in date_str:
                                        date_str = date_str.split('T')[0]
                                    
                                    # Get workgroup name
                                    workgroup_name = None
                                    if meeting.workgroup_id:
                                        from ..models.workgroup import Workgroup
                                        from ..lib.config import ENTITIES_WORKGROUPS_DIR
                                        workgroup = entity_query.get_by_id(meeting.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                                        if workgroup:
                                            workgroup_name = workgroup.name
                                    
                                    # Try to get chunk metadata for this meeting
                                    chunk_meta = chunk_metadata_cache.get(meeting_id_str, {})
                                    if not chunk_meta:
                                        # Try without dashes
                                        chunk_meta = chunk_metadata_cache.get(meeting_id_str.replace('-', ''), {})
                                    if not chunk_meta:
                                        # Try with lowercase
                                        chunk_meta = chunk_metadata_cache.get(meeting_id_str.lower(), {})
                                    
                                    # If no chunk metadata found, infer chunk_type from query
                                    chunk_type = chunk_meta.get("chunk_type") if chunk_meta else None
                                    chunk_entities = chunk_meta.get("entities") if chunk_meta else None
                                    chunk_relationships = chunk_meta.get("relationships") if chunk_meta else None
                                    
                                    # Always ensure chunk_type is set (required for citation verification)
                                    # Must be a non-empty string, not None
                                    if not chunk_type or chunk_type == "":
                                        # For decision queries, use decision_record
                                        if "decision" in query_text.lower():
                                            chunk_type = "decision_record"
                                        else:
                                            chunk_type = "meeting_summary"
                                    
                                    # Ensure chunk_type is a string (not None)
                                    chunk_type = str(chunk_type) if chunk_type else "meeting_summary"
                                    
                                    # If no entities found, try to get topics from tags
                                    if not chunk_entities:
                                        try:
                                            from ..models.tag import Tag
                                            from ..lib.config import ENTITIES_TAGS_DIR
                                            from ..services.entity_storage import load_entity
                                            from uuid import UUID
                                            
                                            # Look for tags for this meeting
                                            for tag_file in ENTITIES_TAGS_DIR.glob("*.json"):
                                                try:
                                                    tag_id = UUID(tag_file.stem)
                                                    tag = load_entity(tag_id, ENTITIES_TAGS_DIR, Tag)
                                                    if tag and tag.meeting_id == meeting.id and tag.topics_covered:
                                                        # Extract topics as entities
                                                        topics = []
                                                        if isinstance(tag.topics_covered, list):
                                                            topics = [str(t).strip() for t in tag.topics_covered if t]
                                                        elif isinstance(tag.topics_covered, str):
                                                            topics = [t.strip() for t in tag.topics_covered.split(",") if t.strip()]
                                                        
                                                        if topics:
                                                            chunk_entities = [
                                                                {"normalized_name": topic, "entity_type": "TOPIC"}
                                                                for topic in topics[:5]  # Limit to 5 topics
                                                            ]
                                                            break
                                                except (ValueError, AttributeError):
                                                    continue
                                        except Exception as e:
                                            logger.debug("failed_to_load_tags_for_citation_entities", meeting_id=meeting_id_str, error=str(e))
                                    
                                    # Create citation with explicit chunk_type (required for verification)
                                    # chunk_type must be a non-empty string
                                    citation = Citation(
                                        meeting_id=meeting_id_str,
                                        date=date_str,
                                        workgroup_name=workgroup_name,
                                        excerpt=f"Meeting on {date_str}" + (f" for {workgroup_name}" if workgroup_name else ""),
                                        chunk_type=chunk_type,  # Always a non-empty string
                                        chunk_entities=chunk_entities if chunk_entities else None,
                                        chunk_relationships=chunk_relationships if chunk_relationships else None
                                    )
                                    
                                    logger.debug(
                                        "citation_created_from_entity_storage",
                                        meeting_id=meeting_id_str,
                                        chunk_type=citation.chunk_type,
                                        chunk_type_is_none=citation.chunk_type is None,
                                        chunk_type_empty=citation.chunk_type == "" if citation.chunk_type else True,
                                        has_entities=bool(citation.chunk_entities),
                                        has_relationships=bool(citation.chunk_relationships)
                                    )
                                    
                                    citations.append(citation)
                        except Exception as e:
                            logger.warning(
                                "failed_to_create_citations_from_entity_storage",
                                year=year,
                                month=month,
                                error=str(e)
                            )
                
                # If still no citations found, add no-evidence citation
                if not citations:
                    citations.append(create_no_evidence_citation(index_name))
            
            # Filter citations if answer indicates no information was found
            # This prevents showing citations when the LLM says "no specific mention"
            citations = filter_citations_for_negative_response(citations, answer)
            
            # If citations were filtered out due to negative response, update evidence_found
            if not citations and is_negative_response(answer):
                evidence_found = False
                # Use a more informative message
                answer = get_no_evidence_message()
            
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


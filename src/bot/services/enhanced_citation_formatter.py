"""Enhanced citation formatter service for citations with entity context."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from ...models.rag_query import Citation
from ...services.entity_normalization import EntityNormalizationService
from ...services.relationship_triple_generator import RelationshipTripleGenerator
from ...services.chunking import chunk_by_semantic_unit
from ...services.entity_query import EntityQueryService
from ...lib.config import ENTITIES_MEETINGS_DIR
from ...models.meeting import Meeting
from ...models.meeting_record import MeetingRecord
from ...lib.logging import get_logger
from ..models.enhanced_citation import EnhancedCitation

logger = get_logger(__name__)


class EnhancedCitationFormatter:
    """
    Service for formatting citations with enhanced entity context.
    
    Enhances citations with:
    - Normalized entity names (canonical names)
    - Relationship triples (Subject -> Relationship -> Object)
    - Semantic chunk type and metadata
    """
    
    def __init__(
        self,
        normalization_service: Optional[EntityNormalizationService] = None,
        relationship_generator: Optional[RelationshipTripleGenerator] = None,
        entity_query_service: Optional[EntityQueryService] = None,
    ):
        """
        Initialize enhanced citation formatter.
        
        Args:
            normalization_service: Optional EntityNormalizationService instance
            relationship_generator: Optional RelationshipTripleGenerator instance
            entity_query_service: Optional EntityQueryService instance
        """
        self.normalization_service = normalization_service or EntityNormalizationService()
        self.relationship_generator = relationship_generator or RelationshipTripleGenerator()
        self.entity_query_service = entity_query_service or EntityQueryService()
        
        # Phase 7: T058 - Cache for chunk metadata to ensure efficient loading
        self._chunk_metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._index_cache: Optional[Any] = None
        self._index_name_cache: Optional[str] = None
        
        logger.info("enhanced_citation_formatter_initialized")
    
    def format_citation(
        self,
        citation: Citation,
        meeting_id: Optional[UUID] = None,
    ) -> str:
        """
        Format a citation with enhanced entity context.
        
        Args:
            citation: Base Citation model
            meeting_id: Optional UUID of the meeting (will be parsed from citation.meeting_id if not provided)
            
        Returns:
            Formatted citation string with entity context
        """
        # Phase 8: T064 - Logging for enhanced citation formatting
        logger.debug(
            "enhanced_citation_formatting_start",
            citation_id=citation.meeting_id,
            meeting_id=str(meeting_id) if meeting_id else "unknown",
            has_chunk_type=bool(citation.chunk_type),
            has_chunk_entities=bool(citation.chunk_entities),
            has_chunk_relationships=bool(citation.chunk_relationships)
        )
        try:
            # Handle quantitative query citations (entity-storage, quantitative-analysis, etc.)
            if citation.meeting_id in ("entity-storage", "quantitative-analysis", "no-evidence"):
                workgroup_name = citation.workgroup_name or "unknown"
                # Try to extract count from excerpt for quantitative queries
                import re
                count_match = re.search(r'Counted (\d+)', citation.excerpt)
                if count_match and workgroup_name != "unknown":
                    count = count_match.group(1)
                    return f"[{citation.meeting_id} | {citation.date} | {workgroup_name}: {count} meetings]"
                elif workgroup_name != "unknown":
                    return f"[{citation.meeting_id} | {citation.date} | {workgroup_name}]"
                else:
                    return f"[{citation.meeting_id} | {citation.date} | {workgroup_name}]"
            
            # Parse meeting_id from citation if not provided
            if not meeting_id:
                try:
                    meeting_id = UUID(citation.meeting_id)
                except (ValueError, AttributeError):
                    logger.debug("enhanced_citation_invalid_meeting_id", meeting_id=citation.meeting_id)
                    # Fallback to basic format
                    workgroup_name = citation.workgroup_name or "unknown"
                    return f"[{citation.meeting_id} | {citation.date} | {workgroup_name}]"
            
            # Load meeting to get context
            meeting = self.entity_query_service.get_by_id(
                meeting_id,
                ENTITIES_MEETINGS_DIR,
                Meeting
            )
            
            if not meeting:
                # Fallback to basic format if meeting not found
                workgroup_name = citation.workgroup_name or "unknown"
                return f"[{citation.meeting_id} | {citation.date} | {workgroup_name}]"
            
            # Get normalized workgroup name
            workgroup_name = citation.workgroup_name or "unknown"
            if meeting.workgroup_id:
                from ...lib.config import ENTITIES_WORKGROUPS_DIR
                from ...models.workgroup import Workgroup
                try:
                    workgroup = self.entity_query_service.get_by_id(
                        meeting.workgroup_id,
                        ENTITIES_WORKGROUPS_DIR,
                        Workgroup
                    )
                    if workgroup:
                        # Normalize workgroup name
                        try:
                            _, normalized_name = self.normalization_service.normalize_entity_name(
                                workgroup.name,
                                existing_entities=None,
                                context={"workgroup_id": meeting.workgroup_id}
                            )
                            workgroup_name = normalized_name
                        except Exception as norm_error:
                            # Phase 8: T059 - Error handling for missing entity data
                            logger.debug(
                                "enhanced_citation_workgroup_normalization_failed",
                                workgroup_id=str(meeting.workgroup_id),
                                workgroup_name=workgroup.name if workgroup else "unknown",
                                error=str(norm_error)
                            )
                            # Use workgroup name as-is if normalization fails
                            workgroup_name = workgroup.name if workgroup else workgroup_name
                    else:
                        # Phase 8: T059 - Error handling for missing entity data
                        logger.debug(
                            "enhanced_citation_workgroup_not_found",
                            workgroup_id=str(meeting.workgroup_id),
                            meeting_id=str(meeting_id)
                        )
                except Exception as entity_error:
                    # Phase 8: T059 - Error handling for missing entity data
                    logger.debug(
                        "enhanced_citation_workgroup_load_failed",
                        workgroup_id=str(meeting.workgroup_id),
                        error=str(entity_error)
                    )
            
            # Start with basic citation format
            citation_parts = [citation.meeting_id, citation.date, workgroup_name]
            
            # Add semantic chunk metadata (Phase 7: T055-T057)
            # Phase 8: T061 - Error handling for missing chunk metadata
            chunk_type = citation.chunk_type
            chunk_entities = citation.chunk_entities or []
            chunk_relationships = citation.chunk_relationships or []
            
            # Log if chunk metadata is missing
            if not chunk_type and not chunk_entities and not chunk_relationships:
                logger.debug(
                    "enhanced_citation_chunk_metadata_missing",
                    meeting_id=str(meeting_id),
                    citation_id=citation.meeting_id
                )
            
            # Build enhanced citation with chunk context
            base_citation = f"[{citation_parts[0]} | {citation_parts[1]} | {citation_parts[2]}]"
            
            # Add chunk type if available
            if chunk_type:
                # Map chunk types to readable labels
                chunk_type_labels = {
                    "meeting_summary": "summary",
                    "decision_record": "decision",
                    "action_item": "action",
                    "attendance": "attendance",
                    "resource": "resource"
                }
                chunk_label = chunk_type_labels.get(chunk_type, chunk_type)
                base_citation += f" ({chunk_label})"
            
            # Add key entities if available (limit to 3 to keep it concise)
            # Phase 8: T061 - Error handling for missing chunk metadata
            if chunk_entities and len(chunk_entities) > 0:
                try:
                    entity_names = []
                    for entity in chunk_entities[:3]:  # Limit to first 3 entities
                        if not isinstance(entity, dict):
                            logger.debug(
                                "enhanced_citation_invalid_entity_format",
                                entity_type=type(entity).__name__,
                                meeting_id=str(meeting_id)
                            )
                            continue
                        normalized_name = entity.get("normalized_name") or entity.get("entity_id", "")
                        if normalized_name:
                            entity_names.append(normalized_name)
                    
                    if entity_names:
                        entities_str = ", ".join(entity_names)
                        if len(chunk_entities) > 3:
                            entities_str += f" (+{len(chunk_entities) - 3} more)"
                        base_citation += f" - Entities: {entities_str}"
                except Exception as entity_error:
                    # Phase 8: T061 - Error handling for missing chunk metadata
                    logger.debug(
                        "enhanced_citation_entity_formatting_failed",
                        meeting_id=str(meeting_id),
                        error=str(entity_error)
                    )
            
            # Phase 7: T057 - Display relationship context from chunk metadata
            # Phase 8: T060 - Error handling for missing relationship triples
            if chunk_relationships and len(chunk_relationships) > 0:
                try:
                    # Format relationships concisely (limit to 2 most relevant)
                    relationship_strs = []
                    for rel in chunk_relationships[:2]:  # Limit to first 2 relationships
                        if not isinstance(rel, dict):
                            logger.debug(
                                "enhanced_citation_invalid_relationship_format",
                                relationship_type=type(rel).__name__,
                                meeting_id=str(meeting_id)
                            )
                            continue
                        subject = rel.get("subject", "")
                        relationship = rel.get("relationship", "")
                        obj = rel.get("object", "")
                        if subject and relationship and obj:
                            # Format as "Subject → Relationship → Object"
                            relationship_strs.append(f"{subject} → {relationship} → {obj}")
                    
                    if relationship_strs:
                        rels_str = "; ".join(relationship_strs)
                        if len(chunk_relationships) > 2:
                            rels_str += f" (+{len(chunk_relationships) - 2} more)"
                        base_citation += f" - {rels_str}"
                except Exception as rel_error:
                    # Phase 8: T060 - Error handling for missing relationship triples
                    logger.debug(
                        "enhanced_citation_relationship_formatting_failed",
                        meeting_id=str(meeting_id),
                        error=str(rel_error)
                    )
            
            # Phase 8: T064 - Logging for enhanced citation formatting
            logger.debug(
                "enhanced_citation_formatting_success",
                citation_id=citation.meeting_id,
                meeting_id=str(meeting_id) if meeting_id else "unknown",
                citation_length=len(base_citation),
                has_chunk_type=bool(chunk_type),
                entity_count=len(chunk_entities) if chunk_entities else 0,
                relationship_count=len(chunk_relationships) if chunk_relationships else 0
            )
            return base_citation
            
        except Exception as e:
            # Phase 8: T064 - Enhanced logging for citation formatting
            logger.warning(
                "enhanced_citation_formatting_failed",
                error=str(e),
                citation_id=citation.meeting_id,
                meeting_id=str(meeting_id) if meeting_id else "unknown",
                error_type=type(e).__name__
            )
            # Fallback to basic format
            workgroup_name = citation.workgroup_name or "unknown"
            return f"[{citation.meeting_id} | {citation.date} | {workgroup_name}]"
    
    def format_enhanced_citation(
        self,
        citation: Citation,
        meeting_id: Optional[UUID] = None,
    ) -> EnhancedCitation:
        """
        Format a citation as an EnhancedCitation model with full entity context.
        
        Args:
            citation: Base Citation model
            meeting_id: Optional UUID of the meeting
            
        Returns:
            EnhancedCitation with normalized entities, relationships, and chunk metadata
        """
        # Parse meeting_id
        if not meeting_id:
            try:
                meeting_id = UUID(citation.meeting_id)
            except (ValueError, AttributeError):
                logger.debug("enhanced_citation_invalid_meeting_id", meeting_id=citation.meeting_id)
                # Return basic enhanced citation
                return EnhancedCitation(
                    meeting_id=citation.meeting_id,
                    date=citation.date,
                    workgroup_name=citation.workgroup_name,
                    excerpt=citation.excerpt,
                )
        
        # Get normalized workgroup name (default to citation value)
        workgroup_name = citation.workgroup_name or "unknown"
        
        # Load meeting and entities
        meeting = self.entity_query_service.get_by_id(
            meeting_id,
            ENTITIES_MEETINGS_DIR,
            Meeting
        )
        
        normalized_entities = []
        relationship_triples = []
        
        # Load chunk metadata from citation (Phase 7: T054)
        chunk_type = citation.chunk_type
        chunk_entities = []
        chunk_relationships = []
        
        # Extract chunk entities from citation metadata
        if citation.chunk_entities:
            chunk_entities = [
                {
                    "entity_id": e.get("entity_id", ""),
                    "entity_type": e.get("entity_type", ""),
                    "normalized_name": e.get("normalized_name", ""),
                    "mentions": e.get("mentions", [])
                }
                for e in citation.chunk_entities
            ]
        
        # Extract chunk relationships from citation metadata
        if citation.chunk_relationships:
            chunk_relationships = [
                {
                    "subject": r.get("subject", ""),
                    "relationship": r.get("relationship", ""),
                    "object": r.get("object", "")
                }
                for r in citation.chunk_relationships
            ]
        
        if meeting:
            # Get normalized workgroup name
            if meeting.workgroup_id:
                # Load and normalize workgroup
                from ...lib.config import ENTITIES_WORKGROUPS_DIR
                from ...models.workgroup import Workgroup
                workgroup = self.entity_query_service.get_by_id(
                    meeting.workgroup_id,
                    ENTITIES_WORKGROUPS_DIR,
                    Workgroup
                )
                if workgroup:
                    _, normalized_name = self.normalization_service.normalize_entity_name(
                        workgroup.name,
                        existing_entities=None,
                        context={"workgroup_id": meeting.workgroup_id}
                    )
                    workgroup_name = normalized_name
                    normalized_entities.append({
                        "entity_id": str(workgroup.id),
                        "entity_type": "Workgroup",
                        "canonical_name": normalized_name,
                        "variations": [workgroup.name]  # Will be enhanced with actual variations
                    })
            
            # Load relationship triples for this meeting
            try:
                # Load entities for meeting
                from ...services.chunking import _load_meeting_entities
                entities = _load_meeting_entities(meeting_id)
                
                # Generate relationship triples
                triples = self.relationship_generator.generate_triples(entities, meeting_id)
                relationship_triples = [
                    {
                        "subject": t.subject_type,
                        "relationship": t.relationship,
                        "object": t.object_type,
                    }
                    for t in triples
                ]
            except Exception as e:
                logger.debug("enhanced_citation_relationships_failed", error=str(e))
        
        # Phase 7: T054 - Load chunk metadata from storage if not in citation
        # If chunk metadata is missing, try to load from FAISS index
        if not chunk_type and not chunk_entities and not chunk_relationships:
            chunk_metadata = self._load_chunk_metadata_from_storage(meeting_id)
            if chunk_metadata:
                chunk_type = chunk_metadata.get("chunk_type")
                if chunk_metadata.get("entities"):
                    chunk_entities = [
                        {
                            "entity_id": e.get("entity_id", ""),
                            "entity_type": e.get("entity_type", ""),
                            "normalized_name": e.get("normalized_name", ""),
                            "mentions": e.get("mentions", [])
                        }
                        for e in chunk_metadata.get("entities", [])
                    ]
                if chunk_metadata.get("relationships"):
                    chunk_relationships = [
                        {
                            "subject": r.get("subject", ""),
                            "relationship": r.get("relationship", ""),
                            "object": r.get("object", "")
                        }
                        for r in chunk_metadata.get("relationships", [])
                    ]
        
        return EnhancedCitation(
            meeting_id=citation.meeting_id,
            date=citation.date,
            workgroup_name=workgroup_name,
            excerpt=citation.excerpt,
            normalized_entities=normalized_entities,
            relationship_triples=relationship_triples,
            chunk_type=chunk_type,
            chunk_entities=chunk_entities,
        )


    def _load_chunk_metadata_from_storage(
        self,
        meeting_id: UUID,
        index_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 7: T054 - Load semantic chunk metadata from chunk storage (FAISS index).
        
        This method loads chunk metadata from the FAISS index if it's not already
        available in the Citation. Uses caching for efficient loading (T058).
        
        Args:
            meeting_id: UUID of the meeting
            index_name: Optional index name (if None, will try to infer from environment)
            
        Returns:
            Dictionary with chunk_type, entities, and relationships, or None if not found
        """
        try:
            # Phase 7: T058 - Check cache first for efficient loading
            cache_key = str(meeting_id)
            if cache_key in self._chunk_metadata_cache:
                logger.debug("chunk_metadata_cache_hit", meeting_id=cache_key)
                return self._chunk_metadata_cache[cache_key]
            
            # Try to load from FAISS index
            from ...services.retrieval import load_index
            import os
            
            # Get index name from environment or use default
            if not index_name:
                index_name = os.getenv("ARCHIVE_RAG_INDEX_PATH", "meetings")
            
            # Check if we already have this index loaded
            if self._index_name_cache != index_name or self._index_cache is None:
                try:
                    # Load index (this is cached per index name)
                    index, embedding_index = load_index(index_name)
                    self._index_cache = embedding_index
                    self._index_name_cache = index_name
                except (FileNotFoundError, ValueError) as e:
                    logger.debug("chunk_metadata_index_not_found", index_name=index_name, error=str(e))
                    return None
            
            # Search for chunk metadata for this meeting
            meeting_id_str = str(meeting_id)
            chunk_metadata = None
            
            # Search through embedding index metadata
            for idx, chunk_meta in self._index_cache.metadata.items():
                chunk_meeting_id = chunk_meta.get("meeting_id", "")
                if chunk_meeting_id and str(chunk_meeting_id) == meeting_id_str:
                    # Found matching chunk - extract metadata
                    chunk_metadata = {
                        "chunk_type": chunk_meta.get("chunk_type"),
                        "entities": chunk_meta.get("entities", []),
                        "relationships": chunk_meta.get("relationships", [])
                    }
                    break
            
            # Cache the result (even if None) for efficient loading
            self._chunk_metadata_cache[cache_key] = chunk_metadata
            
            if chunk_metadata:
                logger.debug("chunk_metadata_loaded_from_storage", meeting_id=cache_key)
            else:
                logger.debug("chunk_metadata_not_found_in_storage", meeting_id=cache_key)
            
            return chunk_metadata
            
        except Exception as e:
            logger.debug("chunk_metadata_load_failed", meeting_id=str(meeting_id), error=str(e))
            return None


def create_enhanced_citation_formatter() -> EnhancedCitationFormatter:
    """
    Create an enhanced citation formatter instance.
    
    Returns:
        EnhancedCitationFormatter instance
    """
    return EnhancedCitationFormatter()


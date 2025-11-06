"""Semantic chunking service for chunking text by semantic units with entity metadata."""

import re
from typing import List, Optional
from uuid import UUID

from src.lib.config import (
    CHUNKING_MAX_TOKENS_PER_CHUNK,
    CHUNKING_SPLIT_AT_SENTENCE_BOUNDARIES,
    CHUNKING_PRESERVE_ENTITY_CONTEXT,
    CHUNKING_TYPES,
)
from src.lib.logging import get_logger
from src.models.chunk_metadata import ChunkMetadata, ChunkEntity, ChunkMetadataModel, ChunkRelationship
from src.models.meeting_record import MeetingRecord

logger = get_logger(__name__)


class SemanticChunkingService:
    """
    Service for chunking meeting content by semantic units.
    
    Creates chunks aligned with semantic boundaries (meeting summary, action item,
    decision record, attendance, resource) rather than arbitrary token counts.
    """
    
    def __init__(
        self,
        max_tokens: int = CHUNKING_MAX_TOKENS_PER_CHUNK,
        split_at_sentence_boundaries: bool = CHUNKING_SPLIT_AT_SENTENCE_BOUNDARIES,
        preserve_entity_context: bool = CHUNKING_PRESERVE_ENTITY_CONTEXT,
    ):
        """
        Initialize semantic chunking service.
        
        Args:
            max_tokens: Maximum tokens per chunk before splitting
            split_at_sentence_boundaries: Split at sentence boundaries if chunk exceeds token limit
            preserve_entity_context: Preserve entity metadata in split chunks
        """
        self.max_tokens = max_tokens
        self.split_at_sentence_boundaries = split_at_sentence_boundaries
        self.preserve_entity_context = preserve_entity_context
        
        logger.info(
            "semantic_chunking_service_initialized",
            max_tokens=max_tokens,
            split_at_sentence_boundaries=split_at_sentence_boundaries,
        )
    
    def chunk_by_semantic_unit(
        self,
        meeting_record: MeetingRecord,
        entities: List,
        meeting_id: UUID,
        relationship_triples: Optional[List] = None,
    ) -> List[ChunkMetadata]:
        """
        Create semantic chunks with entity metadata from meeting record.
        
        Args:
            meeting_record: MeetingRecord to chunk
            entities: List of entities mentioned in the meeting
            meeting_id: Meeting ID for metadata
            relationship_triples: Optional list of RelationshipTriple objects for embedding in chunks
            
        Returns:
            List of ChunkMetadata objects
        """
        chunks = []
        
        # Chunk type: meeting_summary (from meetingInfo.purpose)
        if meeting_record.meetingInfo and meeting_record.meetingInfo.purpose:
            chunk = self._create_chunk(
                text=meeting_record.meetingInfo.purpose,
                chunk_type="meeting_summary",
                source_field="meetingInfo.purpose",
                meeting_id=meeting_id,
                entities=entities,
                relationship_triples=relationship_triples,
            )
            chunks.extend(self.split_chunk_if_needed(chunk))
        
        # Chunk type: action_item (each actionItems[] item)
        if meeting_record.agendaItems:
            for agenda_item_index, agenda_item in enumerate(meeting_record.agendaItems):
                if agenda_item.actionItems:
                    for action_item_index, action_item in enumerate(agenda_item.actionItems):
                        action_text = action_item.text if hasattr(action_item, 'text') else str(action_item)
                        chunk = self._create_chunk(
                            text=action_text,
                            chunk_type="action_item",
                            source_field=f"agendaItems[{agenda_item_index}].actionItems[{action_item_index}]",
                            meeting_id=meeting_id,
                            entities=entities,
                            relationship_triples=relationship_triples,
                        )
                        chunks.extend(self.split_chunk_if_needed(chunk))
        
        # Chunk type: decision_record (each decisionItems[] item)
        if meeting_record.agendaItems:
            for agenda_item_index, agenda_item in enumerate(meeting_record.agendaItems):
                if agenda_item.decisionItems:
                    for decision_item_index, decision_item in enumerate(agenda_item.decisionItems):
                        decision_text = decision_item.decision if hasattr(decision_item, 'decision') else str(decision_item)
                        chunk = self._create_chunk(
                            text=decision_text,
                            chunk_type="decision_record",
                            source_field=f"agendaItems[{agenda_item_index}].decisionItems[{decision_item_index}]",
                            meeting_id=meeting_id,
                            entities=entities,
                            relationship_triples=relationship_triples,
                        )
                        chunks.extend(self.split_chunk_if_needed(chunk))
        
        # Chunk type: attendance (peoplePresent list)
        if meeting_record.meetingInfo and meeting_record.meetingInfo.peoplePresent:
            chunk = self._create_chunk(
                text=meeting_record.meetingInfo.peoplePresent,
                chunk_type="attendance",
                source_field="meetingInfo.peoplePresent",
                meeting_id=meeting_id,
                entities=entities,
                relationship_triples=relationship_triples,
            )
            chunks.extend(self.split_chunk_if_needed(chunk))
        
        # Chunk type: resource (each workingDocs[] item)
        if meeting_record.meetingInfo and meeting_record.meetingInfo.workingDocs:
            for doc_index, doc in enumerate(meeting_record.meetingInfo.workingDocs):
                doc_text = doc.title if hasattr(doc, 'title') else str(doc)
                chunk = self._create_chunk(
                    text=doc_text,
                    chunk_type="resource",
                    source_field=f"meetingInfo.workingDocs[{doc_index}]",
                    meeting_id=meeting_id,
                    entities=entities,
                    relationship_triples=relationship_triples,
                )
                chunks.extend(self.split_chunk_if_needed(chunk))
        
        # Update chunk indices
        for i, chunk in enumerate(chunks):
            chunk.metadata.chunk_index = i
            chunk.metadata.total_chunks = len(chunks)
        
        logger.info(
            "semantic_chunks_created",
            meeting_id=str(meeting_id),
            chunk_count=len(chunks),
        )
        
        return chunks
    
    def split_chunk_if_needed(
        self,
        chunk: ChunkMetadata,
    ) -> List[ChunkMetadata]:
        """
        Split chunk at sentence boundaries if exceeds token limit.
        
        Args:
            chunk: ChunkMetadata to potentially split
            
        Returns:
            List of chunks (single chunk if no split needed, multiple if split)
        """
        # Simple token estimation (rough: 1 token ≈ 4 characters)
        estimated_tokens = len(chunk.text) / 4
        
        if estimated_tokens <= self.max_tokens:
            return [chunk]
        
        if not self.split_at_sentence_boundaries:
            # Return as-is if splitting not enabled
            logger.warning(
                "chunk_exceeds_token_limit",
                estimated_tokens=estimated_tokens,
                max_tokens=self.max_tokens,
            )
            return [chunk]
        
        # Split at sentence boundaries
        sentences = re.split(r'[.!?]+\s+', chunk.text)
        split_chunks = []
        
        current_text = ""
        current_entities = chunk.entities.copy()
        
        for sentence in sentences:
            sentence_text = sentence.strip()
            if not sentence_text:
                continue
            
            # Check if adding this sentence would exceed limit
            potential_text = (current_text + " " + sentence_text).strip()
            potential_tokens = len(potential_text) / 4
            
            if potential_tokens > self.max_tokens and current_text:
                # Create chunk from current text
                split_chunk = ChunkMetadata(
                    text=current_text,
                    entities=current_entities if self.preserve_entity_context else [],
                    metadata=ChunkMetadataModel(
                        meeting_id=chunk.metadata.meeting_id,
                        chunk_type=chunk.metadata.chunk_type,
                        source_field=chunk.metadata.source_field,
                        relationships=chunk.metadata.relationships.copy() if self.preserve_entity_context else [],
                    ),
                )
                split_chunks.append(split_chunk)
                current_text = sentence_text
            else:
                current_text = potential_text if current_text else sentence_text
        
        # Add remaining text as final chunk
        if current_text:
            split_chunk = ChunkMetadata(
                text=current_text,
                entities=current_entities if self.preserve_entity_context else [],
                metadata=ChunkMetadataModel(
                    meeting_id=chunk.metadata.meeting_id,
                    chunk_type=chunk.metadata.chunk_type,
                    source_field=chunk.metadata.source_field,
                    relationships=chunk.metadata.relationships.copy() if self.preserve_entity_context else [],
                ),
            )
            split_chunks.append(split_chunk)
        
        logger.debug(
            "chunk_split",
            original_length=len(chunk.text),
            split_count=len(split_chunks),
        )
        
        return split_chunks if split_chunks else [chunk]
    
    def _create_chunk(
        self,
        text: str,
        chunk_type: str,
        source_field: str,
        meeting_id: UUID,
        entities: List,
        relationship_triples: Optional[List] = None,
    ) -> ChunkMetadata:
        """
        Create a chunk with entity metadata.
        
        Args:
            text: Chunk text content
            chunk_type: Type of semantic chunk (meeting_summary, action_item, etc.)
            source_field: JSON path source field
            meeting_id: Meeting UUID
            entities: List of entities to match against text
            relationship_triples: Optional list of RelationshipTriple objects for this meeting
            
        Returns:
            ChunkMetadata with embedded entities and relationships
        """
        chunk_entities = []
        chunk_relationships = []
        text_lower = text.lower()
        
        # Extract entity mentions from text and match with entities
        # Handle different entity types (Person has display_name, Workgroup has name, etc.)
        for entity in entities:
            entity_name = None
            entity_type_name = type(entity).__name__
            
            # Get entity name based on entity type
            if hasattr(entity, 'display_name'):
                entity_name = entity.display_name
            elif hasattr(entity, 'name'):
                entity_name = entity.name
            elif hasattr(entity, 'text'):
                entity_name = entity.text
            elif hasattr(entity, 'decision'):
                entity_name = entity.decision
            elif hasattr(entity, 'title'):
                entity_name = entity.title
            
            if not entity_name:
                continue
            
            # Check if entity name appears in text (case-insensitive)
            entity_name_lower = entity_name.lower()
            if entity_name_lower in text_lower:
                # Collect all mentions (including variations)
                mentions = [entity_name]
                
                # Check for variations (e.g., "Stephen" vs "Stephen [QADAO]")
                # Look for patterns where entity name appears with additional context
                pattern = re.escape(entity_name_lower)
                matches = re.findall(rf'\b{pattern}[^\s]*\b', text_lower, re.IGNORECASE)
                for match in matches:
                    if match not in mentions and match.lower() != entity_name_lower:
                        # Find the actual text (not lowercased) for the mention
                        original_match = text[text_lower.find(match):text_lower.find(match)+len(match)]
                        if original_match not in mentions:
                            mentions.append(original_match)
                
                chunk_entities.append(ChunkEntity(
                    entity_id=entity.id,
                    entity_type=entity_type_name,
                    normalized_name=entity_name,
                    mentions=mentions,
                ))
        
        # Extract relevant relationships for this chunk
        # Filter relationships where subject or object entities are mentioned in the chunk
        if relationship_triples:
            chunk_entity_ids = {ce.entity_id for ce in chunk_entities}
            for triple in relationship_triples:
                # Include relationship if subject or object is mentioned in chunk
                if (triple.subject_id in chunk_entity_ids or 
                    triple.object_id in chunk_entity_ids):
                    chunk_relationships.append(ChunkRelationship(
                        subject=triple.subject_type,
                        relationship=triple.relationship,
                        object=triple.object_type,
                    ))
        
        return ChunkMetadata(
            text=text,
            entities=chunk_entities,
            metadata=ChunkMetadataModel(
                meeting_id=meeting_id,
                chunk_type=chunk_type,
                source_field=source_field,
                relationships=chunk_relationships,
            ),
        )


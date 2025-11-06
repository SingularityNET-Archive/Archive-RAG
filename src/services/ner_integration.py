"""NER integration service for extracting entities from unstructured text fields."""

from typing import List, Optional
from uuid import UUID

import spacy

from src.lib.config import (
    NER_MODEL_NAME,
    NER_ENTITY_TYPES,
    NER_MIN_CONFIDENCE,
    NER_FILTER_CRITERIA,
)
from src.lib.logging import get_logger
from src.models.ner_entity import NEREntity
from src.models.person import Person
from src.services.entity_normalization import EntityNormalizationService

logger = get_logger(__name__)


class NERIntegrationService:
    """
    Service for integrating Named Entity Recognition (NER) with entity extraction.
    
    Extracts entities from unstructured text fields and merges them with
    structured JSON entities.
    """
    
    def __init__(
        self,
        model_name: str = NER_MODEL_NAME,
        entity_types: Optional[List[str]] = None,
        min_confidence: float = NER_MIN_CONFIDENCE,
    ):
        """
        Initialize NER integration service.
        
        Args:
            model_name: spaCy model name
            entity_types: List of entity types to extract
            min_confidence: Minimum confidence threshold
        """
        self.model_name = model_name
        self.entity_types = entity_types or NER_ENTITY_TYPES
        self.min_confidence = min_confidence
        
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            raise ValueError(
                f"spaCy model '{model_name}' not found. "
                f"Install it with: python -m spacy download {model_name}"
            )
        
        self.normalization_service = EntityNormalizationService()
        
        logger.info(
            "ner_integration_service_initialized",
            model_name=model_name,
            entity_types=self.entity_types,
            min_confidence=min_confidence,
        )
    
    def extract_from_text(
        self,
        text: str,
        meeting_id: UUID,
        source_field: str,
    ) -> List[NEREntity]:
        """
        Extract entities from text using spaCy NER.
        
        Applies filtering criteria (FR-013, FR-014) to ensure only meaningful
        entities are extracted.
        
        Args:
            text: Text to extract entities from
            meeting_id: Source meeting ID
            source_field: JSON path where text was found
            
        Returns:
            List of NEREntity objects that meet extraction criteria
        """
        if not text or not text.strip():
            return []
        
        doc = self.nlp(text)
        ner_entities = []
        
        for ent in doc.ents:
            # Filter by entity type if specified
            if ent.label_ not in self.entity_types:
                continue
            
            entity_text = ent.text.strip()
            
            # Apply extraction criteria filtering (FR-013, FR-014)
            if not self._should_extract_ner_entity(entity_text, ent.label_):
                continue
            
            # Create NER entity
            ner_entity = NEREntity(
                text=entity_text,
                entity_type=ent.label_,
                source_text=text,
                source_field=source_field,
                source_meeting_id=meeting_id,
                normalized_entity_id=None,  # Will be set during merging
                confidence=1.0,  # spaCy doesn't provide confidence, use 1.0 as default
            )
            
            ner_entities.append(ner_entity)
        
        logger.debug(
            "ner_entities_extracted",
            text_length=len(text),
            source_field=source_field,
            entity_count=len(ner_entities),
        )
        
        return ner_entities
    
    def _should_extract_ner_entity(
        self,
        entity_text: str,
        entity_type: str,
    ) -> bool:
        """
        Check if NER entity should be extracted based on criteria (FR-013, FR-014).
        
        Entity is extracted if it meets at least one criterion (OR logic):
        - Entity is a thing (person, workgroup, doc, meeting)
        - Entity is searchable by users
        - Entity appears in multiple meetings (will be checked later)
        - Entity provides context/references
        
        Also filters out one-off filler comments (FR-014).
        
        Args:
            entity_text: Entity text to check
            entity_type: spaCy entity type (PERSON, ORG, GPE, DATE, etc.)
            
        Returns:
            True if entity should be extracted, False otherwise
        """
        if not entity_text or not entity_text.strip():
            return False
        
        # Filter out obvious filler comments (FR-014)
        filler_keywords = ["comment", "filler", "n/a", "none", "tbd", "todo", "tba"]
        entity_lower = entity_text.lower().strip()
        if any(keyword in entity_lower for keyword in filler_keywords):
            return False
        
        # Filter out very short entities (likely noise)
        if len(entity_text.strip()) < 2:
            return False
        
        # DATE entities: Check first to filter out relative dates before other criteria
        if entity_type == "DATE":
            # Filter out relative dates that aren't useful
            relative_dates = ["today", "tomorrow", "yesterday", "now", "next", "last"]
            if entity_lower in relative_dates:
                return False
            # If it's a DATE and not a relative date, extract it
            return True
        
        # Criterion 1: Entity is a thing (person, workgroup, doc, meeting)
        # Map spaCy entity types to our thing types
        thing_entity_types = ["PERSON", "ORG", "GPE"]
        if entity_type in thing_entity_types:
            return True
        
        # Criterion 2: Entity is searchable (has meaningful content, not just punctuation)
        if len(entity_lower) >= 2 and entity_lower.replace(" ", "").isalnum():
            return True
        
        # Criterion 3: Entity provides context (has meaningful words)
        words = entity_lower.split()
        if len(words) >= 1 and any(len(word) >= 3 for word in words):
            return True
        
        return False
    
    def merge_with_structured(
        self,
        ner_entities: List[NEREntity],
        structured_entities: List,
    ) -> List:
        """
        Merge NER entities with structured entities.
        
        If NER entity matches structured entity (same name, >95% similarity),
        merge NER entity into structured entity. Otherwise, return NER entities
        for potential new entity creation.
        
        Uses EntityNormalizationService to normalize entity names before matching.
        
        Args:
            ner_entities: List of NER-extracted entities
            structured_entities: List of structured entities (Person, Workgroup, etc.)
            
        Returns:
            List of NER entities with normalized_entity_id set if matched
        """
        merged_ner_entities = []
        
        for ner_entity in ner_entities:
            # Normalize NER entity name using EntityNormalizationService
            normalized_id, normalized_name = self.normalization_service.normalize_entity_name(
                ner_entity.text,
                existing_entities=structured_entities if structured_entities else None
            )
            
            # Check if normalization found an existing entity (ID not placeholder)
            if normalized_id.int != 0:
                ner_entity.normalized_entity_id = normalized_id
                logger.debug(
                    "ner_entity_normalized_to_existing",
                    ner_text=ner_entity.text,
                    normalized_name=normalized_name,
                    entity_id=str(normalized_id),
                )
            else:
                # Check for fuzzy match with existing structured entities
                matched = False
                for entity in structured_entities:
                    entity_name = None
                    if hasattr(entity, 'display_name'):
                        entity_name = entity.display_name
                    elif hasattr(entity, 'name'):
                        entity_name = entity.name
                    
                    if entity_name:
                        from rapidfuzz import fuzz
                        similarity = fuzz.ratio(ner_entity.text.lower(), entity_name.lower()) / 100.0
                        
                        if similarity >= 0.95:
                            ner_entity.normalized_entity_id = entity.id
                            matched = True
                            logger.debug(
                                "ner_entity_matched_fuzzy",
                                ner_text=ner_entity.text,
                                entity_id=str(entity.id),
                                similarity=similarity,
                            )
                            break
                
                if not matched:
                    logger.debug(
                        "ner_entity_new",
                        ner_text=ner_entity.text,
                        entity_type=ner_entity.entity_type,
                        normalized_name=normalized_name,
                    )
            
            merged_ner_entities.append(ner_entity)
        
        return merged_ner_entities


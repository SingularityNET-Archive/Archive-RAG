"""Entity normalization service for merging entity name variations."""

import re
from typing import List, Optional, Tuple, Dict
from uuid import UUID

from rapidfuzz import fuzz

from src.lib.config import (
    ENTITY_NORMALIZATION_SIMILARITY_THRESHOLD,
    ENTITY_NORMALIZATION_PATTERN_RULES,
    ENTITY_NORMALIZATION_ENABLE_FUZZY_MATCHING,
    ENTITY_NORMALIZATION_ENABLE_CONTEXT_DISAMBIGUATION,
)
from src.lib.logging import get_logger
from src.models.person import Person
from src.models.workgroup import Workgroup
from src.services.entity_storage import load_entity, ENTITIES_PEOPLE_DIR, ENTITIES_WORKGROUPS_DIR, ENTITIES_MEETINGS_DIR
from src.models.meeting import Meeting

logger = get_logger(__name__)


class EntityNormalizationService:
    """
    Service for normalizing entity name variations to canonical entities.
    
    Merges variations like "Stephen" and "Stephen [QADAO]" into a single
    canonical entity to avoid duplicates and splits.
    """
    
    def __init__(
        self,
        similarity_threshold: float = ENTITY_NORMALIZATION_SIMILARITY_THRESHOLD,
        pattern_rules: Optional[List[str]] = None,
        enable_fuzzy_matching: bool = ENTITY_NORMALIZATION_ENABLE_FUZZY_MATCHING,
        enable_context_disambiguation: bool = ENTITY_NORMALIZATION_ENABLE_CONTEXT_DISAMBIGUATION,
    ):
        """
        Initialize entity normalization service.
        
        Args:
            similarity_threshold: Minimum similarity (0.0-1.0) for fuzzy matching
            pattern_rules: List of regex patterns for pattern-based normalization
            enable_fuzzy_matching: Enable fuzzy similarity matching
            enable_context_disambiguation: Enable context-based disambiguation
        """
        self.similarity_threshold = similarity_threshold
        self.pattern_rules = pattern_rules or ENTITY_NORMALIZATION_PATTERN_RULES
        self.enable_fuzzy_matching = enable_fuzzy_matching
        self.enable_context_disambiguation = enable_context_disambiguation
        
        # T082 [Phase 9] Cache for entity lookups to improve performance
        self._entity_cache: Dict[str, List[Person]] = {}
        self._normalization_cache: Dict[str, Tuple[UUID, str]] = {}
        
        logger.info(
            "entity_normalization_service_initialized",
            similarity_threshold=similarity_threshold,
            pattern_rules_count=len(self.pattern_rules),
            enable_fuzzy_matching=enable_fuzzy_matching,
            enable_context_disambiguation=enable_context_disambiguation,
        )
    
    def normalize_entity_name(
        self,
        name: str,
        existing_entities: Optional[List] = None,
        context: Optional[Dict] = None,
    ) -> Tuple[UUID, str]:
        """
        Normalize entity name to canonical entity.
        
        Args:
            name: Entity name to normalize
            existing_entities: Optional list of existing entities to check against
            context: Optional context dict with keys like 'workgroup_id', 'meeting_id' for disambiguation
            
        Returns:
            Tuple of (canonical_entity_id, canonical_name)
            
        Raises:
            ValueError: If name is empty or normalization fails
        """
        if not name or not name.strip():
            raise ValueError("Entity name cannot be empty")
        
        name = name.strip()
        
        # T082 [Phase 9] Check cache first
        cache_key = name.lower()
        if cache_key in self._normalization_cache:
            cached_id, cached_name = self._normalization_cache[cache_key]
            logger.debug("entity_normalization_cache_hit", name=name)
            return cached_id, cached_name
        
        # Step 1: Pattern-based normalization
        canonical_name = self.merge_variations([name])
        
        # Step 2: Find similar entities if fuzzy matching enabled
        if existing_entities is None:
            existing_entities = self._load_existing_entities()
        
        similar_entities = []
        if self.enable_fuzzy_matching:
            similar_entities = self.find_similar_entities(
                canonical_name,
                existing_entities,
                self.similarity_threshold
            )
        
        # T080 [Phase 9] Apply context-based disambiguation if enabled
        if self.enable_context_disambiguation and context and similar_entities:
            similar_entities = self._disambiguate_by_context(
                name,
                similar_entities,
                context
            )
        
        # Step 3: Return canonical entity
        if similar_entities:
            # Use existing canonical entity
            canonical_entity = similar_entities[0]
            # Get entity name (handle both Person with display_name and Workgroup with name)
            canonical_name = None
            if hasattr(canonical_entity, 'display_name'):
                canonical_name = canonical_entity.display_name
            elif hasattr(canonical_entity, 'name'):
                canonical_name = canonical_entity.name
            
            result = (canonical_entity.id, canonical_name or name)
            
            # T082 [Phase 9] Cache the result
            self._normalization_cache[cache_key] = result
            
            logger.debug(
                "entity_normalized_to_existing",
                original_name=name,
                canonical_name=canonical_name,
                canonical_id=str(canonical_entity.id),
            )
            return result
        else:
            # New entity - would need to create it, but for now return the normalized name
            # In practice, this would create a new entity and return its ID
            result = (UUID(int=0), canonical_name)
            
            # T082 [Phase 9] Cache the result
            self._normalization_cache[cache_key] = result
            
            logger.debug(
                "entity_normalized_new",
                original_name=name,
                canonical_name=canonical_name,
            )
            return result
    
    def merge_variations(self, variations: List[str]) -> str:
        """
        Merge name variations into canonical name.
        
        Applies pattern-based normalization to remove common suffixes.
        
        Args:
            variations: List of name variations
            
        Returns:
            Canonical name
        """
        if not variations:
            raise ValueError("Variations list cannot be empty")
        
        # Use the first variation as base
        canonical = variations[0].strip()
        
        # Apply pattern-based normalization rules
        for pattern in self.pattern_rules:
            canonical = re.sub(pattern, "", canonical, flags=re.IGNORECASE).strip()
        
        # Clean up extra spaces
        canonical = " ".join(canonical.split())
        
        return canonical
    
    def find_similar_entities(
        self,
        name: str,
        entities: List[Person],
        threshold: float = None,
    ) -> List[Person]:
        """
        Find similar entities using fuzzy matching.
        
        Args:
            name: Entity name to find matches for
            entities: List of entities to search
            threshold: Similarity threshold (defaults to instance threshold)
            
        Returns:
            List of similar entities sorted by similarity (highest first)
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        if not entities:
            return []
        
        similar = []
        for entity in entities:
            # Calculate similarity using rapidfuzz
            # Get entity name (handle both Person with display_name and Workgroup with name)
            entity_name = None
            if hasattr(entity, 'display_name'):
                entity_name = entity.display_name
            elif hasattr(entity, 'name'):
                entity_name = entity.name
            
            if not entity_name:
                continue
            
            similarity = fuzz.ratio(name.lower(), entity_name.lower()) / 100.0
            
            if similarity >= threshold:
                similar.append((entity, similarity))
        
        # Sort by similarity (highest first)
        similar.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(
            "similar_entities_found",
            name=name,
            similar_count=len(similar),
            threshold=threshold,
        )
        
        return [entity for entity, _ in similar]
    
    def _load_existing_entities(self) -> List[Person]:
        """Load existing person entities for normalization matching."""
        # T082 [Phase 9] Check cache first
        cache_key = "all_persons"
        if cache_key in self._entity_cache:
            logger.debug("entity_cache_hit", cache_key=cache_key)
            return self._entity_cache[cache_key]
        
        try:
            # Use direct entity storage to avoid circular import
            from pathlib import Path
            persons = []
            for person_file in ENTITIES_PEOPLE_DIR.glob("*.json"):
                try:
                    person_id = UUID(person_file.stem)
                    person = load_entity(person_id, ENTITIES_PEOPLE_DIR, Person)
                    if person:
                        persons.append(person)
                except (ValueError, AttributeError):
                    continue
            
            # T082 [Phase 9] Cache the result
            self._entity_cache[cache_key] = persons
            
            return persons
        except Exception as e:
            logger.warning(
                "failed_to_load_existing_entities",
                error=str(e),
            )
            return []
    
    def _disambiguate_by_context(
        self,
        name: str,
        similar_entities: List,
        context: Dict,
    ) -> List:
        """
        T080 [Phase 9] Disambiguate entities using context (workgroup associations, meeting patterns).
        
        Uses context information to determine which entity is most likely the correct match.
        
        Args:
            name: Entity name being matched
            similar_entities: List of similar entities found by fuzzy matching
            context: Context dict with keys like 'workgroup_id', 'meeting_id'
            
        Returns:
            Filtered list of entities, sorted by context relevance
        """
        if len(similar_entities) <= 1:
            return similar_entities
        
        context_scores = []
        
        # Get workgroup from context
        workgroup_id = context.get('workgroup_id')
        if workgroup_id:
            try:
                workgroup = load_entity(workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
                if workgroup:
                    # Check if any similar entities appear in meetings with this workgroup
                    for entity in similar_entities:
                        score = 0.0
                        # Check meetings associated with this workgroup
                        for meeting_file in ENTITIES_MEETINGS_DIR.glob("*.json"):
                            try:
                                meeting_id = UUID(meeting_file.stem)
                                meeting = load_entity(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
                                if meeting and meeting.workgroup_id == workgroup_id:
                                    # Simple heuristic: if entity appears in same workgroup's meetings, increase score
                                    # This is a placeholder - actual implementation would check participant lists
                                    score += 0.1
                            except (ValueError, AttributeError):
                                continue
                        context_scores.append((entity, score))
            except Exception as e:
                logger.debug("context_disambiguation_failed", error=str(e))
        
        # If we have context scores, sort by them
        if context_scores:
            context_scores.sort(key=lambda x: x[1], reverse=True)
            logger.debug(
                "entities_disambiguated_by_context",
                name=name,
                similar_count=len(similar_entities),
                context_scores=[(str(e[0].id), e[1]) for e in context_scores[:3]],
            )
            return [entity for entity, _ in context_scores]
        
        # No context disambiguation possible, return original list
        return similar_entities
    
    def clear_cache(self):
        """T082 [Phase 9] Clear normalization and entity caches."""
        self._entity_cache.clear()
        self._normalization_cache.clear()
        logger.debug("entity_normalization_cache_cleared")


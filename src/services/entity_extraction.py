"""Entity extraction service using spaCy."""

from typing import List, Dict, Any, Optional, Set
import spacy
from collections import Counter

from ..lib.config import DEFAULT_SPACY_MODEL, DEFAULT_MIN_ENTITY_FREQUENCY
from ..lib.pii_detection import create_pii_detector
from ..lib.logging import get_logger

logger = get_logger(__name__)


class EntityExtractionService:
    """Service for extracting named entities using spaCy."""
    
    def __init__(
        self,
        model_name: str = DEFAULT_SPACY_MODEL,
        entity_types: Optional[Set[str]] = None,
        min_frequency: int = DEFAULT_MIN_ENTITY_FREQUENCY,
        no_pii: bool = False
    ):
        """
        Initialize entity extraction service.
        
        Args:
            model_name: spaCy model name (default: en_core_web_sm)
            entity_types: Set of entity types to extract (default: all)
            min_frequency: Minimum frequency for entity inclusion (default: 2)
            no_pii: Skip PII detection and redaction (default: False)
        """
        self.model_name = model_name
        self.entity_types = entity_types
        self.min_frequency = min_frequency
        self.no_pii = no_pii
        
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            raise ValueError(
                f"spaCy model '{model_name}' not found. "
                f"Install it with: python -m spacy download {model_name}"
            )
        
        self.pii_detector = None if no_pii else create_pii_detector()
        
        logger.info(
            "entity_extraction_initialized",
            model_name=model_name,
            entity_types=entity_types,
            min_frequency=min_frequency
        )
    
    def extract_entities(self, documents: List[str]) -> Dict[str, Any]:
        """
        Extract named entities from documents.
        
        Args:
            documents: List of document text strings
            
        Returns:
            Dictionary with entities, frequencies, and metadata
        """
        if not documents:
            raise ValueError("No documents provided for entity extraction")
        
        # Extract entities from all documents
        all_entities = []
        entity_frequencies = Counter()
        
        for doc_text in documents:
            # Redact PII if enabled
            if not self.no_pii and self.pii_detector:
                doc_text = self.pii_detector.redact(doc_text)
            
            # Process with spaCy
            doc = self.nlp(doc_text)
            
            # Extract entities
            for ent in doc.ents:
                # Filter by entity type if specified
                if self.entity_types and ent.label_ not in self.entity_types:
                    continue
                
                entity_text = ent.text.strip()
                entity_type = ent.label_
                
                # Store entity
                all_entities.append({
                    "text": entity_text,
                    "type": entity_type
                })
                
                # Count frequency
                entity_key = (entity_text, entity_type)
                entity_frequencies[entity_key] += 1
        
        # Filter by minimum frequency and aggregate
        filtered_entities = []
        for (entity_text, entity_type), frequency in entity_frequencies.items():
            if frequency >= self.min_frequency:
                filtered_entities.append({
                    "text": entity_text,
                    "type": entity_type,
                    "frequency": frequency
                })
        
        # Sort by frequency (descending)
        filtered_entities.sort(key=lambda x: x["frequency"], reverse=True)
        
        logger.info(
            "entities_extracted",
            total_entities=len(all_entities),
            filtered_entities=len(filtered_entities),
            min_frequency=self.min_frequency
        )
        
        return {
            "entities": filtered_entities,
            "model": self.model_name,
            "entity_types": list(self.entity_types) if self.entity_types else None,
            "min_frequency": self.min_frequency,
            "total_extracted": len(all_entities),
            "total_filtered": len(filtered_entities)
        }


def create_entity_extraction_service(
    model_name: str = DEFAULT_SPACY_MODEL,
    entity_types: Optional[Set[str]] = None,
    min_frequency: int = DEFAULT_MIN_ENTITY_FREQUENCY,
    no_pii: bool = False
) -> EntityExtractionService:
    """
    Create an entity extraction service instance.
    
    Args:
        model_name: spaCy model name
        entity_types: Set of entity types to extract
        min_frequency: Minimum frequency for entity inclusion
        no_pii: Skip PII detection and redaction
        
    Returns:
        EntityExtractionService instance
    """
    return EntityExtractionService(model_name, entity_types, min_frequency, no_pii)


# Data Contracts: Refined Entity Extraction

**Feature**: Refine Entity Extraction  
**Date**: 2025-01-21  
**Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

## Overview

Data contracts define the structure and validation rules for enhanced entity extraction outputs: normalized entities, relationship triples, chunk metadata, and NER-extracted entities.

---

## Relationship Triple Contract

**Format**: `Subject -> Relationship -> Object`

**Structure**:
```python
{
    "subject_id": "UUID",
    "subject_type": "Workgroup|Meeting|Person|ActionItem|DecisionItem|...",
    "subject_name": "String (canonical name)",
    "relationship": "held|attended|produced|assigned_to|has_effect|...",
    "object_id": "UUID",
    "object_type": "Workgroup|Meeting|Person|ActionItem|DecisionItem|...",
    "object_name": "String (canonical name)",
    "source_meeting_id": "UUID",
    "source_field": "String (JSON path, e.g., 'meetingInfo.workgroup_id')"
}
```

**Relationship Types**:
- `held` (Workgroup → Meeting)
- `attended` (Person → Meeting)
- `produced` (Meeting → Decision)
- `assigned_to` (ActionItem → Person)
- `has_effect` (Decision → Effect)
- `has_document` (Meeting → Document)
- `has_agenda_item` (Meeting → AgendaItem)

**Validation Rules**:
- `subject_id` and `object_id` must reference existing entities
- `subject_type` and `object_type` must be valid entity types
- `relationship` must be a valid relationship type
- `source_meeting_id` must reference existing meeting

---

## Chunk Metadata Contract

**Structure**:
```python
{
    "text": "String (chunk text content)",
    "entities": [
        {
            "entity_id": "UUID",
            "entity_type": "Person|Workgroup|Meeting|Document|DecisionItem|ActionItem",
            "normalized_name": "String (canonical name)",
            "mentions": ["String"]  # All name variations found in chunk
        }
    ],
    "metadata": {
        "meeting_id": "UUID",
        "chunk_type": "meeting_summary|action_item|decision_record|attendance|resource",
        "source_field": "String (JSON path, e.g., 'meetingInfo.purpose')",
        "relationships": [
            {
                "subject": "String (entity type)",
                "relationship": "String (relationship type)",
                "object": "String (entity type)"
            }
        ],
        "chunk_index": "Integer (0-based index for chunks from same source)",
        "total_chunks": "Integer (total chunks from same source)"
    }
}
```

**Chunk Types**:
- `meeting_summary`: From `meetingInfo.purpose`
- `action_item`: From `actionItems[]` array items
- `decision_record`: From `decisionItems[]` array items
- `attendance`: From `peoplePresent` list
- `resource`: From `workingDocs[]` array items

**Validation Rules**:
- `text` must not be empty
- `entities` array must contain valid entity references
- `metadata.meeting_id` must reference existing meeting
- `metadata.chunk_type` must be valid chunk type
- `metadata.source_field` must be valid JSON path

**Splitting Rules** (for chunks exceeding token limits):
- Split at sentence boundaries within semantic unit
- Each split chunk must preserve entity metadata
- Split chunks must maintain `chunk_index` and `total_chunks` for reassembly

---

## Normalized Entity Contract

**Structure** (extends existing entity models):
```python
{
    # Existing entity fields (id, display_name, created_at, updated_at, etc.)
    "id": "UUID",
    "display_name": "String (canonical name)",
    "normalized_variations": [
        {
            "variation": "String (original name variation)",
            "normalization_method": "pattern|fuzzy|manual",
            "confidence": "Float (0.0-1.0)",
            "source_meeting_id": "UUID"
        }
    ],
    "canonical_name": "String (same as display_name, explicit canonical reference)"
}
```

**Normalization Methods**:
- `pattern`: Pattern-based normalization (regex rules, e.g., removing `[QADAO]` suffix)
- `fuzzy`: Fuzzy similarity matching (rapidfuzz >95% similarity)
- `manual`: Manual normalization (future: admin override)

**Validation Rules**:
- `canonical_name` must match `display_name`
- `normalized_variations` must contain at least one variation (the canonical name itself)
- `confidence` must be between 0.0 and 1.0
- All variations must reference valid source meetings

---

## NER-Extracted Entity Contract

**Structure**:
```python
{
    "text": "String (extracted entity text)",
    "entity_type": "PERSON|ORG|GPE|DATE|... (spaCy entity type)",
    "source_text": "String (original text field where entity was found)",
    "source_field": "String (JSON path, e.g., 'meetingInfo.purpose')",
    "source_meeting_id": "UUID",
    "normalized_entity_id": "UUID (if merged with structured entity, null if new)",
    "confidence": "Float (NER confidence score, 0.0-1.0)"
}
```

**Integration Rules**:
- If NER entity matches structured entity (same name, >95% similarity) → merge into structured entity
- If NER entity is new → create new entity if it meets extraction criteria (FR-013)
- Structured entity takes precedence over NER entity when merging

**Validation Rules**:
- `text` must not be empty
- `entity_type` must be valid spaCy entity type
- `source_meeting_id` must reference existing meeting
- `confidence` must be between 0.0 and 1.0

---

## Entity Extraction Output Contract

**Structure** (complete output from entity extraction process):
```python
{
    "structured_entity_list": [
        {
            "entity_id": "UUID",
            "entity_type": "Person|Workgroup|Meeting|...",
            "canonical_name": "String",
            "normalized_variations": ["String"],
            "source_meetings": ["UUID"]
        }
    ],
    "normalized_cluster_labels": {
        "entity_id": {
            "canonical_name": "String",
            "variations": ["String"],
            "cluster_id": "UUID"
        }
    },
    "relationship_triples": [
        {
            "subject_id": "UUID",
            "subject_type": "String",
            "relationship": "String",
            "object_id": "UUID",
            "object_type": "String"
        }
    ],
    "chunks_for_embedding": [
        {
            "text": "String",
            "entities": [...],
            "metadata": {...}
        }
    ]
}
```

**Validation Rules**:
- All entity IDs must reference existing entities
- All relationship triples must have valid subject and object references
- All chunks must have valid entity references in metadata
- All normalized cluster labels must reference existing entities

---

## Service Contracts

### EntityNormalizationService

**Methods**:
- `normalize_entity_name(name: str, existing_entities: List[Entity]) -> Tuple[UUID, str]`: Returns canonical entity ID and canonical name
- `merge_variations(variations: List[str]) -> str`: Merges name variations into canonical name
- `find_similar_entities(name: str, entities: List[Entity], threshold: float = 0.95) -> List[Entity]`: Finds similar entities using fuzzy matching

### RelationshipTripleGenerator

**Methods**:
- `generate_triples(entities: List[Entity]) -> List[RelationshipTriple]`: Generates relationship triples from entities
- `get_triples_for_entity(entity_id: UUID) -> List[RelationshipTriple]`: Gets all triples involving an entity

### SemanticChunkingService

**Methods**:
- `chunk_by_semantic_unit(meeting_record: MeetingRecord, entities: List[Entity]) -> List[Chunk]`: Creates semantic chunks with entity metadata
- `split_chunk_if_needed(chunk: Chunk, max_tokens: int) -> List[Chunk]`: Splits chunk at sentence boundaries if exceeds token limit

### NERIntegrationService

**Methods**:
- `extract_from_text(text: str, meeting_id: UUID, source_field: str) -> List[NEREntity]`: Extracts entities from text using NER
- `merge_with_structured(ner_entities: List[NEREntity], structured_entities: List[Entity]) -> List[Entity]`: Merges NER entities with structured entities


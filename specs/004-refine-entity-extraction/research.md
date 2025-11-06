# Research: Refine Entity Extraction

**Feature**: Refine Entity Extraction  
**Date**: 2025-01-21  
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

## Research Questions

### 1. Entity Normalization Similarity Library

**Question**: Which Python library should be used for entity name similarity matching and normalization?

**Context**: 
- Need to normalize entity name variations (e.g., "Stephen" and "Stephen [QADAO]" → canonical "Stephen")
- Must support pattern matching (e.g., recognizing "[QADAO]" as a suffix to normalize)
- Must support fuzzy matching for similar names
- Must be Python-only (no external database dependencies)
- Must be deterministic (same inputs produce same outputs)

**Research**:
- **fuzzywuzzy**: Popular choice, uses Levenshtein distance, but requires `python-Levenshtein` C extension for performance (may violate "Python-only" if strict)
- **rapidfuzz**: Modern replacement for fuzzywuzzy, pure Python implementation available, faster, actively maintained
- **difflib** (standard library): Built-in `SequenceMatcher`, no dependencies, but slower and less accurate for fuzzy matching
- **re** (standard library): For pattern-based normalization (e.g., removing "[QADAO]" suffix)

**Decision**: Use **rapidfuzz** for fuzzy similarity matching + **re** (standard library) for pattern-based normalization

**Rationale**:
- rapidfuzz is pure Python (no C extensions required), faster than difflib, actively maintained
- Pattern matching with `re` handles predictable variations (e.g., "[QADAO]" suffix)
- Combination provides both deterministic pattern rules and fuzzy matching for edge cases
- No external database dependencies (complies with Constitution)
- Deterministic with fixed similarity threshold

**Alternatives Considered**:
- fuzzywuzzy: Rejected due to C extension dependency (may violate strict Python-only interpretation)
- difflib only: Rejected due to lower accuracy and performance for fuzzy matching
- Manual string matching only: Rejected due to inability to handle spelling variations and typos

---

### 2. Relationship Triple Storage Format

**Question**: Where and how should relationship triples be stored?

**Context**:
- Need to store relationship triples in format "Subject -> Relationship -> Object" (e.g., "Person -> attended -> Meeting")
- Must maintain traceability to source meeting records
- Must support efficient querying (find all relationships for an entity)
- Must comply with Constitution (local JSON files, no external database)

**Research**:
- **Option A**: Separate JSON files per relationship type (e.g., `entities/_relations/workgroup_meeting.json`, `entities/_relations/meeting_person.json`)
- **Option B**: Embed relationship lists in entity JSON files (e.g., Meeting entity contains `attended_by: [person_ids]`)
- **Option C**: Single relationship index file (`entities/_relations/all_relations.json` with array of triples)
- **Option D**: Hybrid - embed forward relationships in entities, maintain separate reverse index files

**Decision**: **Option B** - Embed relationship lists in entity JSON files (existing pattern)

**Rationale**:
- Aligns with existing entity storage pattern (entities already have relationship fields)
- Example: Meeting entity already has `workgroup_id` (FK), Person entity could have `attended_meetings: [meeting_ids]`
- Maintains referential integrity naturally (FKs in entity files)
- Efficient querying: load entity file, relationships are embedded
- No additional storage files needed
- Relationship triples can be generated on-demand from entity files

**Alternatives Considered**:
- Option A (separate files): Rejected due to added complexity and potential sync issues
- Option C (single index): Rejected due to large file size and query inefficiency
- Option D (hybrid): Rejected as unnecessary complexity - forward relationships sufficient

**Implementation Note**: Relationship triples will be generated dynamically from entity files when needed for output (FR-011), not stored as separate triple records.

---

### 3. Chunk Metadata Storage

**Question**: How should entity metadata be stored with semantic chunks?

**Context**:
- Semantic chunks must include entity metadata (which entities are mentioned, relationships, normalized references)
- Chunks are used for embedding generation
- Must maintain traceability to source meeting records
- Must comply with Constitution (local storage, no external database)

**Research**:
- **Option A**: Embed metadata in chunk JSON structure (e.g., `chunk.text`, `chunk.entities: [entity_ids]`, `chunk.metadata: {...}`)
- **Option B**: Separate metadata index file mapping chunk_id to entity metadata
- **Option C**: Store metadata in entity files (entities reference chunks they appear in)

**Decision**: **Option A** - Embed metadata in chunk JSON structure

**Rationale**:
- Simplest approach - chunk contains all information needed for embedding
- No additional lookups required when processing chunks
- Aligns with existing chunk storage pattern
- Metadata travels with chunk (no risk of metadata loss)
- Efficient for embedding generation (all context in one place)

**Alternatives Considered**:
- Option B (separate index): Rejected due to added complexity and potential sync issues
- Option C (reverse index): Rejected as less efficient for embedding generation (requires lookups)

**Implementation Note**: Chunk structure will include:
```python
{
  "text": "...",
  "entities": [{"entity_id": "...", "entity_type": "Person", "normalized_name": "..."}],
  "metadata": {
    "meeting_id": "...",
    "chunk_type": "meeting_summary|action_item|decision_record|attendance|resource",
    "source_field": "meetingInfo.purpose|actionItems[]|..."
  }
}
```

---

### 4. Performance Targets

**Question**: What are acceptable performance targets for entity extraction and normalization?

**Context**:
- Must process 120+ meeting records
- Entity extraction and normalization should not significantly slow down ingestion
- NER processing adds computational overhead
- Must maintain determinism

**Research**:
- **Baseline**: Current ingestion without entity extraction (from existing codebase)
- **Target**: Entity extraction should add <2 seconds per meeting record (acceptable for batch processing)
- **NER Processing**: spaCy NER is relatively fast (typically <100ms per document for small-medium text)
- **Normalization**: Pattern matching is O(1) per entity, fuzzy matching is O(n*m) where n=existing entities, m=new entities
- **Scale**: 120 meetings × ~5 entities per meeting = ~600 entities to normalize

**Decision**: Target processing time: **<2 seconds per meeting record** for complete entity extraction, normalization, and relationship generation

**Rationale**:
- Batch ingestion is acceptable (not real-time requirement)
- 120 meetings × 2 seconds = ~4 minutes total processing time (acceptable)
- NER processing is fast (<100ms per text field)
- Normalization can be optimized with caching and index lookups
- Prioritize correctness over speed (95% normalization accuracy is critical)

**Alternatives Considered**:
- <1 second per record: Too aggressive, may compromise normalization accuracy
- <5 seconds per record: Too lenient, users expect reasonable performance
- <2 seconds: Balanced - allows for thorough processing without excessive delay

**Implementation Note**: Performance will be measured and optimized iteratively. If normalization becomes bottleneck, will implement entity index caching for faster lookups.

---

## Summary

All research questions resolved:

1. ✅ **Entity Normalization**: Use rapidfuzz + re (standard library) for pattern matching and fuzzy similarity
2. ✅ **Relationship Storage**: Embed relationships in entity JSON files (existing pattern), generate triples on-demand
3. ✅ **Chunk Metadata**: Embed entity metadata in chunk JSON structure
4. ✅ **Performance Targets**: Target <2 seconds per meeting record for complete processing

All decisions comply with Archive-RAG Constitution (Python-only, local JSON storage, no external database dependencies, deterministic behavior).


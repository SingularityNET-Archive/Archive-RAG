# Data Model: Refined Entity Extraction

**Feature**: Refine Entity Extraction  
**Date**: 2025-01-21  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

## Overview

This feature enhances the existing entity-based data model with refined extraction capabilities: entity normalization to avoid splits, Named Entity Recognition (NER) integration for text fields, relationship triple generation, and semantic chunking with entity metadata. The enhancements build upon the existing entity model (see [001-entity-data-model](../001-entity-data-model/data-model.md)) without changing core entity structures.

## New Data Structures

### Entity Normalization

**Description**: Canonical entity representation with normalized name variations merged into a single entity record.

**Implementation**:
- Existing entity models (Person, Workgroup, etc.) remain unchanged
- Normalization happens during entity extraction/creation phase
- Name variations (e.g., "Stephen", "Stephen [QADAO]") are mapped to canonical entity ID
- Only canonical entity is stored; variations are resolved to canonical before storage

**Normalization Rules**:
- Pattern-based normalization: Remove common suffixes (e.g., `[QADAO]`, `[ORG]`) using regex patterns
- Fuzzy similarity matching: Use rapidfuzz to match similar names (>95% similarity threshold)
- Context-based disambiguation: For ambiguous names, create separate entities initially, use meeting patterns/workgroup associations to merge later

**Storage**: Normalized entities stored in existing entity JSON files (no new file structure)

---

### Relationship Triple

**Description**: A triple connecting two entities in format "Subject -> Relationship -> Object".

**Format**: `Subject -> Relationship -> Object`

**Example Triples**:
- `Workgroup -> held -> Meeting`
- `Person -> attended -> Meeting`
- `Meeting -> produced -> Decision`
- `ActionItem -> assigned_to -> Person`
- `Decision -> has_effect -> Effect`

**Storage**: 
- Relationship triples are **not stored separately**
- Relationships embedded in entity JSON files (existing FK pattern)
- Triples generated on-demand from entity files when needed for output

**Generation Logic**:
```python
# Example: Generate triples from Meeting entity
meeting.workgroup_id → "Workgroup -> held -> Meeting"
meeting.people (via MeetingPerson) → "Person -> attended -> Meeting"
meeting.agenda_items → "Meeting -> has -> AgendaItem"
meeting.agenda_items.decision_items → "Meeting -> produced -> Decision"
```

---

### Chunk Metadata with Entities

**Description**: Entity information embedded in semantic chunks for embedding generation.

**Chunk Structure**:
```python
{
  "text": "Meeting summary text...",
  "entities": [
    {
      "entity_id": "uuid",
      "entity_type": "Person|Workgroup|Meeting|Document|Decision|ActionItem",
      "normalized_name": "Stephen",  # Canonical name
      "mentions": ["Stephen", "Stephen [QADAO]"]  # All name variations found
    }
  ],
  "metadata": {
    "meeting_id": "uuid",
    "chunk_type": "meeting_summary|action_item|decision_record|attendance|resource",
    "source_field": "meetingInfo.purpose|actionItems[]|decisionItems[]|peoplePresent|workingDocs[]",
    "relationships": [
      {"subject": "Person", "relationship": "attended", "object": "Meeting"}
    ]
  }
}
```

**Chunk Types** (Semantic Units):
- `meeting_summary`: `meetingInfo.purpose` field
- `action_item`: Each item in `actionItems[]` array
- `decision_record`: Each item in `decisionItems[]` array
- `attendance`: `peoplePresent` list
- `resource`: Each document in `workingDocs[]` array

**Storage**: Embedded in chunk JSON structure (existing chunk storage)

---

### NER-Extracted Entity

**Description**: Entities extracted from unstructured text fields using Named Entity Recognition (spaCy).

**Integration**:
- NER extracts entities from text fields (purpose, decision text, action item descriptions, etc.)
- Extracted entities are normalized and merged with structured JSON entities
- If NER entity conflicts with structured entity (same real-world object), NER entity merges into structured entity (structured entity is canonical)

**Entity Types Extracted**:
- PERSON (people mentioned in text)
- ORG (organizations mentioned)
- GPE (geopolitical entities - locations)
- DATE (dates mentioned in narrative)
- Other relevant spaCy entity types

**Storage**: Merged into existing entity JSON files (no separate NER entity storage)

---

## Enhanced Entity Extraction Process

### 1. JSON Structure Extraction

**Input**: MeetingRecord (JSON object)

**Process**:
- Treat all JSON objects as candidate entities
- Extract fields representing nouns/real-world objects:
  - `workgroup` → Workgroup entity
  - `meetingInfo` → Meeting entity
  - `peoplePresent` → Person entities
  - `workingDocs[]` → Document entities
  - `agendaItems[]` → AgendaItem entities
  - `agendaItems[].actionItems[]` → ActionItem entities
  - `agendaItems[].decisionItems[]` → DecisionItem entities

**Output**: Candidate entity list with source references

---

### 2. NER Text Field Extraction

**Input**: Text fields from MeetingRecord (purpose, decision text, action descriptions, etc.)

**Process**:
- Apply spaCy NER to all text fields
- Extract entities (PERSON, ORG, GPE, DATE, etc.)
- Filter entities by criteria (FR-013): entity is a thing OR searchable OR appears in multiple meetings OR provides context
- Filter out one-off filler comments

**Output**: NER-extracted entity list

---

### 3. Entity Normalization

**Input**: Candidate entities (JSON structure + NER extracted)

**Process**:
- Pattern-based normalization: Apply regex rules to remove common suffixes (e.g., `\[QADAO\]`, `\[ORG\]`)
- Fuzzy similarity matching: Use rapidfuzz to find similar names (>95% similarity)
- Merge variations into canonical entity:
  - If variation found → map to canonical entity ID
  - If new entity → create canonical entity
  - If ambiguous → create separate entities, mark for later disambiguation
- Store only canonical entity (variations resolved to canonical)

**Output**: Normalized entity list (canonical entities only)

---

### 4. Relationship Triple Generation

**Input**: Normalized entities with relationships from JSON structure

**Process**:
- Extract relationships from entity foreign keys and junction tables:
  - `Meeting.workgroup_id` → "Workgroup -> held -> Meeting"
  - `MeetingPerson` → "Person -> attended -> Meeting"
  - `ActionItem.assignee_id` → "ActionItem -> assigned_to -> Person"
  - `DecisionItem.effect` → "Decision -> has_effect -> Effect"
- Generate triple format: "Subject -> Relationship -> Object"

**Output**: Relationship triple list (for output generation, not stored)

---

### 5. Semantic Chunking with Entity Metadata

**Input**: MeetingRecord with normalized entities

**Process**:
- Chunk by semantic unit boundaries (not raw token counts):
  - `meetingInfo.purpose` → single meeting summary chunk
  - `actionItems[]` → separate chunk per action item
  - `decisionItems[]` → separate chunk per decision record
  - `peoplePresent` → single attendance chunk
  - `workingDocs[]` → separate chunk per document
- Embed entity metadata in each chunk:
  - Entities mentioned in chunk text
  - Normalized entity references
  - Relationships relevant to chunk
- If chunk exceeds token limit → split at sentence boundaries, preserve entity context in each split chunk

**Output**: Semantic chunks with embedded entity metadata

---

## Data Flow

```
MeetingRecord (JSON)
    ↓
[1] JSON Structure Extraction → Candidate Entities
    ↓
[2] NER Text Field Extraction → NER Entities
    ↓
[3] Entity Normalization → Canonical Entities
    ↓
[4] Relationship Triple Generation → Relationship Triples
    ↓
[5] Semantic Chunking with Metadata → Chunks with Entity Context
    ↓
Output: Structured Entity List + Normalized Cluster Labels + Relationship Triples + Chunks for Embedding
```

---

## Entity Extraction Criteria (FR-013)

Entities are extracted if they meet **at least one** criterion (OR logic):

1. **Entity is a thing**: Person, workgroup, document, meeting, decision, action item
2. **Searchable by users**: Users would search for this entity
3. **Appears in multiple meetings**: Entity appears across different meetings
4. **Provides context/references**: Entity provides context or is referenced in relationships

**Filtered Out**:
- One-off filler comments
- Entities that don't meet any criteria

---

## Integration with Existing Entity Model

This feature enhances the existing entity model without changing core structures:

- **Existing entities unchanged**: Workgroup, Meeting, Person, Document, AgendaItem, ActionItem, DecisionItem, Tag
- **New functionality**: Normalization layer, NER integration, relationship triple generation, semantic chunking
- **Storage unchanged**: Still uses local JSON files in `entities/` directory structure
- **Relationships unchanged**: Still uses FK pattern and junction tables (MeetingPerson)

---

## Determinism & Traceability

**Determinism**:
- Same MeetingRecord produces identical entity structure
- Normalization uses deterministic rules (pattern matching + fixed similarity threshold)
- NER uses version-locked spaCy model

**Traceability**:
- All entities traceable to source MeetingRecord (`meeting_id`, `date`, `workgroup`)
- Chunk metadata includes source field and meeting reference
- Relationship triples can be traced back to entity foreign keys


# Feature Specification: Refine Entity Extraction

**Feature Branch**: `004-refine-entity-extraction`  
**Created**: 2025-01-21  
**Status**: Draft  
**Input**: User description: "Refine entity extraction - I wish to refine entity extrcation from the source JSON. Examine the JSON and treat JSON objects as candidate entities. Extract fields that represent nouns or real-world objects. Capture relationships - for example - | Relationship           | Example                               | | ---------------------- | ------------------------------------- | | Workgroup → Meeting    | \"Archives WG\" had meeting Jan 08 2025 | | Meeting → People       | Meeting attended by X                 | | Meeting → Decisions    | Meeting produced decisions            | | Action Item → Assignee | Action assigned to André              | | Decision → Effect      | \`mayAffectOtherPeople\`                | .Apply named entity recognition (NER) to text fields. Normalize & store entity references Standardize entities to avoid splits (\"Stephen\", \"Stephen [QADAO]\"). Chunk text by entity context Before embedding, chunk by semantic unit, not raw tokens. Recommended chunks: Chunk Type	Example Meeting summary block	meetingInfo.purpose Action item block	actionItems[] Decision record	decisionItems[] Attendance block	peoplePresent list Resource block	workingDocs[] Output of entity extraction | Output Type               | Description                      | | ------------------------- | -------------------------------- | | Structured entity list    | People, roles, topics, decisions | | Normalized cluster labels | Canonical names/tags             | | Relationship triples      | \`Person -> attended -> Meeting\`  | | Chunks for embedding      | Text with metadata               | Extract it as an entity if it is: ✅ A thing (person, workgroup, doc, meeting) ✅ Something users might search for ✅ Something that appears in multiple meetings ✅ A source of context or references Don't extract one-off text like filler comments"

## Clarifications

### Session 2025-01-21

- Q: When normalizing entity name variations, should the system merge them into a single canonical entity immediately, or maintain both name variations with a canonical reference? → A: Merge variations into single canonical entity immediately (variations point to one canonical entity, only canonical stored)
- Q: When the system encounters an ambiguous name that could refer to multiple different entities (e.g., "John" appears in different meetings with different contexts), how should it resolve this? → A: Create separate entities initially, use context (meeting patterns, workgroup associations) to disambiguate and merge later
- Q: When evaluating whether to extract an entity, should all criteria be met (AND), or is meeting any one criterion sufficient (OR)? → A: Any criterion met (OR logic - entity is a thing OR searchable OR appears in multiple meetings OR provides context)
- Q: When NER extracts an entity that conflicts with a structured JSON entity, should the system discard the NER entity, merge it into the structured entity, or store it as an alternative name variation? → A: Merge NER entity into structured entity (NER name becomes variation, normalizes to structured entity)
- Q: When a semantic unit (e.g., a meeting summary block or decision record) exceeds embedding token limits, how should the system split it? → A: Split at sentence boundaries within semantic unit (preserve sentences, maintain entity mentions in each chunk)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract Entities from JSON Structure (Priority: P1)

A user ingests meeting records and expects the system to automatically identify all entities (people, workgroups, meetings, documents, decisions, action items) from the JSON structure, treating JSON objects as candidate entities.

**Why this priority**: Foundation for all other entity extraction - without recognizing entities in the JSON structure, relationship extraction and normalization cannot proceed.

**Independent Test**: Can be fully tested by ingesting a single meeting record with known entities (workgroup, meeting, people, documents) and verifying all entities are correctly identified and stored. Delivers immediate value by enabling structured data extraction.

**Acceptance Scenarios**:

1. **Given** a meeting record with workgroup, meetingInfo, peoplePresent, workingDocs, agendaItems, **When** the system processes the record, **Then** all JSON objects are treated as candidate entities and extracted
2. **Given** a meeting record with nested entities (agendaItems containing decisionItems and actionItems), **When** the system processes the record, **Then** all nested entities are identified and extracted
3. **Given** a meeting record with fields representing real-world objects (workgroup names, person names, document titles), **When** the system processes the record, **Then** these noun fields are extracted as entities
4. **Given** a meeting record with filler text or one-off comments, **When** the system processes the record, **Then** only meaningful entities are extracted (things users search for, appear in multiple meetings, or provide context)

---

### User Story 2 - Capture Entity Relationships (Priority: P1)

A user needs the system to automatically identify and store relationships between entities, such as which workgroup held a meeting, who attended meetings, what decisions were made, and who action items are assigned to.

**Why this priority**: Relationships enable navigation and context - users need to understand how entities connect to each other for meaningful queries and analysis.

**Independent Test**: Can be fully tested by ingesting a meeting record with known relationships (workgroup-meeting, meeting-people, meeting-decisions, action-assignee) and verifying all relationship triples are correctly captured. Delivers value by enabling relationship-based queries.

**Acceptance Scenarios**:

1. **Given** a meeting record where "Archives WG" held a meeting on Jan 08 2025, **When** the system processes the record, **Then** a Workgroup → Meeting relationship is captured
2. **Given** a meeting record with peoplePresent list, **When** the system processes the record, **Then** Meeting → People relationships are captured for all attendees
3. **Given** a meeting record with decisionItems, **When** the system processes the record, **Then** Meeting → Decisions relationships are captured
4. **Given** an action item with an assignee name, **When** the system processes the record, **Then** Action Item → Assignee relationship is captured
5. **Given** a decision item with an effect field (e.g., "mayAffectOtherPeople"), **When** the system processes the record, **Then** Decision → Effect relationship is captured

---

### User Story 3 - Normalize Entity References (Priority: P1)

A user expects the system to recognize that "Stephen" and "Stephen [QADAO]" refer to the same person, standardizing entity names to avoid duplicates and splits.

**Why this priority**: Critical for data quality - without normalization, the same entity appears multiple times, breaking queries and relationships. Users search for "Stephen" and expect to find all references regardless of variations.

**Independent Test**: Can be fully tested by ingesting meeting records where the same person appears with different name variations (e.g., "Stephen", "Stephen [QADAO]", "Stephen QADAO") and verifying all variations are normalized to a canonical name. Delivers value by preventing entity fragmentation.

**Acceptance Scenarios**:

1. **Given** meeting records where "Stephen" appears as "Stephen", "Stephen [QADAO]", and "Stephen QADAO", **When** the system processes the records, **Then** all variations are normalized to a canonical entity name
2. **Given** meeting records with person name variations, **When** the system processes the records, **Then** all entity references point to the normalized canonical name
3. **Given** meeting records with normalized entities, **When** a user queries for an entity by any of its variations, **Then** all references to that entity are returned
4. **Given** entity name variations that represent different people (e.g., "John Smith" vs "John Doe"), **When** the system processes the records, **Then** these are kept as separate entities

---

### User Story 4 - Apply Named Entity Recognition to Text Fields (Priority: P2)

A user needs the system to extract additional entities from unstructured text fields (like meeting purposes, decision text, action item descriptions) using Named Entity Recognition (NER) to find entities not explicitly structured in JSON.

**Why this priority**: Enhances entity discovery - text fields may contain entity mentions that aren't in structured fields, enabling more complete entity extraction and better search coverage.

**Independent Test**: Can be fully tested by processing meeting records with text fields containing entity mentions (e.g., organization names, locations, dates in narrative text) and verifying these entities are extracted via NER. Delivers value by discovering entities in unstructured content.

**Acceptance Scenarios**:

1. **Given** a meeting record with a purpose field containing "Discuss QADAO budget proposal", **When** the system processes the record, **Then** "QADAO" is extracted as an entity via NER
2. **Given** a decision text containing entity mentions not in structured fields, **When** the system processes the record, **Then** these entities are identified via NER and added to the entity list
3. **Given** text fields with entity mentions, **When** the system processes the record, **Then** extracted NER entities are normalized and merged with existing entity references
4. **Given** text fields with filler comments or one-off mentions, **When** the system processes the record, **Then** only meaningful entities (things users search for, appear multiple times, provide context) are extracted

---

### User Story 5 - Chunk Text by Semantic Unit Before Embedding (Priority: P2)

A user expects the system to chunk meeting content by semantic units (meeting summaries, action item blocks, decision records, attendance lists, resource blocks) rather than raw token counts, preserving entity context within chunks.

**Why this priority**: Improves embedding quality - semantic chunks maintain entity context, enabling better search results and relationship understanding in vector space.

**Independent Test**: Can be fully tested by processing a meeting record and verifying that chunks align with semantic units (meeting summary block, action item block, decision record, attendance block, resource block) rather than arbitrary token boundaries. Delivers value by improving search relevance.

**Acceptance Scenarios**:

1. **Given** a meeting record with meetingInfo.purpose, **When** the system chunks the content, **Then** the meeting summary block is kept as a single semantic chunk
2. **Given** a meeting record with actionItems array, **When** the system chunks the content, **Then** each action item block is a separate semantic chunk
3. **Given** a meeting record with decisionItems array, **When** the system chunks the content, **Then** each decision record is a separate semantic chunk
4. **Given** a meeting record with peoplePresent list, **When** the system chunks the content, **Then** the attendance block is kept as a single semantic chunk
5. **Given** a meeting record with workingDocs array, **When** the system chunks the content, **Then** each resource block (document) is a separate semantic chunk
6. **Given** semantic chunks with embedded entities, **When** chunks are created, **Then** entity metadata is included with each chunk for context

---

### User Story 6 - Generate Structured Entity Output (Priority: P2)

A user needs the system to produce structured outputs including normalized entity lists, relationship triples, and chunks with metadata for downstream processing and querying.

**Why this priority**: Enables downstream functionality - structured outputs are required for querying, relationship navigation, and embedding generation.

**Independent Test**: Can be fully tested by processing meeting records and verifying all required outputs (structured entity list, normalized cluster labels, relationship triples, chunks with metadata) are generated correctly. Delivers value by providing structured data for querying and analysis.

**Acceptance Scenarios**:

1. **Given** processed meeting records, **When** the system generates outputs, **Then** a structured entity list is produced containing all people, workgroups, topics, and decisions
2. **Given** processed meeting records with normalized entities, **When** the system generates outputs, **Then** normalized cluster labels (canonical names/tags) are produced
3. **Given** processed meeting records with relationships, **When** the system generates outputs, **Then** relationship triples are produced (e.g., "Person -> attended -> Meeting")
4. **Given** processed meeting records with semantic chunks, **When** the system generates outputs, **Then** chunks are produced with embedded entity metadata for embedding

---

### Edge Cases

- What happens when a meeting record has missing or null entity fields (e.g., no workgroup, no peoplePresent)?
- How does the system handle entity name variations that are ambiguous (e.g., "John" could refer to multiple people)? → System creates separate entities initially, then uses context (meeting patterns, workgroup associations) to disambiguate and merge later if they are the same entity
- What happens when NER extracts entities that conflict with structured JSON entities (e.g., NER finds "Stephen" but JSON has "Stephen [QADAO]")? → System merges NER entity into structured entity (NER name becomes variation that normalizes to structured entity)
- How does the system handle entities that appear in only one meeting (should they be extracted or filtered out)? → System extracts entities that appear in only one meeting if they meet at least one other criterion (e.g., searchable by users, provide context/references, or are a thing)
- What happens when semantic units are too large for embedding (exceed token limits)? → System splits at sentence boundaries within semantic unit, preserving sentences and maintaining entity mentions in each chunk
- How does the system handle malformed JSON or missing required fields?
- What happens when relationship data is incomplete (e.g., action item without assignee, decision without effect)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST treat all JSON objects in meeting records as candidate entities for extraction
- **FR-002**: System MUST extract fields that represent nouns or real-world objects (workgroups, people, meetings, documents, decisions, action items)
- **FR-003**: System MUST capture relationship triples between entities (Workgroup → Meeting, Meeting → People, Meeting → Decisions, Action Item → Assignee, Decision → Effect)
- **FR-004**: System MUST apply Named Entity Recognition (NER) to all text fields in meeting records
- **FR-005**: System MUST normalize entity references to avoid splits (e.g., "Stephen" and "Stephen [QADAO]" normalized to canonical name) by merging variations into a single canonical entity immediately
- **FR-006**: System MUST standardize entities by clustering similar names and variations to canonical labels, storing only the canonical entity (variations point to canonical, only canonical entity record is stored)
- **FR-007**: System MUST chunk text by semantic unit (meeting summary block, action item block, decision record, attendance block, resource block) before embedding
- **FR-008**: System MUST preserve entity context within semantic chunks (chunks include metadata about contained entities)
- **FR-009**: System MUST generate structured entity list output containing all extracted people, roles, topics, and decisions
- **FR-010**: System MUST generate normalized cluster labels output with canonical names and tags for all entities
- **FR-011**: System MUST generate relationship triples output in format "Subject -> Relationship -> Object"
- **FR-012**: System MUST generate chunks for embedding output with text and associated entity metadata
- **FR-013**: System MUST only extract entities that meet at least one criterion (OR logic): entity is a thing (person, workgroup, doc, meeting) OR searchable by users OR appears in multiple meetings OR provides context/references
- **FR-014**: System MUST filter out one-off text like filler comments from entity extraction
- **FR-015**: System MUST merge NER-extracted entities with structured JSON entities when they refer to the same real-world object
- **FR-016**: System MUST handle missing or null entity fields gracefully (skip extraction for missing fields without failing)
- **FR-017**: System MUST resolve entity name conflicts by preferring structured JSON entities over NER-extracted entities when both exist, merging NER entities into structured entities (NER name becomes a variation that normalizes to the structured entity)
- **FR-019**: System MUST create separate entities initially when ambiguous names could refer to multiple different entities, then use context (meeting patterns, workgroup associations) to disambiguate and merge later if they are determined to be the same entity
- **FR-018**: System MUST handle semantic units that exceed embedding token limits by splitting at sentence boundaries within the semantic unit, preserving sentences and maintaining entity mentions in each chunk

### Key Entities *(include if feature involves data)*

- **Entity Candidate**: A JSON object or field value that represents a noun or real-world object (person, workgroup, document, meeting, decision, action item)
- **Normalized Entity**: A canonical entity representation with standardized name and unique identifier, created by merging variations immediately into a single entity record (e.g., "Stephen" and "Stephen [QADAO]" → single canonical "Stephen" entity; all variations point to this canonical entity, only the canonical entity is stored)
- **Entity Relationship**: A triple connecting two entities (Subject -> Relationship Type -> Object), e.g., "Person -> attended -> Meeting", "Workgroup -> held -> Meeting"
- **Entity Cluster**: A group of entity name variations that refer to the same real-world object, normalized to a canonical label
- **Semantic Chunk**: A text unit aligned with semantic boundaries (meeting summary, action item, decision record, attendance list, resource block) rather than arbitrary token counts
- **Chunk Metadata**: Entity information embedded in semantic chunks, including which entities are mentioned, their relationships, and normalized references

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System extracts 100% of entities explicitly present in JSON structure (workgroups, meetings, people, documents, agenda items, action items, decision items) from meeting records
- **SC-002**: System captures 100% of relationship triples for explicit relationships in JSON structure (Workgroup → Meeting, Meeting → People, Meeting → Decisions, Action Item → Assignee, Decision → Effect)
- **SC-003**: System normalizes entity name variations with 95% accuracy (variations of the same entity are correctly merged to canonical names)
- **SC-004**: System extracts at least 80% of additional entities from text fields using NER that are not present in structured JSON fields
- **SC-005**: System chunks 100% of meeting content by semantic unit boundaries (meeting summary, action item, decision record, attendance, resource blocks) rather than raw token counts
- **SC-006**: System preserves entity context in 100% of semantic chunks (each chunk includes metadata about contained entities)
- **SC-007**: System generates structured entity list, normalized cluster labels, relationship triples, and chunks with metadata for 100% of processed meeting records
- **SC-008**: System filters out 100% of one-off filler comments from entity extraction (only meaningful, searchable entities are extracted)
- **SC-009**: System handles meeting records with missing entity fields without errors (gracefully skips missing fields)
- **SC-010**: Users can query for entities using any name variation and receive 100% of results for that entity (normalization enables complete entity discovery)

## Assumptions

- Source JSON follows the established meeting record structure with workgroup, meetingInfo, agendaItems, tags, etc.
- Entity normalization can be achieved through pattern matching, similarity algorithms, and manual rules (e.g., recognizing "[QADAO]" as a suffix to be normalized)
- NER models are available and can be configured to extract relevant entity types (PERSON, ORG, etc.)
- Semantic chunking boundaries are defined by JSON structure (meetingInfo.purpose = meeting summary block, actionItems[] = action item blocks, etc.)
- Users expect entity extraction to happen automatically during meeting record ingestion
- Entity extraction outputs are stored for downstream querying and embedding generation
- Relationship triples follow Subject -> Relationship -> Object format
- Chunks can include metadata alongside text content for embedding

# Tasks: Refine Entity Extraction

**Input**: Design documents from `/specs/004-refine-entity-extraction/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are NOT included (not requested in spec). Focus on implementation tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency installation, and configuration

- [X] T001 Update `requirements.txt` to add `rapidfuzz>=3.0.0` dependency
- [X] T002 Update `pyproject.toml` to add `rapidfuzz>=3.0.0` dependency
- [X] T003 [P] Update `src/lib/config.py` to add entity normalization configuration (similarity_threshold, pattern_rules, enable_fuzzy_matching, enable_context_disambiguation)
- [X] T004 [P] Update `src/lib/config.py` to add NER configuration (model_name, entity_types, min_confidence, filter_criteria)
- [X] T005 [P] Update `src/lib/config.py` to add chunking configuration (max_tokens_per_chunk, split_at_sentence_boundaries, preserve_entity_context, chunk_types)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core services that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Create `src/models/relationship_triple.py` with RelationshipTriple model (subject_id, subject_type, subject_name, relationship, object_id, object_type, object_name, source_meeting_id, source_field)
- [X] T007 [P] Create `src/models/chunk_metadata.py` with ChunkMetadata model (entities list, meeting_id, chunk_type, source_field, relationships list, chunk_index, total_chunks)
- [X] T008 [P] Create `src/models/ner_entity.py` with NEREntity model (text, entity_type, source_text, source_field, source_meeting_id, normalized_entity_id, confidence)
- [X] T009 Create `src/services/entity_normalization.py` with EntityNormalizationService class
- [X] T010 [P] Implement `normalize_entity_name()` method in `src/services/entity_normalization.py` that returns canonical entity ID and canonical name
- [X] T011 [P] Implement `merge_variations()` method in `src/services/entity_normalization.py` that merges name variations into canonical name
- [X] T012 [P] Implement `find_similar_entities()` method in `src/services/entity_normalization.py` using rapidfuzz with >95% similarity threshold
- [X] T013 [P] Implement pattern-based normalization rules in `src/services/entity_normalization.py` using regex to remove suffixes (e.g., `[QADAO]`, `[ORG]`)
- [X] T014 Create `src/services/relationship_triple_generator.py` with RelationshipTripleGenerator class
- [X] T015 [P] Implement `generate_triples()` method in `src/services/relationship_triple_generator.py` that generates relationship triples from entities
- [X] T016 [P] Implement `get_triples_for_entity()` method in `src/services/relationship_triple_generator.py` that gets all triples involving an entity
- [X] T017 Create `src/services/semantic_chunking.py` with SemanticChunkingService class
- [X] T018 [P] Implement `chunk_by_semantic_unit()` method in `src/services/semantic_chunking.py` that creates semantic chunks with entity metadata
- [X] T019 [P] Implement `split_chunk_if_needed()` method in `src/services/semantic_chunking.py` that splits chunks at sentence boundaries if exceeds token limit
- [X] T020 Create `src/services/ner_integration.py` with NERIntegrationService class
- [X] T021 [P] Implement `extract_from_text()` method in `src/services/ner_integration.py` that extracts entities from text using spaCy NER
- [X] T022 [P] Implement `merge_with_structured()` method in `src/services/ner_integration.py` that merges NER entities with structured entities

**Checkpoint**: Foundation ready - all core services implemented. User story implementation can now begin.

---

## Phase 3: User Story 1 - Extract Entities from JSON Structure (Priority: P1) 🎯 MVP

**Goal**: Enable users to automatically identify all entities (people, workgroups, meetings, documents, decisions, action items) from JSON structure, treating JSON objects as candidate entities.

**Independent Test**: Ingest a single meeting record with known entities (workgroup, meeting, people, documents) and verify all entities are correctly identified and stored.

### Implementation for User Story 1

- [X] T023 [US1] Enhance `src/services/meeting_to_entity.py` to treat all JSON objects in MeetingRecord as candidate entities
- [X] T024 [US1] Implement entity candidate extraction in `src/services/meeting_to_entity.py` for workgroup field (extract workgroup name as entity)
- [X] T025 [US1] Implement entity candidate extraction in `src/services/meeting_to_entity.py` for meetingInfo fields (extract meeting as entity)
- [X] T026 [US1] Implement entity candidate extraction in `src/services/meeting_to_entity.py` for peoplePresent list (extract each person as entity)
- [X] T027 [US1] Implement entity candidate extraction in `src/services/meeting_to_entity.py` for workingDocs array (extract each document as entity)
- [X] T028 [US1] Implement entity candidate extraction in `src/services/meeting_to_entity.py` for agendaItems array (extract each agenda item as entity)
- [X] T029 [US1] Implement entity candidate extraction in `src/services/meeting_to_entity.py` for nested decisionItems (extract each decision item as entity)
- [X] T030 [US1] Implement entity candidate extraction in `src/services/meeting_to_entity.py` for nested actionItems (extract each action item as entity)
- [X] T031 [US1] Implement entity filtering logic in `src/services/meeting_to_entity.py` to filter out one-off filler comments (FR-014)
- [X] T032 [US1] Implement entity extraction criteria check in `src/services/meeting_to_entity.py` (FR-013: entity is a thing OR searchable OR appears in multiple meetings OR provides context)
- [X] T033 [US1] Update `src/services/entity_extraction.py` to integrate with enhanced entity candidate extraction

**Checkpoint**: User Story 1 complete. System can extract entities from JSON structure, treating all JSON objects as candidate entities.

---

## Phase 4: User Story 2 - Capture Entity Relationships (Priority: P1)

**Goal**: Enable users to automatically identify and store relationships between entities (workgroup held meeting, people attended meetings, decisions made, action items assigned).

**Independent Test**: Ingest a meeting record with known relationships (workgroup-meeting, meeting-people, meeting-decisions, action-assignee) and verify all relationship triples are correctly captured.

### Implementation for User Story 2

- [X] T034 [US2] Implement Workgroup → Meeting relationship extraction in `src/services/meeting_to_entity.py` (from workgroup_id FK)
- [X] T035 [US2] Implement Meeting → People relationship extraction in `src/services/meeting_to_entity.py` (from peoplePresent list via MeetingPerson junction)
- [X] T036 [US2] Implement Meeting → Decisions relationship extraction in `src/services/meeting_to_entity.py` (from decisionItems array)
- [X] T037 [US2] Implement Action Item → Assignee relationship extraction in `src/services/meeting_to_entity.py` (from assignee_id FK)
- [X] T038 [US2] Implement Decision → Effect relationship extraction in `src/services/meeting_to_entity.py` (from effect field)
- [X] T039 [US2] Integrate RelationshipTripleGenerator with entity extraction process in `src/services/meeting_to_entity.py`
- [X] T040 [US2] Implement relationship triple generation for all extracted relationships in `src/services/meeting_to_entity.py`
- [X] T041 [US2] Update entity storage to preserve relationship data in entity JSON files (existing FK pattern)

**Checkpoint**: User Story 2 complete. System can capture all entity relationships and generate relationship triples.

---

## Phase 5: User Story 3 - Normalize Entity References (Priority: P1)

**Goal**: Enable users to query entities using any name variation, with system recognizing that "Stephen" and "Stephen [QADAO]" refer to the same person.

**Independent Test**: Ingest meeting records where the same person appears with different name variations (e.g., "Stephen", "Stephen [QADAO]", "Stephen QADAO") and verify all variations are normalized to canonical name.

### Implementation for User Story 3

- [X] T042 [US3] Integrate EntityNormalizationService into entity extraction process in `src/services/meeting_to_entity.py`
- [X] T043 [US3] Implement pattern-based normalization in `src/services/meeting_to_entity.py` to normalize entity name variations (e.g., remove `[QADAO]` suffix)
- [X] T044 [US3] Implement fuzzy similarity matching in `src/services/meeting_to_entity.py` to find similar entity names (>95% similarity)
- [X] T045 [US3] Implement entity merging logic in `src/services/meeting_to_entity.py` to merge variations into single canonical entity immediately
- [X] T046 [US3] Implement entity reference updating in `src/services/meeting_to_entity.py` to point all variations to canonical entity ID
- [X] T047 [US3] Implement ambiguous name handling in `src/services/meeting_to_entity.py` (create separate entities initially, use context for disambiguation later)
- [X] T048 [US3] Update entity storage in `src/services/entity_storage.py` to store only canonical entities (variations resolved to canonical before storage)
- [X] T049 [US3] Implement entity lookup by any variation in `src/services/entity_query.py` (query by variation returns canonical entity)
- [X] T050 [US3] Update Person entity model in `src/models/person.py` to track normalized_variations (if needed for tracking)

**Checkpoint**: User Story 3 complete. System can normalize entity name variations and merge them into canonical entities.

---

## Phase 6: User Story 4 - Apply Named Entity Recognition to Text Fields (Priority: P2)

**Goal**: Enable users to extract additional entities from unstructured text fields using NER to find entities not explicitly structured in JSON.

**Independent Test**: Process meeting records with text fields containing entity mentions (e.g., organization names, locations, dates) and verify these entities are extracted via NER.

### Implementation for User Story 4

- [X] T051 [US4] Integrate NERIntegrationService into entity extraction process in `src/services/meeting_to_entity.py`
- [X] T052 [US4] Implement NER extraction for meetingInfo.purpose field in `src/services/meeting_to_entity.py`
- [X] T053 [US4] Implement NER extraction for decision text fields in `src/services/meeting_to_entity.py`
- [X] T054 [US4] Implement NER extraction for action item description fields in `src/services/meeting_to_entity.py`
- [X] T055 [US4] Implement NER entity filtering in `src/services/ner_integration.py` to filter by extraction criteria (FR-013: entity is a thing OR searchable OR appears in multiple meetings OR provides context)
- [X] T056 [US4] Implement NER entity filtering in `src/services/ner_integration.py` to filter out one-off filler comments (FR-014)
- [X] T057 [US4] Implement NER entity merging with structured entities in `src/services/ner_integration.py` (merge NER entity into structured entity when conflicts)
- [X] T058 [US4] Implement NER entity normalization in `src/services/ner_integration.py` to normalize extracted entities using EntityNormalizationService
- [X] T059 [US4] Update entity extraction output to include NER-extracted entities in `src/services/meeting_to_entity.py`

**Checkpoint**: User Story 4 complete. System can extract entities from unstructured text fields using NER and merge them with structured entities.

---

## Phase 7: User Story 5 - Chunk Text by Semantic Unit Before Embedding (Priority: P2)

**Goal**: Enable users to chunk meeting content by semantic units (meeting summaries, action item blocks, decision records, attendance lists, resource blocks) rather than raw token counts.

**Independent Test**: Process a meeting record and verify that chunks align with semantic units (meeting summary block, action item block, decision record, attendance block, resource block) rather than arbitrary token boundaries.

### Implementation for User Story 5

- [ ] T060 [US5] Integrate SemanticChunkingService into chunking process in `src/services/chunking.py`
- [ ] T061 [US5] Implement meeting summary chunking in `src/services/chunking.py` (meetingInfo.purpose → single semantic chunk)
- [ ] T062 [US5] Implement action item chunking in `src/services/chunking.py` (each actionItems[] item → separate chunk)
- [ ] T063 [US5] Implement decision record chunking in `src/services/chunking.py` (each decisionItems[] item → separate chunk)
- [ ] T064 [US5] Implement attendance chunking in `src/services/chunking.py` (peoplePresent list → single chunk)
- [ ] T065 [US5] Implement resource chunking in `src/services/chunking.py` (each workingDocs[] item → separate chunk)
- [ ] T066 [US5] Implement entity metadata embedding in chunks in `src/services/chunking.py` (embed entities mentioned in chunk, normalized references, relationships)
- [ ] T067 [US5] Implement chunk splitting at sentence boundaries in `src/services/chunking.py` for chunks exceeding token limits (FR-018)
- [ ] T068 [US5] Implement entity context preservation in split chunks in `src/services/chunking.py` (maintain entity metadata in each split chunk)
- [ ] T069 [US5] Update chunk structure to include ChunkMetadata model in `src/services/chunking.py`

**Checkpoint**: User Story 5 complete. System can chunk meeting content by semantic units with embedded entity metadata.

---

## Phase 8: User Story 6 - Generate Structured Entity Output (Priority: P2)

**Goal**: Enable users to produce structured outputs including normalized entity lists, relationship triples, and chunks with metadata for downstream processing and querying.

**Independent Test**: Process meeting records and verify all required outputs (structured entity list, normalized cluster labels, relationship triples, chunks with metadata) are generated correctly.

### Implementation for User Story 6

- [ ] T070 [US6] Implement structured entity list generation in `src/services/meeting_to_entity.py` (all extracted people, roles, topics, decisions)
- [ ] T071 [US6] Implement normalized cluster labels generation in `src/services/meeting_to_entity.py` (canonical names/tags for all entities)
- [ ] T072 [US6] Implement relationship triple output generation in `src/services/relationship_triple_generator.py` (format: "Subject -> Relationship -> Object")
- [ ] T073 [US6] Implement chunks for embedding output generation in `src/services/chunking.py` (chunks with embedded entity metadata)
- [ ] T074 [US6] Create output formatter service in `src/services/entity_output_formatter.py` to format all outputs (structured entity list, normalized cluster labels, relationship triples, chunks)
- [ ] T075 [US6] Integrate output formatter with entity extraction process in `src/services/meeting_to_entity.py`
- [ ] T076 [US6] Update CLI command in `src/cli/ingest_entities.py` to output structured entity extraction results (if CLI command exists)

**Checkpoint**: User Story 6 complete. System can generate all required structured outputs for downstream processing.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, performance optimization, edge cases, and integration

- [x] T077 Implement graceful handling of missing entity fields in `src/services/meeting_to_entity.py` (FR-016: skip extraction for missing fields without failing)
- [x] T078 Implement malformed JSON handling in `src/services/meeting_to_entity.py` (edge case: handle malformed JSON or missing required fields)
- [x] T079 Implement incomplete relationship data handling in `src/services/meeting_to_entity.py` (edge case: action item without assignee, decision without effect)
- [x] T080 Implement entity context-based disambiguation in `src/services/entity_normalization.py` (use meeting patterns/workgroup associations to merge ambiguous entities)
- [x] T081 Add performance monitoring/logging in `src/services/meeting_to_entity.py` to track processing time per meeting record (<2 seconds target)
- [x] T082 Optimize entity normalization with caching in `src/services/entity_normalization.py` (cache entity lookups for faster processing)
- [x] T083 Add comprehensive logging for entity extraction process in `src/services/meeting_to_entity.py` (traceability to source meeting records)
- [x] T084 Update documentation in `specs/004-refine-entity-extraction/quickstart.md` with actual usage examples after implementation

---

## Dependencies & Story Completion Order

### Parallel Opportunities

**Phase 2 (Foundational)**: Tasks T007, T008, T010, T011, T012, T013, T015, T016, T018, T019, T021, T022 can run in parallel (different services/models)

**Phase 3 (US1)**: Tasks T024-T030 can run in parallel (different entity types)

**Phase 4 (US2)**: Tasks T034-T038 can run in parallel (different relationship types)

**Phase 6 (US4)**: Tasks T052-T054 can run in parallel (different text fields)

**Phase 7 (US5)**: Tasks T061-T065 can run in parallel (different chunk types)

### Story Dependencies

- **US1** (Extract Entities) → **MUST** complete before US2, US3, US4 (foundation for all)
- **US2** (Capture Relationships) → **MUST** complete after US1 (needs entities first)
- **US3** (Normalize Entities) → **MUST** complete after US1 (needs entities first), can run parallel with US2
- **US4** (NER Integration) → **MUST** complete after US1, US3 (needs entity extraction and normalization)
- **US5** (Semantic Chunking) → **MUST** complete after US1, US3 (needs entities and normalized entities)
- **US6** (Generate Output) → **MUST** complete after all other stories (depends on all outputs)

### Implementation Strategy

**MVP Scope**: User Stories 1, 2, 3 (P1 priorities) - Core entity extraction, relationship capture, and normalization

**Incremental Delivery**:
1. **MVP**: US1 + US2 + US3 (P1) - Core functionality
2. **Enhancement 1**: US4 (P2) - NER integration
3. **Enhancement 2**: US5 (P2) - Semantic chunking
4. **Enhancement 3**: US6 (P2) - Structured output generation

---

## Summary

- **Total Tasks**: 84 tasks
- **User Story Tasks**:
  - US1 (Extract Entities): 11 tasks
  - US2 (Capture Relationships): 8 tasks
  - US3 (Normalize Entities): 9 tasks
  - US4 (NER Integration): 9 tasks
  - US5 (Semantic Chunking): 10 tasks
  - US6 (Generate Output): 7 tasks
  - Setup: 5 tasks
  - Foundational: 17 tasks
  - Polish: 8 tasks

- **Parallel Opportunities**: Multiple tasks can run in parallel within phases (marked with [P])
- **Independent Test Criteria**: Each user story has independent test criteria defined
- **MVP Scope**: User Stories 1, 2, 3 (P1 priorities) for core functionality

**Format Validation**: ✅ All tasks follow checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`


# Tasks: Archive Meeting Retrieval & Grounded Interpretation RAG

**Input**: Design documents from `/specs/001-archive-meeting-rag/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included as optional - following Test-First Governance principle from constitution. Tests should be written first and fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below follow single Python project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per implementation plan (src/, tests/, data/ directories)
- [X] T002 Initialize Python 3.11 project with requirements.txt
- [X] T003 [P] Add dependencies to requirements.txt: sentence-transformers, faiss-cpu, transformers, typer, structlog, pytest, gensim, spacy
- [X] T004 [P] Create .gitignore for audit_logs/, indexes/, __pycache__, .venv/, *.pyc
- [X] T005 [P] Setup pytest configuration in pytest.ini or pyproject.toml
- [X] T006 Create README.md with project overview and quickstart link

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create base configuration management in src/lib/config.py (seed defaults, model paths, etc.)
- [X] T008 Implement SHA-256 hashing utility in src/lib/hashing.py (FR-011)
- [X] T009 [P] Implement PII detection utility using spaCy in src/lib/pii_detection.py (FR-012)
- [X] T010 [P] Implement citation parsing/formating utility in src/lib/citation.py (format: [meeting_id | date | speaker])
- [X] T011 Setup structlog JSON logging infrastructure in src/lib/logging.py
- [X] T012 Create audit log directory structure and persistence logic in src/lib/audit.py
- [X] T013 Create base data validation utilities in src/lib/validation.py (JSON validation, ISO 8601 date validation)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Retrieve Verified Facts From Meeting Records (Priority: P1) 🎯 MVP

**Goal**: User asks questions about historical meetings and receives factual, citation-grounded answers sourced only from meeting JSON logs.

**Independent Test**: Run a query against known meeting JSON and confirm output contains: extracted facts, source citations with meeting ID + timestamps, no hallucinations.

### Tests for User Story 1 (OPTIONAL - Test-First Governance) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] Contract test for index command in tests/contract/test_index_command.py
- [ ] T015 [P] [US1] Contract test for query command in tests/contract/test_query_command.py
- [ ] T016 [P] [US1] Integration test for query journey in tests/integration/test_query_flow.py
- [ ] T017 [P] [US1] Unit test for citation format validation in tests/unit/test_citation_format.py

### Implementation for User Story 1

- [X] T018 [P] [US1] Create MeetingRecord model in src/models/meeting_record.py (id, date, participants, transcript, decisions, tags)
- [X] T019 [P] [US1] Create EmbeddingIndex model in src/models/embedding_index.py (index_id, version_hash, embedding_model, metadata, etc.)
- [X] T020 [P] [US1] Create RAGQuery model in src/models/rag_query.py (query_id, user_input, retrieved_chunks, output, citations, evidence_found, etc.)
- [X] T021 [US1] Implement JSON ingestion service in src/services/ingestion.py (read, validate MeetingRecord, compute SHA-256 hash)
- [X] T022 [US1] Implement document chunking service in src/services/chunking.py (chunk transcript with overlap, metadata preservation)
- [X] T023 [US1] Implement embedding service using sentence-transformers in src/services/embedding.py (local model, deterministic seeds)
- [X] T024 [US1] Implement FAISS index builder service in src/services/index_builder.py (create FAISS index, store metadata mapping, version hash)
- [X] T025 [US1] Implement FAISS retrieval service in src/services/retrieval.py (load index, query embedding, top-k similarity search)
- [X] T026 [US1] Implement RAG generation service in src/services/rag_generator.py (LLM with retrieved context only, deterministic inference)
- [X] T027 [US1] Implement citation extraction service in src/services/citation_extractor.py (format: [meeting_id | date | speaker], traceable to retrieved chunks)
- [X] T028 [US1] Implement evidence checking service in src/services/evidence_checker.py ("No evidence found" when no credible evidence - FR-008)
- [X] T029 [US1] Implement index CLI command in src/cli/index.py (index command: INPUT_DIR, OUTPUT_INDEX, options for embedding-model, chunk-size, seed, hash-only, verify-hash, redact-pii)
- [X] T030 [US1] Implement query CLI command in src/cli/query.py (query command: INDEX_FILE, QUERY, options for model, model-version, top-k, seed, output-format, user-id)
- [X] T031 [US1] Create main CLI entry point in src/cli/main.py (typer app, register index and query commands)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Users can index meeting JSON and query the RAG system with citation-grounded answers.

---

## Phase 4: User Story 2 — Provide Traceable Evidence & Audit Logs (Priority: P1)

**Goal**: The system logs all queries, context, and outputs for audit. Institutional trust requires traceability.

**Independent Test**: Submit one query → verify a structured audit record is created with: input, retrieved text, model version, data version, timestamp, user ID (if applicable).

### Tests for User Story 2 (OPTIONAL - Test-First Governance) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T032 [P] [US2] Contract test for audit-view command in tests/contract/test_audit_view_command.py
- [ ] T033 [P] [US2] Integration test for audit logging in tests/integration/test_audit_logging.py
- [ ] T034 [P] [US2] Unit test for audit log structure in tests/unit/test_audit_structure.py

### Implementation for User Story 2

- [ ] T035 [US2] Enhance query flow to create audit log entry after query completion in src/services/query_service.py
- [ ] T036 [US2] Implement audit log writer service in src/services/audit_writer.py (immutable JSON logs, structured format with query, retrieved sources, model version, output, user ID)
- [ ] T037 [US2] Integrate SSO user ID extraction in src/lib/auth.py (FR-013 - extract user ID from SSO context for audit logs)
- [ ] T038 [US2] Implement audit log retention logic in src/services/audit_retention.py (3-year retention per FR-014)
- [ ] T039 [US2] Implement audit-view CLI command in src/cli/audit_view.py (view logs, filter by query-id, user-id, date-from, date-to, format, export - supports peer review workflow per SC-006)
- [ ] T040 [US2] Register audit-view command in src/cli/main.py
- [ ] T041 [US2] Add audit logging to index command (log indexing operations)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Every query produces an immutable audit log entry with full provenance.

---

## Phase 5: User Story 3 — Topic Modeling & Entity Extraction (Priority: P2)

**Goal**: User can explore high-level topics and entities from the meeting archive. Supports data discovery and better retrieval relevance.

**Independent Test**: Run topic modeling + entity extraction script → outputs reproducible clusters + entity lists with no personal data invented.

### Tests for User Story 3 (OPTIONAL - Test-First Governance) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T042 [P] [US3] Contract test for topic-model command in tests/contract/test_topic_model_command.py
- [ ] T043 [P] [US3] Contract test for extract-entities command in tests/contract/test_extract_entities_command.py
- [ ] T044 [P] [US3] Integration test for topic modeling flow in tests/integration/test_topic_modeling.py
- [ ] T045 [P] [US3] Integration test for entity extraction flow in tests/integration/test_entity_extraction.py

### Implementation for User Story 3

- [ ] T046 [US3] Implement topic modeling service using gensim in src/services/topic_modeling.py (LDA with deterministic seeds, advisory only)
- [ ] T047 [US3] Implement BERTopic-lite alternative in src/services/topic_modeling_bertopic.py (optional method, advisory only)
- [ ] T048 [US3] Enhance entity extraction service using spaCy in src/services/entity_extraction.py (NER, aggregate by type and frequency, PII redaction before extraction)
- [ ] T049 [US3] Implement topic-model CLI command in src/cli/topic_model.py (topic-model command: INDEX_FILE, OUTPUT_DIR, options for num-topics, method, seed, no-pii)
- [ ] T050 [US3] Implement extract-entities CLI command in src/cli/extract_entities.py (extract-entities command: INDEX_FILE, OUTPUT_DIR, options for model, entity-types, min-frequency, no-pii)
- [ ] T051 [US3] Register topic-model and extract-entities commands in src/cli/main.py
- [ ] T052 [US3] Add audit logging for topic modeling operations (advisory logging per constitution)
- [ ] T053 [US3] Add audit logging for entity extraction operations (advisory logging per constitution)

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently. Users can discover topics and entities from the archive with advisory results logged for auditability.

---

## Phase 6: User Story 4 — Evaluation & Governance Tools (Priority: P3)

**Goal**: Provide benchmark questions + scoring script to measure factuality & citation compliance. Guarantees ongoing trust and prevents silent hallucination regressions.

**Independent Test**: Execute evaluation script → score RAG performance, flag incorrect answers. Validate citation accuracy ≥90% (SC-001), hallucination count = 0 (SC-002), retrieval latency <2s (SC-003), reproducible audit logs (SC-004), entity extraction precision ≥85% (SC-005), peer review <3 steps (SC-006).

### Tests for User Story 4 (OPTIONAL - Test-First Governance) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T054 [P] [US4] Contract test for evaluate command in tests/contract/test_evaluate_command.py
- [ ] T055 [P] [US4] Integration test for evaluation flow in tests/integration/test_evaluation.py
- [ ] T056 [P] [US4] Unit test for citation accuracy scoring in tests/unit/test_citation_accuracy.py
- [ ] T057 [P] [US4] Unit test for factuality scoring in tests/unit/test_factuality.py

### Implementation for User Story 4

- [ ] T058 [P] [US4] Create EvaluationCase model in src/models/evaluation_case.py (case_id, prompt, ground_truth, expected_citations, evaluation_metrics, etc.)
- [ ] T059 [US4] Create sample benchmark dataset in data/benchmarks/eval.json (EvaluationCase format with prompts, ground truth, expected citations)
- [ ] T060 [US4] Implement citation accuracy scorer in src/services/citation_scorer.py (validate citation format, compare against expected citations, compute accuracy ≥90% per SC-001)
- [ ] T061 [US4] Implement factuality scorer in src/services/factuality_scorer.py (compare output against ground truth, detect hallucinations - must be 0 per SC-002)
- [ ] T062 [US4] Implement retrieval latency measurement in src/services/latency_measurement.py (<2s target per SC-003)
- [ ] T063 [US4] Implement evaluation runner service in src/services/evaluation_runner.py (load benchmark, run queries, compute metrics, aggregate results)
- [ ] T064 [US4] Implement evaluation report generator in src/services/report_generator.py (format results in report or JSON format)
- [ ] T065 [US4] Implement evaluate CLI command in src/cli/evaluate.py (evaluate command: INDEX_FILE, BENCHMARK_FILE, OUTPUT_DIR, options for model, model-version, seed, output-format)
- [ ] T066 [US4] Register evaluate command in src/cli/main.py
- [ ] T067 [US4] Add audit logging for evaluation operations
- [ ] T068 [US4] Implement reproducible audit log validation in tests/integration/test_audit_reproducibility.py (validate SC-004: same query + seed produces identical audit log)
- [ ] T069 [US4] Add entity extraction precision validation to evaluation runner in src/services/evaluation_runner.py (compute and validate ≥85% precision per SC-005)
- [ ] T070 [US4] Implement peer review workflow validation in tests/integration/test_peer_review_workflow.py (validate SC-006: peer reviewer validates claim in <3 CLI steps using audit-view)

**Checkpoint**: At this point, all user stories should now be independently functional. The system includes full evaluation capabilities to measure and maintain citation accuracy and factuality.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T071 [P] Create sample meeting JSON files in data/sample/ for testing
- [ ] T072 [P] Add comprehensive error handling across all CLI commands (invalid JSON, index not found, model loading failure, etc.)
- [ ] T073 [P] Implement deterministic seed management across all services (embeddings, LLM inference, FAISS, topic modeling)
- [ ] T074 [P] Add version tracking for models in index metadata (embedding version, LLM version for reproducibility)
- [ ] T075 [P] Optimize FAISS index for <2s retrieval latency (IndexFlatIP or IndexIVFFlat for 10k docs)
- [ ] T076 [P] Implement memory optimization for <4GB RAM target (quantized models, lazy loading)
- [ ] T077 [P] Add golden file tests for citation format validation in tests/golden/test_citation_format.py
- [ ] T078 [P] Add integration tests for end-to-end query flow with real meeting JSON in tests/integration/test_full_rag_flow.py
- [ ] T079 Update quickstart.md validation (verify all commands work as documented)
- [ ] T080 [P] Add unit tests for utility functions in tests/unit/ (hashing, PII detection, citation parsing, validation)
- [ ] T081 [P] Security hardening: validate input sanitization, secure hash storage, PII redaction verification
- [ ] T082 [P] Performance testing: validate <2s retrieval latency for 10k docs, <4GB RAM usage
- [ ] T083 Documentation updates: ensure README.md reflects quickstart.md, add architecture diagrams if needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
  - Core RAG functionality: indexing, querying, citation extraction
  - **MVP Scope**: User Story 1 alone provides working RAG system
  
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Integrates with US1 for audit logging
  - Can be implemented in parallel with US1 or after US1
  - Independent testable: audit logging works independently
  - Adds audit capability to existing queries

- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Uses indexed data from US1
  - Independent testable: topic modeling and entity extraction work on any index
  - Does not require query functionality
  - Can run in parallel with US1/US2

- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Requires US1 query functionality
  - Depends on US1 for query execution
  - Independent testable: evaluation can run on any working RAG system
  - Can be implemented after US1

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before CLI commands
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup Phase**: T003, T004, T005 can run in parallel (different files)
- **Foundational Phase**: T009, T010 can run in parallel (different utility modules)
- **User Story 1**: 
  - Models (T018, T019, T020) can run in parallel
  - Tests (T014, T015, T016, T017) can run in parallel
  - Services (T021-T028) must run sequentially due to dependencies
- **User Story 2**: Tests (T032, T033, T034) can run in parallel
- **User Story 3**: Tests (T042, T043, T044, T045) can run in parallel
- **User Story 4**: Tests (T054, T055, T056, T057) can run in parallel; Validation tasks (T068, T069, T070) can run in parallel
- **Polish Phase**: Many tasks marked [P] can run in parallel (T071-T082)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: T014 [P] [US1] Contract test for index command in tests/contract/test_index_command.py
Task: T015 [P] [US1] Contract test for query command in tests/contract/test_query_command.py
Task: T016 [P] [US1] Integration test for query journey in tests/integration/test_query_flow.py
Task: T017 [P] [US1] Unit test for citation format validation in tests/unit/test_citation_format.py

# Launch all models for User Story 1 together:
Task: T018 [P] [US1] Create MeetingRecord model in src/models/meeting_record.py
Task: T019 [P] [US1] Create EmbeddingIndex model in src/models/embedding_index.py
Task: T020 [P] [US1] Create RAGQuery model in src/models/rag_query.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T013) - **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T014-T031)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Index meeting JSON files
   - Query with known questions
   - Verify citations in format [meeting_id | date | speaker]
   - Verify "No evidence found" when appropriate
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
   - Core RAG functionality with citations
3. Add User Story 2 → Test independently → Deploy/Demo
   - Audit logging adds transparency
4. Add User Story 3 → Test independently → Deploy/Demo
   - Topic modeling and entity extraction for discovery
5. Add User Story 4 → Test independently → Deploy/Demo
   - Evaluation suite for ongoing governance
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - **Developer A**: User Story 1 (core RAG)
   - **Developer B**: User Story 2 (audit logging) - can start in parallel
   - **Developer C**: User Story 3 (topic modeling) - can start in parallel
3. After US1 complete:
   - **Developer A**: User Story 4 (evaluation)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Tests are optional but recommended for Test-First Governance (constitution principle IV)
- All tasks must support deterministic, reproducible behavior (constitution principle III)
- All tasks must enable auditability and transparency (constitution principle V)

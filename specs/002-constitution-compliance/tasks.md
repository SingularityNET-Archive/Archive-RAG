# Tasks: Constitution Compliance

**Input**: Design documents from `/specs/002-constitution-compliance/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included - compliance verification requires test coverage to ensure violations are detected.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and compliance checking infrastructure

- [X] T001 Create compliance checking module structure in `src/lib/compliance.py`
- [X] T002 [P] Create static analysis module structure in `src/lib/static_analysis.py`
- [X] T003 Create compliance checking service structure in `src/services/compliance_checker.py`
- [X] T004 [P] Create CLI compliance module structure in `src/cli/compliance.py`
- [X] T005 [P] Create unit test structure in `tests/unit/test_compliance.py`
- [X] T006 [P] Create integration test structure in `tests/integration/test_compliance_checks.py`
- [X] T007 [P] Create contract test structure in `tests/contract/test_compliance_cli.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core compliance checking utilities that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create `ConstitutionViolation` exception class in `src/lib/compliance.py`
- [X] T009 [P] Implement static analysis AST parser for detecting external API imports in `src/lib/static_analysis.py`
- [X] T010 [P] Implement static analysis check for external API calls (requests, openai, httpx) in `src/lib/static_analysis.py`
- [X] T011 [P] Implement static analysis check for HTTP URL patterns in `src/lib/static_analysis.py`
- [X] T012 [P] Implement static analysis check for subprocess/exec calls to external binaries in `src/lib/static_analysis.py`
- [X] T013 Create `ComplianceStatus` data class in `src/lib/compliance.py`
- [X] T014 Implement base compliance checking utilities in `src/lib/compliance.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Ensure Local-Only Processing (Priority: P1) 🎯 MVP

**Goal**: Ensure that entity data model implementation complies with constitution requirements for local-only processing (no external API dependencies for core functionality).

**Independent Test**: Can be fully tested by verifying that entity storage, querying, and relationship navigation operate without external API calls, and that all embeddings and LLM inference use local models only. Delivers immediate value by ensuring constitutional compliance.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T015 [P] [US1] Unit test for static analysis external API detection in `tests/unit/test_compliance.py`
- [X] T016 [P] [US1] Unit test for runtime API call monitoring in `tests/unit/test_compliance.py`
- [X] T017 [P] [US1] Integration test for entity operations no external APIs in `tests/integration/test_compliance_checks.py`
- [X] T018 [P] [US1] Integration test for embedding operations local-only in `tests/integration/test_compliance_checks.py`
- [X] T019 [P] [US1] Integration test for LLM inference local-only in `tests/integration/test_compliance_checks.py`

### Implementation for User Story 1

- [X] T020 [US1] Implement runtime network call monitoring in `src/services/compliance_checker.py`
- [X] T021 [US1] Implement detection of external API calls during entity operations in `src/services/compliance_checker.py`
- [X] T022 [US1] Implement detection of external API calls during embedding generation in `src/services/compliance_checker.py`
- [X] T023 [US1] Implement detection of external API calls during LLM inference in `src/services/compliance_checker.py`
- [X] T024 [US1] Add compliance checks to entity storage operations in `src/services/entity_storage.py`
- [X] T025 [US1] Add compliance checks to embedding operations in `src/services/embedding.py`
- [X] T026 [US1] Add compliance checks to LLM inference operations in `src/services/rag_generator.py`
- [X] T027 [US1] Implement fail-fast error handling with clear violation messages in `src/lib/compliance.py`
- [X] T028 [US1] Add logging for compliance violations in `src/lib/compliance.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently - entity operations, embedding generation, and LLM inference are verified to be local-only.

---

## Phase 4: User Story 2 - Enforce Python-Only Execution (Priority: P1)

**Goal**: Verify that all entity data model operations use only Python standard library and Python packages (no external binaries or system dependencies beyond Python runtime).

**Independent Test**: Can be fully tested by checking that all entity operations use only Python code paths, JSON file storage (standard library), and Python-native dependencies. Delivers value by ensuring cross-platform compatibility and reducing deployment complexity.

### Tests for User Story 2

- [X] T029 [P] [US2] Unit test for Python-only import detection in `tests/unit/test_compliance.py`
- [X] T030 [P] [US2] Unit test for subprocess call detection in `tests/unit/test_compliance.py`
- [X] T031 [P] [US2] Integration test for entity operations Python-only in `tests/integration/test_compliance_checks.py`
- [X] T032 [P] [US2] Integration test for no external binary execution in `tests/integration/test_compliance_checks.py`

### Implementation for User Story 2

- [X] T033 [US2] Implement static analysis check for Python standard library imports only in `src/lib/static_analysis.py`
- [X] T034 [US2] Implement detection of subprocess calls to external binaries in `src/lib/static_analysis.py`
- [X] T035 [US2] Implement runtime process spawn monitoring in `src/services/compliance_checker.py`
- [X] T036 [US2] Implement verification that entity operations use only Python standard library (json, pathlib) in `src/services/compliance_checker.py`
- [X] T037 [US2] Add compliance checks to verify no external binaries in entity storage operations in `src/services/entity_storage.py`
- [X] T038 [US2] Implement Python-only dependency verification in `src/lib/compliance.py`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - all operations are verified to be local-only and Python-only.

---

## Phase 5: User Story 3 - Validate FAISS Storage Compliance (Priority: P2)

**Goal**: Ensure that FAISS vector storage remains local and compatible with the entity data model's RAG functionality.

**Independent Test**: Can be fully tested by verifying that FAISS indexes can be created from entity-based decision items and that RAG queries work with the new entity structure. Delivers value by preserving RAG functionality while maintaining constitutional compliance.

### Tests for User Story 3

- [X] T039 [P] [US3] Integration test for FAISS index creation local-only in `tests/integration/test_compliance_checks.py`
- [X] T040 [P] [US3] Integration test for FAISS operations no remote storage in `tests/integration/test_compliance_checks.py`
- [X] T041 [P] [US3] Integration test for RAG queries with entity-based FAISS index in `tests/integration/test_compliance_checks.py`

### Implementation for User Story 3

- [X] T042 [US3] Implement detection of remote vector database connections in `src/services/compliance_checker.py`
- [X] T043 [US3] Implement verification that FAISS indexes are stored locally only in `src/services/compliance_checker.py`
- [X] T044 [US3] Add compliance checks to FAISS index operations in `src/services/index_builder.py`
- [X] T045 [US3] Add compliance checks to FAISS retrieval operations in `src/services/retrieval.py`
- [X] T046 [US3] Verify entity-based decision items work with local FAISS indexing in `src/services/index_builder.py`
- [X] T047 [US3] Verify RAG queries work with entity-based FAISS indexes in `src/services/query_service.py`

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently - FAISS operations are verified to be local-only and compatible with entity model.

---

## Phase 6: User Story 4 - Verify CLI Support Compliance (Priority: P2)

**Goal**: Access all entity data model operations via CLI commands as required by the constitution.

**Independent Test**: Can be fully tested by executing all entity operations (query workgroup, query person, query meeting, etc.) via CLI commands and verifying they work without external dependencies. Delivers value by ensuring accessible command-line interface for all functionality.

### Tests for User Story 4

- [X] T048 [P] [US4] Contract test for `archive-rag check-compliance` CLI command in `tests/contract/test_compliance_cli.py`
- [X] T049 [P] [US4] Contract test for CLI command compliance verification in `tests/contract/test_compliance_cli.py`
- [X] T050 [P] [US4] Integration test for CLI commands no external dependencies in `tests/integration/test_compliance_checks.py`

### Implementation for User Story 4

- [X] T051 [US4] Implement `archive-rag check-compliance` CLI command in `src/cli/compliance.py`
- [X] T052 [US4] Implement compliance report generation (JSON, text, markdown formats) in `src/cli/compliance.py`
- [X] T053 [US4] Implement compliance status summary in `src/cli/compliance.py`
- [X] T054 [US4] Verify all entity CLI commands work without external dependencies in `src/cli/query.py`
- [X] T055 [US4] Add compliance verification to CLI command execution in `src/cli/compliance.py`
- [X] T056 [US4] Integrate compliance CLI command with main CLI in `src/cli/main.py`

**Checkpoint**: At this point, all user stories should be independently functional - CLI commands are verified to work without external dependencies.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T057 [P] Add comprehensive documentation for compliance checking in `README.md`
- [X] T058 [P] Update documentation with compliance usage examples in `docs/`
- [X] T059 [P] Add compliance checking to CI/CD pipeline (GitHub Actions workflow)
- [X] T060 [P] Create pre-commit hook for compliance checks in `.git/hooks/pre-commit`
- [X] T061 Implement compliance audit report generation with historical tracking in `src/lib/compliance.py`
- [X] T062 [P] Add compliance metrics and reporting in `src/services/compliance_checker.py`
- [X] T063 Code cleanup and refactoring across compliance checking modules
- [X] T064 Run quickstart.md validation to ensure all compliance examples work
- [X] T065 [P] Performance optimization for compliance checks (minimize overhead)
- [X] T066 Add error handling and recovery for compliance check failures in `src/lib/compliance.py`
- [X] T067 [P] Add logging for all compliance operations with audit trail support in `src/lib/compliance.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Needs compliance checking utilities
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Needs compliance checking utilities, can work in parallel with US1
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Needs compliance checking utilities, benefits from US1 completion for entity operations verification
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Needs compliance checking utilities, benefits from all previous stories for comprehensive CLI verification

### Within Each User Story

- Tests (T015-T019, T029-T032, T039-T041, T048-T050) MUST be written and FAIL before implementation
- Static analysis utilities before runtime checks
- Compliance detection before violation handling
- Core compliance checking before integration with existing services
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T004-T007)
- All Foundational tasks marked [P] can run in parallel (T009-T012)
- Once Foundational phase completes, User Stories 1 and 2 (both P1) can start in parallel
- All tests for a user story marked [P] can run in parallel
- Compliance utilities can be developed in parallel with integration tasks
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for static analysis external API detection in tests/unit/test_compliance.py"
Task: "Unit test for runtime API call monitoring in tests/unit/test_compliance.py"
Task: "Integration test for entity operations no external APIs in tests/integration/test_compliance_checks.py"
Task: "Integration test for embedding operations local-only in tests/integration/test_compliance_checks.py"
Task: "Integration test for LLM inference local-only in tests/integration/test_compliance_checks.py"

# Launch compliance detection implementations together:
Task: "Implement runtime network call monitoring in src/services/compliance_checker.py"
Task: "Implement detection of external API calls during entity operations in src/services/compliance_checker.py"
Task: "Implement detection of external API calls during embedding generation in src/services/compliance_checker.py"
Task: "Implement detection of external API calls during LLM inference in src/services/compliance_checker.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Unit test for Python-only import detection in tests/unit/test_compliance.py"
Task: "Unit test for subprocess call detection in tests/unit/test_compliance.py"
Task: "Integration test for entity operations Python-only in tests/integration/test_compliance_checks.py"
Task: "Integration test for no external binary execution in tests/integration/test_compliance_checks.py"

# Launch Python-only verification implementations together:
Task: "Implement static analysis check for Python standard library imports only in src/lib/static_analysis.py"
Task: "Implement detection of subprocess calls to external binaries in src/lib/static_analysis.py"
Task: "Implement runtime process spawn monitoring in src/services/compliance_checker.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Ensure Local-Only Processing)
4. **STOP and VALIDATE**: Test User Story 1 independently - verify entity operations, embedding generation, and LLM inference are local-only
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP - local-only verified!)
3. Add User Story 2 → Test independently → Deploy/Demo (Python-only verified!)
4. Add User Story 3 → Test independently → Deploy/Demo (FAISS compliance verified!)
5. Add User Story 4 → Test independently → Deploy/Demo (CLI compliance verified!)
6. Add Polish phase → Complete feature
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (local-only processing)
   - Developer B: User Story 2 (Python-only execution)
   - Developer C: User Story 3 (FAISS storage compliance)
3. Once US1 and US2 complete:
   - Developer A: User Story 4 (CLI support compliance)
   - Developer B: Polish phase (documentation, CI/CD)
   - Developer C: Polish phase (metrics, optimization)
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
- Compliance checks should not significantly impact performance - monitor overhead
- All compliance violations must be logged to audit trail

---

## Task Summary

**Total Tasks**: 67

**Task Count by Phase**:
- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundational): 7 tasks
- Phase 3 (User Story 1): 14 tasks (5 tests + 9 implementation)
- Phase 4 (User Story 2): 10 tasks (4 tests + 6 implementation)
- Phase 5 (User Story 3): 9 tasks (3 tests + 6 implementation)
- Phase 6 (User Story 4): 9 tasks (3 tests + 6 implementation)
- Phase 7 (Polish): 11 tasks

**Task Count by User Story**:
- User Story 1: 14 tasks
- User Story 2: 10 tasks
- User Story 3: 9 tasks
- User Story 4: 9 tasks

**Parallel Opportunities**: 25 tasks marked [P] can run in parallel

**Suggested MVP Scope**: Phases 1-3 (Setup + Foundational + User Story 1) = 28 tasks


# Tasks: Entity-Based Data Model

**Input**: Design documents from `/specs/001-entity-data-model/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are included for validation and verification. Tests MUST be written and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and entity storage directory structure

- [X] T001 [P] Update `.gitignore` to exclude `entities/` directory in `.gitignore`
- [X] T002 Create entity storage directory structure initialization utility in `src/lib/config.py`
- [X] T003 [P] Update `src/lib/config.py` to add entity storage paths configuration (entities_dir, index_dir, relations_dir)
- [X] T004 Create base entity model pattern in `src/models/base.py` with UUID, created_at, updated_at fields

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core entity storage and query infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create `src/services/entity_storage.py` with directory structure initialization
- [X] T006 [P] Implement `init_entity_storage()` function in `src/services/entity_storage.py` to create `entities/workgroups/`, `entities/meetings/`, `entities/people/`, `entities/documents/`, `entities/agenda_items/`, `entities/action_items/`, `entities/decision_items/`, `entities/tags/`, `entities/_index/`, `entities/_relations/` directories
- [X] T007 [P] Implement `save_entity()` function in `src/services/entity_storage.py` for atomic JSON file writes using temporary files + rename pattern
- [X] T008 [P] Implement `load_entity()` function in `src/services/entity_storage.py` for reading entity JSON files
- [X] T009 [P] Implement `delete_entity()` function in `src/services/entity_storage.py` with backup/restore pattern for atomic deletions
- [X] T010 [P] Implement `save_index()` function in `src/services/entity_storage.py` for updating index JSON files (`_index/meetings_by_workgroup.json`, `_index/meeting_person_by_meeting.json`, `_index/meeting_person_by_person.json`)
- [X] T011 [P] Implement `load_index()` function in `src/services/entity_storage.py` for reading index JSON files
- [X] T012 Create `src/services/entity_query.py` with query service class
- [X] T013 [P] Implement base query methods in `src/services/entity_query.py` (get_by_id, find_by_name, etc.)
- [X] T014 Update `src/lib/validation.py` to add entity validation rules (foreign key validation, required field validation)

**Checkpoint**: Foundation ready - entity storage and query infrastructure complete. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Query Meetings by Workgroup (Priority: P1) 🎯 MVP

**Goal**: Enable users to query all meetings for a specific workgroup, delivering workgroup-level analysis capability.

**Independent Test**: Create a workgroup with multiple meetings, then query all meetings for that workgroup. Verify exact count matches and all meetings belong to the specified workgroup.

### Tests for User Story 1

- [X] T015 [P] [US1] Unit test for Workgroup model validation in `tests/unit/test_entity_models.py`
- [X] T016 [P] [US1] Unit test for Meeting model validation in `tests/unit/test_entity_models.py`
- [X] T017 [P] [US1] Integration test for query meetings by workgroup in `tests/integration/test_entity_relationships.py`
- [X] T018 [P] [US1] Contract test for `archive-rag query-workgroup` command in `tests/contract/test_query_command.py`

### Implementation for User Story 1

- [X] T019 [P] [US1] Create Workgroup model in `src/models/workgroup.py` with id (UUID), name (String, required), created_at, updated_at fields
- [X] T020 [P] [US1] Create Meeting model in `src/models/meeting.py` with id (UUID), workgroup_id (UUID, FK), type (Enum), date (Date, ISO 8601), host_id (UUID, FK), documenter_id (UUID, FK), purpose (Text), video_link (URL), timestamped_video (JSON), no_summary_given (Boolean), canceled_summary (Boolean), created_at, updated_at fields
- [X] T021 [US1] Implement `save_workgroup()` in `src/services/entity_storage.py` to save workgroup JSON file to `entities/workgroups/{id}.json`
- [X] T022 [US1] Implement `save_meeting()` in `src/services/entity_storage.py` to save meeting JSON file to `entities/meetings/{id}.json`
- [X] T023 [US1] Implement `get_meetings_by_workgroup()` in `src/services/entity_query.py` using index file `_index/meetings_by_workgroup.json`
- [X] T024 [US1] Implement workgroup index update logic in `src/services/entity_storage.py` to maintain `_index/meetings_by_workgroup.json` when meetings are saved
- [X] T025 [US1] Implement `archive-rag query-workgroup` CLI command in `src/cli/query.py` (new function `query_workgroup_command`)
- [X] T026 [US1] Add validation for workgroup_id foreign key in `src/lib/validation.py` (validate workgroup exists before saving meeting)
- [X] T027 [US1] Add logging for query-workgroup operations in `src/services/entity_query.py`

**Checkpoint**: At this point, User Story 1 should be fully functional. Users can query meetings by workgroup via CLI command, with all meetings correctly associated with their workgroups.

---

## Phase 4: User Story 2 - Track Action Items and Assignees (Priority: P1)

**Goal**: Enable users to query all action items assigned to a specific person across all meetings, delivering personal task tracking capability.

**Independent Test**: Create meetings with action items assigned to different people, then query all action items for a specific person. Verify only that person's assignments are returned with all fields (assignee, due date, status) correctly populated.

### Tests for User Story 2

- [X] T028 [P] [US2] Unit test for Person model validation in `tests/unit/test_entity_models.py`
- [X] T029 [P] [US2] Unit test for ActionItem model validation in `tests/unit/test_entity_models.py`
- [X] T030 [P] [US2] Unit test for AgendaItem model validation in `tests/unit/test_entity_models.py`
- [X] T031 [P] [US2] Integration test for query action items by person in `tests/integration/test_entity_relationships.py`
- [X] T032 [P] [US2] Contract test for `archive-rag query-person --action-items` command in `tests/contract/test_query_command.py`

### Implementation for User Story 2

- [X] T033 [P] [US2] Create Person model in `src/models/person.py` with id (UUID), display_name (String, required), alias (String), role (String), created_at, updated_at fields
- [X] T034 [P] [US2] Create AgendaItem model in `src/models/agenda_item.py` with id (UUID), meeting_id (UUID, FK), status (Enum), narrative (Text), created_at fields
- [X] T035 [P] [US2] Create ActionItem model in `src/models/action_item.py` with id (UUID), agenda_item_id (UUID, FK), text (String, required), assignee_id (UUID, FK), due_date (Date), status (Enum), created_at, updated_at fields
- [X] T036 [US2] Implement `save_person()` in `src/services/entity_storage.py` to save person JSON file to `entities/people/{id}.json`
- [X] T037 [US2] Implement `save_agenda_item()` in `src/services/entity_storage.py` to save agenda item JSON file to `entities/agenda_items/{id}.json`
- [X] T038 [US2] Implement `save_action_item()` in `src/services/entity_storage.py` to save action item JSON file to `entities/action_items/{id}.json`
- [X] T039 [US2] Implement `get_action_items_by_person()` in `src/services/entity_query.py` to query action items by assignee_id (scan `entities/action_items/` directory with filtering)
- [X] T040 [US2] Implement `archive-rag query-person --action-items` CLI command in `src/cli/query.py` (new function `query_person_command`)
- [X] T041 [US2] Add validation for assignee_id foreign key in `src/lib/validation.py` (validate person exists before saving action item)
- [X] T042 [US2] Add validation for agenda_item_id foreign key in `src/lib/validation.py` (validate agenda item exists before saving action item)
- [X] T043 [US2] Add logging for query-person action items operations in `src/services/entity_query.py`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Users can query meetings by workgroup and action items by person.

---

## Phase 5: User Story 3 - Link Documents to Meetings (Priority: P2)

**Goal**: Enable users to access working documents referenced during meetings, delivering quick access to meeting-related resources.

**Independent Test**: Create a meeting with linked documents, then retrieve all documents for that meeting. Verify all documents with titles and links are returned, and document metadata includes meeting context.

### Tests for User Story 3

- [X] T044 [P] [US3] Unit test for Document model validation in `tests/unit/test_entity_models.py`
- [X] T045 [P] [US3] Integration test for query documents for meeting in `tests/integration/test_entity_relationships.py`
- [X] T046 [P] [US3] Contract test for `archive-rag query-meeting --documents` command in `tests/contract/test_query_command.py`

### Implementation for User Story 3

- [X] T047 [P] [US3] Create Document model in `src/models/document.py` with id (UUID), meeting_id (UUID, FK), title (String, required), link (URL, required), created_at fields
- [X] T048 [US3] Implement `save_document()` in `src/services/entity_storage.py` to save document JSON file to `entities/documents/{id}.json`
- [X] T049 [US3] Implement `get_documents_by_meeting()` in `src/services/entity_query.py` to query documents by meeting_id (scan `entities/documents/` directory with filtering)
- [X] T050 [US3] Implement `archive-rag query-meeting --documents` CLI command in `src/cli/query.py` (extend `query_meeting_command` function)
- [X] T051 [US3] Add validation for meeting_id foreign key in `src/lib/validation.py` (validate meeting exists before saving document)
- [X] T052 [US3] Implement document link validation on access (not during ingestion) in `src/services/entity_query.py` (detect broken links but don't block retrieval)
- [X] T053 [US3] Add logging for query-meeting documents operations in `src/services/entity_query.py`

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently. Users can query meetings by workgroup, action items by person, and documents for meetings.

---

## Phase 6: User Story 4 - Navigate Decisions and Their Context (Priority: P2)

**Goal**: Enable users to see decisions made in meetings along with their rationales and effects, delivering transparent decision-making records.

**Independent Test**: Create agenda items with decision items containing rationales and effects, then query decisions with their full context. Verify all decisions with their rationales and effects are returned, and queries filtered by effect scope work correctly.

### Tests for User Story 4

- [ ] T054 [P] [US4] Unit test for DecisionItem model validation in `tests/unit/test_entity_models.py`
- [ ] T055 [P] [US4] Integration test for query decisions by agenda item in `tests/integration/test_entity_relationships.py`
- [ ] T056 [P] [US4] Integration test for query decisions by effect scope in `tests/integration/test_entity_relationships.py`

### Implementation for User Story 4

- [ ] T057 [P] [US4] Create DecisionItem model in `src/models/decision_item.py` with id (UUID), agenda_item_id (UUID, FK), decision (String, required), rationale (Text), effect (Enum), created_at fields
- [ ] T058 [US4] Implement `save_decision_item()` in `src/services/entity_storage.py` to save decision item JSON file to `entities/decision_items/{id}.json`
- [ ] T059 [US4] Implement `get_decision_items_by_agenda_item()` in `src/services/entity_query.py` to query decision items by agenda_item_id (scan `entities/decision_items/` directory with filtering)
- [ ] T060 [US4] Implement `get_decision_items_by_effect()` in `src/services/entity_query.py` to filter decisions by effect scope (e.g., "mayAffectOtherPeople")
- [ ] T061 [US4] Extend `archive-rag query-meeting` CLI command to show decision items in `src/cli/query.py` (add `--decisions` option)
- [ ] T062 [US4] Add validation for agenda_item_id foreign key in `src/lib/validation.py` (validate agenda item exists before saving decision item)
- [ ] T063 [US4] Add logging for decision item query operations in `src/services/entity_query.py`

**Checkpoint**: At this point, User Stories 1, 2, 3, AND 4 should all work independently. Users can navigate decisions with their full context including rationales and effects.

---

## Phase 7: User Story 5 - Filter by Tags and Topics (Priority: P3)

**Goal**: Enable users to find meetings by topics covered or emotional tone, delivering topic-based discovery across workgroups.

**Independent Test**: Tag meetings with topics and emotions, then query meetings by tag values. Verify all meetings with matching tags are returned, and untagged meetings are excluded from tag-based queries.

### Tests for User Story 5

- [ ] T064 [P] [US5] Unit test for Tag model validation in `tests/unit/test_entity_models.py`
- [ ] T065 [P] [US5] Integration test for query meetings by tag in `tests/integration/test_entity_relationships.py`

### Implementation for User Story 5

- [ ] T066 [P] [US5] Create Tag model in `src/models/tag.py` with id (UUID), meeting_id (UUID, FK), topics_covered (Text or Array), emotions (Text or Array), created_at fields
- [ ] T067 [US5] Implement `save_tag()` in `src/services/entity_storage.py` to save tag JSON file to `entities/tags/{id}.json`
- [ ] T068 [US5] Implement `get_meetings_by_tag()` in `src/services/entity_query.py` to query meetings by tag values (topics_covered or emotions) - scan `entities/tags/` directory with filtering
- [ ] T069 [US5] Add tag-based query support to `archive-rag query-meeting` CLI command in `src/cli/query.py` (add `--tags` option)
- [ ] T070 [US5] Add validation for meeting_id foreign key in `src/lib/validation.py` (validate meeting exists before saving tag)
- [ ] T071 [US5] Add logging for tag query operations in `src/services/entity_query.py`

**Checkpoint**: At this point, all user stories should work independently. Users can query meetings by workgroup, action items by person, documents for meetings, decisions with context, and meetings by tags.

---

## Phase 8: Many-to-Many Relationship & Cascade Deletes

**Purpose**: Implement Meeting-Person many-to-many relationship and cascade delete behaviors for all entity relationships

- [ ] T072 [P] Create MeetingPerson junction model in `src/models/meeting_person.py` with meeting_id (UUID, FK), person_id (UUID, FK), role (String), created_at fields
- [ ] T073 [P] Implement `save_meeting_person()` in `src/services/entity_storage.py` to save junction record to `entities/_relations/meeting_person.json` (append to array)
- [ ] T074 [P] Implement `load_meeting_person()` in `src/services/entity_storage.py` to read junction records from `entities/_relations/meeting_person.json`
- [ ] T075 [P] Implement `get_meetings_by_person()` in `src/services/entity_query.py` using index file `_index/meeting_person_by_person.json`
- [ ] T076 [P] Implement `get_people_by_meeting()` in `src/services/entity_query.py` using index file `_index/meeting_person_by_meeting.json`
- [ ] T077 [P] Implement meeting-person index update logic in `src/services/entity_storage.py` to maintain both `_index/meeting_person_by_meeting.json` and `_index/meeting_person_by_person.json`
- [ ] T078 Implement cascade delete for Person → ActionItems in `src/services/entity_storage.py` (delete person → delete all associated action items)
- [ ] T079 Implement cascade delete for Workgroup → Meetings (and all related entities) in `src/services/entity_storage.py` (delete workgroup → cascade delete all meetings, documents, agenda items, action items, decision items, tags)
- [ ] T080 Implement cascade delete for Meeting → Documents, AgendaItems, Tags, MeetingPerson records in `src/services/entity_storage.py` (delete meeting → cascade delete all related entities)
- [ ] T081 Implement cascade delete for AgendaItem → ActionItems, DecisionItems in `src/services/entity_storage.py` (delete agenda item → cascade delete all related items)
- [ ] T082 [P] Add validation for Meeting → at least one participant requirement in `src/lib/validation.py` (FR-024: meetings must have at least one MeetingPerson record)
- [ ] T083 [P] Add integration tests for cascade delete behaviors in `tests/integration/test_entity_relationships.py`
- [ ] T084 Extend `archive-rag query-person --meetings` CLI command in `src/cli/query.py` to query meetings attended by person via many-to-many relationship
- [ ] T085 Add validation and error handling for cascade delete operations with backup/restore pattern in `src/services/entity_storage.py`

---

## Phase 9: Migration & URL Ingestion Integration

**Purpose**: Migrate existing flat JSON data to entity model and preserve URL ingestion from GitHub

- [ ] T086 [P] Create `src/services/migration.py` with migration service class
- [ ] T087 [P] Implement `migrate_meeting_record_to_entities()` in `src/services/migration.py` to convert MeetingRecord to entity JSON files (Workgroup, Meeting, Person, Document, AgendaItem, ActionItem, DecisionItem, Tag)
- [ ] T088 [P] Implement `migrate_from_url()` in `src/services/migration.py` to fetch JSON array from GitHub URL and migrate each meeting
- [ ] T089 [P] Implement `migrate_from_directory()` in `src/services/migration.py` to migrate all JSON files in a directory
- [ ] T090 [P] Update `src/services/ingestion.py` to preserve URL ingestion and add entity conversion after MeetingRecord parsing (call `migrate_meeting_record_to_entities()` after creating MeetingRecord)
- [ ] T091 [P] Update `src/services/chunking.py` to extract transcript from DecisionItem entities for RAG embedding (read from entity JSON files instead of MeetingRecord.transcript)
- [ ] T092 [P] Update `src/services/retrieval.py` to support entity-based queries alongside vector similarity search
- [ ] T093 [P] Implement `archive-rag init-entities` CLI command in `src/cli/main.py` (new function `init_entities_command`)
- [ ] T094 [P] Implement `archive-rag migrate-entities` CLI command in `src/cli/migrate.py` (new file with `migrate_entities_command`)
- [ ] T095 [P] Update `archive-rag index` command in `src/cli/index.py` to support `--use-entities` flag for entity-based storage
- [ ] T096 [P] Update `archive-rag query` command in `src/cli/query.py` to support `--use-entity-context` flag for entity-based queries
- [ ] T097 [P] Add integration test for URL ingestion with entity conversion in `tests/integration/test_entity_migration.py`
- [ ] T098 [P] Add validation test for migration completeness (100% data preservation SC-010) in `tests/integration/test_entity_migration.py`

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T099 [P] Update `src/lib/config.py` to add entity storage configuration options (entities_dir path, index update intervals, etc.)
- [ ] T100 [P] Implement `archive-rag validate-entities` CLI command in `src/cli/validate.py` (new file) to check referential integrity
- [ ] T101 [P] Implement `archive-rag test-cascade-delete` CLI command in `src/cli/validate.py` to test cascade delete behaviors
- [ ] T102 [P] Add performance benchmarks for entity queries (SC-001, SC-002, SC-003, SC-007) in `tests/integration/test_entity_performance.py`
- [ ] T103 [P] Update documentation in `README.md` to include entity-based data model usage
- [ ] T104 [P] Update `MODIFYING_DATA_FORMAT.md` to reflect entity-based structure
- [ ] T105 [P] Add logging for all entity operations (create, read, update, delete) with audit trail support
- [ ] T106 [P] Code cleanup and refactoring across entity services
- [ ] T107 [P] Run quickstart.md validation to ensure all examples work with entity model
- [ ] T108 [P] Add error handling and recovery for corrupted entity JSON files in `src/services/entity_storage.py`
- [ ] T109 [P] Implement entity validation utility functions in `src/lib/validation.py` (check foreign key references, validate required fields)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Many-to-Many & Cascade (Phase 8)**: Depends on User Stories 1-2 completion (needs Person, Meeting, ActionItem entities)
- **Migration & URL Ingestion (Phase 9)**: Depends on all entity models being complete (Phases 3-7)
- **Polish (Phase 10)**: Depends on all desired user stories and migration being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Needs Workgroup and Meeting entities
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Needs Person, AgendaItem, ActionItem entities
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Needs Document entity (depends on Meeting from US1)
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Needs DecisionItem entity (depends on AgendaItem from US2)
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Needs Tag entity (depends on Meeting from US1)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before CLI commands
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, User Stories 1 and 2 can start in parallel (both P1)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- User Stories 3 and 4 can run in parallel after US1 and US2 are complete (both P2)
- User Story 5 can run after US1 is complete (P3)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for Workgroup model validation in tests/unit/test_entity_models.py"
Task: "Unit test for Meeting model validation in tests/unit/test_entity_models.py"
Task: "Integration test for query meetings by workgroup in tests/integration/test_entity_relationships.py"
Task: "Contract test for archive-rag query-workgroup command in tests/contract/test_query_command.py"

# Launch all models for User Story 1 together:
Task: "Create Workgroup model in src/models/workgroup.py"
Task: "Create Meeting model in src/models/meeting.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Unit test for Person model validation in tests/unit/test_entity_models.py"
Task: "Unit test for ActionItem model validation in tests/unit/test_entity_models.py"
Task: "Unit test for AgendaItem model validation in tests/unit/test_entity_models.py"
Task: "Integration test for query action items by person in tests/integration/test_entity_relationships.py"
Task: "Contract test for archive-rag query-person --action-items command in tests/contract/test_query_command.py"

# Launch all models for User Story 2 together:
Task: "Create Person model in src/models/person.py"
Task: "Create AgendaItem model in src/models/agenda_item.py"
Task: "Create ActionItem model in src/models/action_item.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Query Meetings by Workgroup)
4. **STOP and VALIDATE**: Test User Story 1 independently - users can query meetings by workgroup
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (Action item tracking)
4. Add User Story 3 → Test independently → Deploy/Demo (Document linking)
5. Add User Story 4 → Test independently → Deploy/Demo (Decision context)
6. Add User Story 5 → Test independently → Deploy/Demo (Tag filtering)
7. Add Many-to-Many & Cascade → Test independently → Deploy/Demo (Full relationships)
8. Add Migration & URL Ingestion → Test independently → Deploy/Demo (Full system)
9. Polish → Final validation → Production ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Query Meetings by Workgroup)
   - Developer B: User Story 2 (Track Action Items)
3. Once US1 and US2 complete:
   - Developer A: User Story 3 (Link Documents)
   - Developer B: User Story 4 (Navigate Decisions)
   - Developer C: User Story 5 (Filter by Tags)
4. Team works together on Many-to-Many & Cascade
5. Team works together on Migration & URL Ingestion
6. Team polishes together

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- URL ingestion from GitHub source must be preserved throughout migration
- Entity JSON files must maintain human-readable format for debugging
- Index files must be updated atomically with entity saves
- Cascade deletes must use backup/restore pattern for atomicity
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Summary

- **Total Tasks**: 109 tasks
- **Setup Phase**: 4 tasks
- **Foundational Phase**: 11 tasks
- **User Story 1 (P1)**: 13 tasks (13 tests + implementation)
- **User Story 2 (P1)**: 11 tasks (5 tests + implementation)
- **User Story 3 (P2)**: 10 tasks (3 tests + implementation)
- **User Story 4 (P2)**: 10 tasks (3 tests + implementation)
- **User Story 5 (P3)**: 8 tasks (2 tests + implementation)
- **Many-to-Many & Cascade**: 14 tasks
- **Migration & URL Ingestion**: 13 tasks
- **Polish**: 11 tasks

**Suggested MVP Scope**: Phases 1-3 (Setup, Foundational, User Story 1) - Query Meetings by Workgroup

**Parallel Opportunities**: 
- 70+ tasks marked with [P] can run in parallel
- User Stories 1 and 2 can be worked on in parallel after Foundational
- User Stories 3 and 4 can be worked on in parallel after US1 and US2
- All test tasks within a story can run in parallel
- All model creation tasks within a story can run in parallel


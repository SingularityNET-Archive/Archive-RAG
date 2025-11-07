# Tasks: Enhance Discord Bot with Entity Extraction and Issue Reporting

**Input**: Design documents from `/specs/005-enhance-discord-bot/`
**Prerequisites**: plan.md, spec.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2], [US3])
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create IssueReport model in `src/bot/models/issue_report.py`
- [x] T002 [P] Create enhanced citation formatter service in `src/bot/services/enhanced_citation_formatter.py`
- [x] T003 [P] Create issue reporting service in `src/bot/services/issue_reporting_service.py`
- [x] T004 [P] Create relationship query service in `src/bot/services/relationship_query_service.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Integrate EntityNormalizationService into bot services in `src/bot/services/__init__.py`
- [x] T006 Integrate RelationshipTripleGenerator into bot services in `src/bot/services/__init__.py`
- [x] T007 Integrate SemanticChunkingService metadata access into bot services in `src/bot/services/__init__.py`
- [x] T008 Create enhanced citation data model in `src/bot/models/enhanced_citation.py`
- [x] T009 Setup issue report storage mechanism (local JSON files) in `src/bot/services/issue_storage.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Enhanced Citations with Entity Context (Priority: P1) 🎯 MVP

**Goal**: Enhance citations in bot responses to include normalized entity names, relationship triples, and semantic chunk metadata

**Independent Test**: Run `/archive query query:"What decisions did Stephen make?"` and verify citations include normalized entity names, relationship context, and chunk type

### Implementation for User Story 1

- [x] T010 [US1] Enhance MessageFormatter.format_citation() to include normalized entity names in `src/bot/services/message_formatter.py`
- [x] T011 [US1] Add relationship triple display to citations in `src/bot/services/message_formatter.py`
- [x] T012 [US1] Add semantic chunk type display to citations in `src/bot/services/message_formatter.py`
- [x] T013 [US1] Integrate EntityNormalizationService into citation formatting in `src/bot/services/enhanced_citation_formatter.py`
- [x] T014 [US1] Load relationship triples for citations from RelationshipTripleGenerator in `src/bot/services/enhanced_citation_formatter.py`
- [x] T015 [US1] Load semantic chunk metadata for citations from chunk metadata in `src/bot/services/enhanced_citation_formatter.py`
- [x] T016 [US1] Ensure citations always show current canonical entity names (even if chunk predates normalization) in `src/bot/services/enhanced_citation_formatter.py`
- [x] T017 [US1] Update QueryCommand to use enhanced citation formatter in `src/bot/commands/query.py`
- [x] T018 [US1] Update TopicsCommand to use enhanced citation formatter in `src/bot/commands/topics.py`
- [x] T019 [US1] Update PeopleCommand to use enhanced citation formatter in `src/bot/commands/people.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Entity Relationship Queries (Priority: P1)

**Goal**: Add `/archive relationships` command to query entity relationships directly

**Independent Test**: Run `/archive relationships person:"Stephen"` and verify it shows all relationships for that person (e.g., "Stephen → attended → Meeting", "Stephen → assigned_to → ActionItem")

### Implementation for User Story 2

- [x] T020 [US2] Create RelationshipsCommand class in `src/bot/commands/relationships.py`
- [x] T021 [US2] Implement relationship query handler for workgroup entities in `src/bot/commands/relationships.py`
- [x] T022 [US2] Implement relationship query handler for person entities in `src/bot/commands/relationships.py`
- [x] T023 [US2] Implement relationship query handler for meeting entities in `src/bot/commands/relationships.py`
- [x] T024 [US2] Implement relationship query handler for decision entities in `src/bot/commands/relationships.py`
- [x] T025 [US2] Implement relationship query handler for action item entities in `src/bot/commands/relationships.py`
- [x] T026 [US2] Integrate EntityNormalizationService for normalizing entity names in queries in `src/bot/commands/relationships.py`
- [x] T027 [US2] Integrate RelationshipTripleGenerator to fetch relationship triples in `src/bot/services/relationship_query_service.py`
- [x] T028 [US2] Format relationship triples as "Subject → Relationship → Object" in `src/bot/commands/relationships.py`
- [x] T029 [US2] Handle normalization failures with exact match results and suggestions in `src/bot/commands/relationships.py`
- [x] T030 [US2] Handle non-existent entity queries with helpful error messages and suggestions in `src/bot/commands/relationships.py`
- [x] T031 [US2] Register `/archive relationships` command in bot setup hook in `src/bot/bot.py`
- [x] T032 [US2] Update PermissionChecker to allow public access to relationships command in `src/bot/services/permission_checker.py`

**Checkpoint**: At this point, User Story 2 should be fully functional and testable independently

---

## Phase 5: User Story 3 - Issue Reporting for Incorrect Information (Priority: P1)

**Goal**: Add issue reporting functionality via Discord button component on bot responses

**Independent Test**: Click "Report Issue" button on bot response, submit issue details, verify issue is logged and confirmation is received

### Implementation for User Story 3

- [x] T033 [US3] Create IssueReport Pydantic model in `src/bot/models/issue_report.py`
- [x] T034 [US3] Implement issue report storage service using local JSON files in `src/bot/services/issue_storage.py`
- [x] T035 [US3] Create issue reporting modal form for Discord interaction in `src/bot/services/issue_reporting_service.py`
- [x] T036 [US3] Implement issue report context capture (query, response, citations, timestamp, user ID, message ID) in `src/bot/services/issue_reporting_service.py`
- [x] T037 [US3] Add "Report Issue" button component to all bot responses in `src/bot/services/message_formatter.py`
- [x] T038 [US3] Handle button click interaction and open modal form in `src/bot/services/issue_reporting_service.py`
- [x] T039 [US3] Implement issue submission handler in `src/bot/services/issue_reporting_service.py`
- [x] T040 [US3] Send confirmation message to user after issue submission in `src/bot/services/issue_reporting_service.py`
- [x] T041 [US3] Implement automated spam detection (duplicate reports, rapid-fire submissions) in `src/bot/services/issue_reporting_service.py`
- [x] T042 [US3] Flag suspicious reports for admin review while logging all reports in `src/bot/services/issue_storage.py`
- [x] T043 [US3] Implement issue report aggregation by query/response pattern in `src/bot/services/issue_reporting_service.py`
- [x] T044 [US3] Update QueryCommand to include report issue button in responses in `src/bot/commands/query.py`
- [x] T045 [US3] Update TopicsCommand to include report issue button in responses in `src/bot/commands/topics.py`
- [x] T046 [US3] Update PeopleCommand to include report issue button in responses in `src/bot/commands/people.py`
- [x] T047 [US3] Update RelationshipsCommand to include report issue button in responses in `src/bot/commands/relationships.py`

**Checkpoint**: At this point, User Story 3 should be fully functional and testable independently

---

## Phase 6: User Story 4 - Entity Search Commands with Normalization (Priority: P2)

**Goal**: Enhance `/archive people` command to use entity normalization for searching with name variations

**Independent Test**: Run `/archive people person:"Stephen [QADAO]"` and verify it normalizes to "Stephen" and shows all mentions regardless of name variation

### Implementation for User Story 4

- [ ] T048 [US4] Integrate EntityNormalizationService into PeopleCommand in `src/bot/commands/people.py`
- [ ] T049 [US4] Normalize entity names in people search queries in `src/bot/commands/people.py`
- [ ] T050 [US4] Show all name variations that normalized to canonical name in search results in `src/bot/commands/people.py`
- [ ] T051 [US4] Handle normalization failures with exact match results and suggestions in `src/bot/commands/people.py`
- [ ] T052 [US4] Update PeopleCommand response format to show normalized entity and variations in `src/bot/commands/people.py`
- [ ] T053 [US4] Update TopicsCommand to use entity normalization (if applicable) in `src/bot/commands/topics.py`

**Checkpoint**: At this point, User Story 4 should be fully functional and testable independently

---

## Phase 7: User Story 5 - Semantic Chunk Context in Responses (Priority: P2)

**Goal**: Display semantic chunk type and entity metadata in citations

**Independent Test**: Run `/archive query` and verify citations indicate semantic chunk type (e.g., "decision_record", "action_item") and show entities mentioned in chunk

### Implementation for User Story 5

- [ ] T054 [US5] Load semantic chunk metadata from chunk storage in `src/bot/services/enhanced_citation_formatter.py`
- [ ] T055 [US5] Display semantic chunk type in citation format (meeting_summary, decision_record, action_item, attendance, resource) in `src/bot/services/enhanced_citation_formatter.py`
- [ ] T056 [US5] Display entity metadata from chunks in citations (which entities are mentioned) in `src/bot/services/enhanced_citation_formatter.py`
- [ ] T057 [US5] Display relationship context from chunk metadata in citations (e.g., assignee, related meeting) in `src/bot/services/enhanced_citation_formatter.py`
- [ ] T058 [US5] Ensure chunk metadata is loaded efficiently for citation display in `src/bot/services/enhanced_citation_formatter.py`

**Checkpoint**: At this point, User Story 5 should be fully functional and testable independently

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T059 [P] Add error handling for missing entity data in citation formatting in `src/bot/services/enhanced_citation_formatter.py`
- [ ] T060 [P] Add error handling for missing relationship triples in `src/bot/services/relationship_query_service.py`
- [ ] T061 [P] Add error handling for missing chunk metadata in `src/bot/services/enhanced_citation_formatter.py`
- [ ] T062 [P] Add logging for all issue reporting operations in `src/bot/services/issue_reporting_service.py`
- [ ] T063 [P] Add logging for relationship query operations in `src/bot/commands/relationships.py`
- [ ] T064 [P] Add logging for enhanced citation formatting in `src/bot/services/enhanced_citation_formatter.py`
- [ ] T065 Update bot documentation with new commands and features in `docs/discord-bot-quick-reference.md`
- [ ] T066 Update bot documentation with issue reporting instructions in `docs/discord-bot-testing.md`
- [ ] T067 Add admin access methods for reviewing issue reports (CLI or admin command) in `src/cli/admin_commands.py` or `src/bot/commands/admin.py`
- [ ] T068 Validate all citations meet Discord message length limits (2000 characters) in `src/bot/utils/message_splitter.py`
- [ ] T069 [P] Add unit tests for enhanced citation formatter in `tests/unit/bot/test_enhanced_citation_formatter.py`
- [ ] T070 [P] Add unit tests for relationship query service in `tests/unit/bot/test_relationship_query_service.py`
- [ ] T071 [P] Add unit tests for issue reporting service in `tests/unit/bot/test_issue_reporting_service.py`
- [ ] T072 Add integration tests for enhanced citations in query responses in `tests/integration/bot/test_enhanced_citations.py`
- [ ] T073 Add integration tests for relationship queries in `tests/integration/bot/test_relationship_queries.py`
- [ ] T074 Add integration tests for issue reporting flow in `tests/integration/bot/test_issue_reporting.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories, can run parallel with US1
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories, can run parallel with US1/US2
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Enhances existing PeopleCommand, can run parallel with other stories
- **User Story 5 (P2)**: Can start after Foundational (Phase 2) - Enhances citations, can run parallel with other stories

### Within Each User Story

- Models before services
- Services before commands
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all foundational model/service tasks together:
Task: "Create IssueReport model in src/bot/models/issue_report.py"
Task: "Create enhanced citation formatter service in src/bot/services/enhanced_citation_formatter.py"
Task: "Create issue reporting service in src/bot/services/issue_reporting_service.py"
Task: "Create relationship query service in src/bot/services/relationship_query_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Enhanced Citations)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Add User Story 5 → Test independently → Deploy/Demo
7. Polish phase → Final improvements
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Enhanced Citations)
   - Developer B: User Story 2 (Relationship Queries)
   - Developer C: User Story 3 (Issue Reporting)
3. Next iteration:
   - Developer A: User Story 4 (Entity Search Normalization)
   - Developer B: User Story 5 (Semantic Chunk Context)
   - Developer C: Polish tasks
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- All entity extraction services (EntityNormalizationService, RelationshipTripleGenerator, SemanticChunkingService) are already implemented and available
- Issue reports will be stored in local JSON files (following Archive-RAG constitution)
- Discord button components require discord.py 2.0+ for modals
- Citations must always show current canonical entity names, even if chunk predates normalization
- All error handling must be graceful with helpful messages to users


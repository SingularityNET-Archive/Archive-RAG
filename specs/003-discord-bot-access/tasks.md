# Tasks: Discord Bot Interface for Archive-RAG

**Input**: Design documents from `/specs/003-discord-bot-access/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in the feature specification. Test tasks are included for completeness but can be deferred if TDD approach is not required.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths assume single project structure as per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create Discord bot module structure `src/bot/` with `__init__.py`
- [x] T002 [P] Create bot commands directory `src/bot/commands/` with `__init__.py`
- [x] T003 [P] Create bot services directory `src/bot/services/` with `__init__.py`
- [x] T004 [P] Create bot utils directory `src/bot/utils/` with `__init__.py`
- [x] T005 [P] Create bot tests directory `tests/bot/` with `__init__.py`
- [x] T006 Add discord.py>=2.3.0 dependency to requirements.txt
- [x] T007 [P] Add pytest-asyncio>=0.21.0 dependency to requirements.txt for async bot tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Create bot configuration loader in `src/bot/config.py` (load DISCORD_BOT_TOKEN from environment)
- [x] T009 [P] Create DiscordUser model in `src/bot/models/discord_user.py` (user_id, username, roles)
- [x] T010 [P] Create RateLimitEntry model in `src/bot/services/rate_limiter.py` (user_id, timestamps deque, limit, window) - Note: Implemented as class within rate_limiter service
- [x] T011 Implement rate limiter service in `src/bot/services/rate_limiter.py` (in-memory token bucket, 10 queries/minute per user)
- [x] T012 [P] Implement permission checker service in `src/bot/services/permission_checker.py` (role-based access control: public, contributor, admin)
- [x] T013 [P] Implement message splitter utility in `src/bot/utils/message_splitter.py` (split messages >2000 chars, answer first, then citations)
- [x] T014 [P] Implement message formatter service in `src/bot/services/message_formatter.py` (format RAGQuery results for Discord, format citations)
- [x] T015 Implement async query service wrapper in `src/bot/services/async_query_service.py` (bridge sync QueryService to async, timeout handling)
- [x] T016 Create bot initialization in `src/bot/bot.py` (Discord client setup, command registration, connection handling)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Ask Questions About Archive Meeting Data (Priority: P1) 🎯 MVP

**Goal**: Discord community members can ask natural-language questions about archived meetings using `/archive query` command

**Independent Test**: Send `/archive query "What decisions were made last January?"` → bot returns answer + citations

### Implementation for User Story 1

- [x] T017 [US1] Create `/archive query` command handler in `src/bot/commands/query.py` (slash command definition, parameter: query text)
- [x] T018 [US1] Implement query command logic in `src/bot/commands/query.py` (send acknowledgment, check rate limit, call async query service)
- [x] T019 [US1] Add response formatting in `src/bot/commands/query.py` (format answer + citations, handle message splitting for long responses)
- [x] T020 [US1] Add error handling in `src/bot/commands/query.py` (RAG pipeline unavailable, rate limit exceeded, no evidence found, generic errors)
- [x] T021 [US1] Add audit logging in `src/bot/commands/query.py` (create ArchiveQueryLog entry with all metadata, use existing AuditWriter)
- [x] T022 [US1] Register `/archive query` command in `src/bot/bot.py` (command tree registration)
- [x] T023 [US1] Create bot CLI entry point in `src/cli/bot.py` (start bot command, load config, run bot)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Users can execute `/archive query` commands and receive RAG answers with citations.

---

## Phase 4: User Story 2 - Retrieve Entities & Topics (Priority: P2)

**Goal**: Contributors can search by person/topic tags using `/archive topics` and `/archive people` commands

**Independent Test**: `/archive people "Gorga"` → returns mentions, links, context excerpts (requires contributor role)

### Implementation for User Story 2

- [x] T024 [US2] Create `/archive topics` command handler in `src/bot/commands/topics.py` (slash command definition, parameter: topic name, contributor+ access)
- [x] T025 [US2] Implement topics command logic in `src/bot/commands/topics.py` (send acknowledgment, check permissions, check rate limit, call EntityQueryService)
- [x] T026 [US2] Add topics response formatting in `src/bot/commands/topics.py` (format top 5 references with timestamps + links)
- [x] T027 [US2] Add topics error handling in `src/bot/commands/topics.py` (permission denied, no topics found, rate limit exceeded)
- [x] T028 [US2] Create `/archive people` command handler in `src/bot/commands/people.py` (slash command definition, parameter: person name, contributor+ access)
- [x] T029 [US2] Implement people command logic in `src/bot/commands/people.py` (send acknowledgment, check permissions, check rate limit, call EntityQueryService)
- [x] T030 [US2] Add people response formatting in `src/bot/commands/people.py` (format mentions, links, context excerpts)
- [x] T031 [US2] Add people error handling in `src/bot/commands/people.py` (permission denied, no people found, rate limit exceeded)
- [x] T032 [US2] Add audit logging for topics and people commands (create ArchiveQueryLog entries)
- [x] T033 [US2] Register `/archive topics` and `/archive people` commands in `src/bot/bot.py` (command tree registration)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Contributors can use `/archive topics` and `/archive people` commands, while public users can use `/archive query`.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and ensure full compliance

### User Story 3 - Provenance & Transparency (Cross-Cutting)

**Goal**: All bot responses include citations and source log IDs for auditability (US3)

**Note**: Citation formatting is already implemented in US1 and US2. This phase ensures completeness and cross-cutting improvements.

- [x] T034 [P] Verify citation format compliance in `src/bot/services/message_formatter.py` (ensure all citations follow `[meeting_id | date | speaker]` format) - Enhanced to support optional speaker/host, default uses workgroup_name for context
- [x] T035 [P] Verify audit logging completeness in all command handlers (ensure 100% logging compliance per SC-006) - All commands now log execution times, user info, and performance status
- [ ] T036 [P] Add "View full meeting record" links to citations in `src/bot/services/message_formatter.py`

### Error Handling & User Experience

- [x] T037 [P] Improve error messages across all commands (ensure all error messages are user-friendly per FR-008)
- [x] T038 [P] Add timeout handling for RAG pipeline calls in `src/bot/services/async_query_service.py` (handle RAG pipeline timeout gracefully)
- [ ] T039 [P] Add Discord API rate limit handling in `src/bot/bot.py` (queue requests when Discord rate limits exceeded)
- [x] T040 [P] Add validation for empty/unclear queries in command handlers (return helpful suggestions)

### Testing & Documentation

- [ ] T041 [P] Create bot initialization tests in `tests/bot/test_bot.py` (test bot connection, command registration)
- [ ] T042 [P] Create command handler tests in `tests/bot/test_commands.py` (mock Discord API, test command execution)
- [ ] T043 [P] Create rate limiter tests in `tests/bot/test_rate_limiter.py` (test rate limit enforcement, cleanup)
- [ ] T044 [P] Create permission checker tests in `tests/bot/test_permissions.py` (test role-based access control)
- [ ] T045 [P] Update quickstart.md with bot setup instructions (if needed)
- [ ] T046 [P] Add bot usage examples to README.md (document Discord bot commands)

### Performance & Monitoring

- [x] T047 [P] Add performance monitoring for query execution times in command handlers (track SC-001: 95% under 3 seconds)
- [x] T048 [P] Add background task for rate limit cleanup in `src/bot/services/rate_limiter.py` (periodic cleanup of expired entries) - Already implemented
- [x] T049 [P] Add logging for bot operations in `src/bot/bot.py` (structured logging using existing logger) - Enhanced with detailed startup, command sync, and cleanup logging

**Checkpoint**: All user stories should now be fully functional with complete error handling, audit logging, and performance monitoring.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Phase 5)**: Depends on all desired user stories being complete (US1 and US2)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories - MVP
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on US1, can run in parallel
- **User Story 3 (P3)**: Cross-cutting concern - implemented in Polish phase after US1 and US2 complete

### Within Each User Story

- Command handlers depend on services (rate limiter, permission checker, async query service)
- Response formatting depends on message formatter and message splitter
- Audit logging depends on existing AuditWriter
- All services must be implemented before command handlers

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, User Stories 1 and 2 can start in parallel (if team capacity allows)
- Within US2, topics and people commands can be implemented in parallel
- All Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# All foundational services must be complete first:
# - Rate limiter (T011)
# - Permission checker (T012)
# - Message formatter (T014)
# - Async query service (T015)
# - Bot initialization (T016)

# Then User Story 1 tasks can proceed:
Task: "Create /archive query command handler in src/bot/commands/query.py"
Task: "Implement query command logic in src/bot/commands/query.py"
Task: "Add response formatting in src/bot/commands/query.py"
Task: "Add error handling in src/bot/commands/query.py"
Task: "Add audit logging in src/bot/commands/query.py"
```

---

## Parallel Example: User Story 2

```bash
# After foundational services are complete:

# Topics command can be implemented:
Task: "Create /archive topics command handler in src/bot/commands/topics.py"
Task: "Implement topics command logic in src/bot/commands/topics.py"
Task: "Add topics response formatting in src/bot/commands/topics.py"

# People command can be implemented in parallel:
Task: "Create /archive people command handler in src/bot/commands/people.py"
Task: "Implement people command logic in src/bot/commands/people.py"
Task: "Add people response formatting in src/bot/commands/people.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T016) - **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T017-T023)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (`/archive query`) → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 (`/archive topics`, `/archive people`) → Test independently → Deploy/Demo
4. Add Polish phase (error handling, monitoring, documentation) → Test → Deploy/Demo
5. Each phase adds value without breaking previous phases

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (`/archive query`)
   - Developer B: User Story 2 (`/archive topics` and `/archive people` in parallel)
   - Developer C: Polish phase (error handling, tests, documentation)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (if tests are included)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All tasks integrate with existing services (QueryService, EntityQueryService, AuditWriter) without modifying them
- Bot uses existing RAG pipeline and audit system for full constitution compliance


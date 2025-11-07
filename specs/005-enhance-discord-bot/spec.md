# Feature Specification: Enhance Discord Bot with Entity Extraction and Issue Reporting

**Feature Branch**: `005-enhance-discord-bot`  
**Created**: 2025-11-06  
**Status**: Draft  
**Input**: User description: "Review the recent improvements to entity extraction, chunking and semantic to inform improvments to the Archive RAG Discord Bot. Suggest clear commands to use with the bot. Include relevant citations. Add the ability to raise an issue if the information returned is incorrect or misleading."

## Clarifications

### Session 2025-11-06

- Q: What should be the primary method for users to report issues from bot responses? → A: Discord button component (primary) - Button appears on every bot response, opens modal for issue details
- Q: How should the system handle potentially spam or abusive issue reports? → A: Automated detection + manual review - Detect patterns (duplicate reports, rapid-fire submissions), flag suspicious ones, but log all for admin review
- Q: What should happen when entity normalization fails to match a name variation? → A: Show both normalized and original - Attempt normalization, if it fails show results for exact match (if any) and suggest checking spelling/variations
- Q: What should happen when a user queries relationships for an entity that doesn't exist? → A: Show helpful suggestions - Return "Entity not found" with suggestions for similar entities (if normalization produces close matches) and guidance on how to search
- Q: When citations reference entities that were merged/normalized after the chunk was created, how should citations be displayed? → A: Always show canonical names - Citations always display current canonical entity names, even if chunk predates normalization (show current state)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enhanced Citations with Entity Context (Priority: P1)

**As** a Discord user querying archived meetings

**I want** to see detailed citations that include entity relationships and normalized names

**So that** I can trace information back to source meetings and understand context better

**Why this priority**: This leverages the core entity extraction improvements (normalization, relationships, semantic chunks) to provide immediate value. Enhanced citations improve trust and traceability of bot responses.

**Independent Test**: Can be fully tested by running `/archive query` and verifying citations include entity context (normalized names, relationships, chunk metadata). Delivers immediate value by improving citation quality.

**Acceptance Scenarios**:

1. **Given** I query `/archive query query:"What decisions did Stephen make?"`, **When** the bot responds, **Then** citations include normalized entity names (e.g., "Stephen [QADAO]" normalized to "Stephen") and show relationship context (e.g., "Stephen → attended → Meeting")
2. **Given** I query about a workgroup, **When** the bot responds, **Then** citations show relationship triples (e.g., "Archives WG → held → Meeting" and "Archives WG → made → Decision")
3. **Given** I query about a decision or action item, **When** the bot responds, **Then** citations include semantic chunk type (e.g., "decision_record", "action_item") and show which entities are mentioned in that chunk
4. **Given** citations reference entities with name variations, **When** the bot displays citations, **Then** all variations are normalized to canonical names for consistency

---

### User Story 2 - Entity Relationship Queries (Priority: P1)

**As** a Discord user

**I want** to query entity relationships directly (e.g., "Which workgroups made decisions?", "Who attended meetings?")

**So that** I can explore connections between entities without parsing natural language

**Why this priority**: This directly leverages relationship triples from entity extraction. Provides structured query capability that complements natural language queries.

**Independent Test**: Can be fully tested by adding `/archive relationships` command and verifying it returns relationship triples. Delivers value by enabling relationship exploration.

**Acceptance Scenarios**:

1. **Given** I run `/archive relationships workgroup:"Archives WG"`, **When** the bot responds, **Then** it shows all relationships for that workgroup (e.g., "Archives WG → held → Meeting", "Archives WG → made → Decision")
2. **Given** I run `/archive relationships person:"Stephen"`, **When** the bot responds, **Then** it shows all relationships for that person (e.g., "Stephen → attended → Meeting", "Stephen → assigned_to → ActionItem")
3. **Given** I run `/archive relationships meeting:"[meeting_id]"`, **When** the bot responds, **Then** it shows all entities related to that meeting (people, decisions, actions, documents)
4. **Given** I query with a name variation (e.g., "Stephen [QADAO]"), **When** the bot responds, **Then** it normalizes to canonical name and shows all relationships for that entity
5. **Given** I query with a name that cannot be normalized (e.g., very different spelling), **When** the bot responds, **Then** it shows results for exact match (if any) and suggests checking spelling/variations, indicating normalization was not applied
6. **Given** I query relationships for an entity that doesn't exist, **When** the bot responds, **Then** it returns "Entity not found" with suggestions for similar entities (if close matches exist) and guidance on how to search

---

### User Story 3 - Issue Reporting for Incorrect Information (Priority: P1)

**As** a Discord user who receives incorrect or misleading information

**I want** to report the issue directly from the bot response

**So that** the information can be corrected and the system improved

**Why this priority**: Critical for maintaining trust and improving system quality. Users need a way to flag problems when they encounter incorrect information.

**Independent Test**: Can be fully tested by adding issue reporting button/reaction to bot responses and verifying issues are logged. Delivers immediate value by enabling user feedback.

**Acceptance Scenarios**:

1. **Given** I receive a bot response, **When** I click the "Report Issue" button on the response, **Then** a modal form opens allowing me to provide details about what was incorrect or misleading
2. **Given** I report an issue, **When** the issue is submitted, **Then** it includes context (query text, response text, citations, timestamp, user ID) for investigation
3. **Given** I report an issue, **When** the issue is submitted, **Then** I receive confirmation that the issue was logged
4. **Given** multiple users report issues with the same response, **When** issues are reviewed, **Then** the system can aggregate reports to identify problematic patterns
5. **Given** a user submits multiple issue reports rapidly, **When** the system processes the reports, **Then** it flags potentially spam submissions for admin review while still logging all reports

---

### User Story 4 - Entity Search Commands with Normalization (Priority: P2)

**As** a Discord user searching for entities

**I want** to search using any name variation and get results for the canonical entity

**So that** I don't miss information due to naming inconsistencies

**Why this priority**: Leverages entity normalization to improve search. Users shouldn't need to know exact canonical names.

**Independent Test**: Can be fully tested by enhancing `/archive people` to use normalization and verifying searches with variations return all results. Delivers value by improving search completeness.

**Acceptance Scenarios**:

1. **Given** I search `/archive people person:"Stephen [QADAO]"`, **When** the bot responds, **Then** it normalizes to "Stephen" and shows all mentions regardless of name variation
2. **Given** I search for a person with multiple name variations, **When** the bot responds, **Then** it shows all variations that were normalized to the canonical name
3. **Given** I search for a workgroup, **When** the bot responds, **Then** it shows all meetings, decisions, and actions associated with that workgroup using relationship triples

---

### User Story 5 - Semantic Chunk Context in Responses (Priority: P2)

**As** a Discord user viewing query results

**I want** to see which semantic chunk type (meeting summary, decision, action item, etc.) each citation came from

**So that** I can understand the context and source type of information

**Why this priority**: Leverages semantic chunking improvements to provide better context. Users benefit from understanding the type of content they're viewing.

**Independent Test**: Can be fully tested by including chunk metadata in citations and verifying chunk types are displayed. Delivers value by improving citation clarity.

**Acceptance Scenarios**:

1. **Given** I receive citations in a query response, **When** the bot displays citations, **Then** each citation indicates the semantic chunk type (e.g., "decision_record", "action_item", "meeting_summary")
2. **Given** I receive a citation from a decision chunk, **When** the bot displays the citation, **Then** it shows which entities are mentioned in that chunk (from chunk metadata)
3. **Given** I receive a citation from an action item chunk, **When** the bot displays the citation, **Then** it shows relationship context (e.g., assignee, related meeting)

---

### Edge Cases

- What happens when a user reports an issue but the original query/response context is no longer available?
- How does the system handle issue reports that are spam or not actionable? → System uses automated detection to identify patterns (duplicate reports, rapid-fire submissions) and flags suspicious reports for admin review, but logs all reports for transparency
- What happens when entity normalization fails to match a name variation (e.g., very different spellings)? → System attempts normalization, if it fails shows results for exact match (if any) and suggests checking spelling/variations, providing transparency about normalization status
- How does the system handle relationship queries for entities that don't exist? → System returns "Entity not found" message with suggestions for similar entities (if normalization produces close matches) and provides guidance on how to search for entities
- What happens when citations reference entities that were merged/normalized after the chunk was created? → Citations always display current canonical entity names, even if the chunk was created before normalization occurred, ensuring users see the current normalized state
- How does the system handle issue reports for queries that had no results (false negatives)?
- What happens when multiple users report conflicting information about the same response?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST include normalized entity names in all citations (variations normalized to canonical names, always showing current canonical state even if chunk predates normalization)
- **FR-002**: System MUST display relationship triples in citations when available (e.g., "Workgroup → Meeting", "Person → Meeting")
- **FR-003**: System MUST show semantic chunk type in citations (meeting_summary, decision_record, action_item, attendance, resource)
- **FR-004**: System MUST provide a Discord button component on every bot response that allows users to report issues directly (button opens modal form for issue details)
- **FR-005**: System MUST capture issue report context (query text, response text, citations, timestamp, user ID, message ID)
- **FR-006**: System MUST allow users to provide issue details (description of what was incorrect or misleading)
- **FR-007**: System MUST confirm issue submission to users (acknowledgment message)
- **FR-008**: System MUST support entity relationship queries via `/archive relationships` command
- **FR-009**: System MUST normalize entity names in relationship queries (accept variations, return canonical names)
- **FR-020**: System MUST handle normalization failures gracefully by showing results for exact match (if any) and suggesting checking spelling/variations when normalization cannot be applied
- **FR-010**: System MUST display entity relationship triples in response format (Subject → Relationship → Object)
- **FR-011**: System MUST enhance `/archive people` command to use entity normalization (searches with variations return all results for canonical entity)
- **FR-012**: System MUST show entity name variations in search results (indicate which variations normalized to canonical name)
- **FR-013**: System MUST include entity metadata from semantic chunks in citations (which entities are mentioned in chunk)
- **FR-014**: System MUST log all issue reports for review and analysis
- **FR-015**: System MUST aggregate issue reports by query/response pattern to identify problematic patterns
- **FR-019**: System MUST use automated detection to identify potentially spam or abusive issue reports (duplicate reports, rapid-fire submissions) and flag them for admin review while logging all reports
- **FR-016**: Issue reports MUST be accessible to admins for review and resolution
- **FR-017**: System MUST handle relationship queries for workgroups, people, meetings, decisions, and action items
- **FR-021**: System MUST return helpful error messages when relationship queries target non-existent entities, including suggestions for similar entities (if normalization produces close matches) and guidance on how to search
- **FR-018**: System MUST display relationship context in citations (e.g., "from decision_record chunk", "assigned to Person")

### Key Entities *(include if feature involves data)*

- **Enhanced Citation**: A citation that includes normalized entity names, relationship triples, semantic chunk type, and entity metadata from chunk context
- **Issue Report**: A user-submitted report containing query context, response details, user feedback, and metadata (timestamp, user ID, message ID) for tracking incorrect or misleading information
- **Entity Relationship Query**: A query that returns relationship triples for a specified entity (workgroup, person, meeting, decision, action item)
- **Normalized Entity Search**: A search that accepts name variations and returns results for the canonical entity, showing all variations that were normalized

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of citations in bot responses include normalized entity names (no raw variations displayed)
- **SC-002**: 100% of citations show semantic chunk type when available (meeting_summary, decision_record, action_item, etc.)
- **SC-003**: Users can report issues from 100% of bot responses (issue reporting available for all query responses)
- **SC-004**: Issue reports capture 100% of required context (query, response, citations, timestamp, user ID) for investigation
- **SC-005**: Entity relationship queries return results in under 3 seconds for 95% of queries
- **SC-006**: Entity search commands normalize name variations correctly 95% of the time (variations mapped to canonical names)
- **SC-007**: Users can explore relationships for workgroups, people, meetings, decisions, and action items via `/archive relationships` command
- **SC-008**: Issue reports are logged and accessible to admins within 1 minute of submission
- **SC-009**: Users receive confirmation of issue submission within 5 seconds of reporting
- **SC-010**: Relationship triples are displayed in readable format (Subject → Relationship → Object) for 100% of relationship queries

## Assumptions

- Entity extraction improvements (normalization, relationships, semantic chunking) are already implemented and available
- Citation format can be enhanced to include additional metadata without breaking Discord message length limits
- Issue reports will be stored for admin review (storage mechanism not specified, but accessible to admins)
- Users understand that issue reports help improve the system but don't guarantee immediate fixes
- Entity normalization patterns are stable (variations consistently map to canonical names)
- Relationship triples are available for all extracted entities
- Semantic chunk metadata includes entity mentions and relationships for each chunk
- Discord bot can add interactive components (buttons, reactions) to messages for issue reporting
- Admins have access to review and manage issue reports
- Issue reporting is voluntary (users can choose to report or not)

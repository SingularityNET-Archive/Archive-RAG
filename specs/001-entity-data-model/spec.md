# Feature Specification: Entity-Based Data Model

**Feature Branch**: `001-entity-data-model`  
**Created**: 2025-11-02  
**Status**: Draft  
**Input**: User description: "change the data model to fit the following specs"

## Clarifications

### Session 2025-11-02

- Q: How should referential integrity be handled when deleting entities with references (e.g., person deleted but referenced in action items)? → A: Cascade delete - When a person/workgroup is deleted, also delete all related meetings/action items
- Q: How should the meeting-person (attendance) relationship be structured? → A: Many-to-many relationship - Separate junction table/entity linking meetings and people, enables bidirectional queries
- Q: Should meetings be required to have at least one participant? → A: Require at least one participant - Meeting validation fails if participant list is empty
- Q: Should agenda items be required to have at least one action item or decision item? → A: Allow empty agenda items - Agenda items can exist without action items or decision items (placeholder topics)
- Q: How should the system handle invalid or inaccessible document links? → A: Store as-is, validate on access - Accept links during ingestion, detect broken links when documents are accessed
- Q: What does "95% accuracy" mean for SC-005 (query meetings by topic tags)? → A: Both Precision and Recall: 95% precision (95% of returned meetings contain the queried topic) AND 95% recall (95% of meetings with the topic are returned)
- Q: What does "100% data preservation" include for SC-010 (migration)? → A: All meeting content (transcript text), entity relationships (foreign keys), metadata (dates, types, flags), and external references (document links)
- Q: How should the system handle meetings with canceled summaries or no summaries given (FR-018)? → A: Store flags and allow queries - meetings with `canceled_summary=true` or `no_summary_given=true` are returned in queries but marked appropriately in results

### Session 2025-11-02 (continued)

- Q: How should the system handle meetings with no participants given the contradiction between FR-024 (validation requires participants) and SC-009 (handles no participants without errors)? → A: Reject new meetings with no participants (validation fails), but allow reading/migrating legacy meetings that had no participants

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query Meetings by Workgroup (Priority: P1)

A user needs to find all meetings for a specific workgroup to understand the group's activity over time.

**Why this priority**: Core functionality - users must be able to navigate and filter meetings by workgroup, which is the primary organizational unit.

**Independent Test**: Can be fully tested by creating a workgroup with multiple meetings, then querying all meetings for that workgroup. Delivers immediate value by enabling workgroup-level analysis.

**Acceptance Scenarios**:

1. **Given** multiple workgroups exist, **When** a user queries meetings by workgroup_id, **Then** only meetings belonging to that workgroup are returned
2. **Given** a workgroup with 5 meetings and another with 3 meetings, **When** querying the first workgroup, **Then** exactly 5 meetings are returned
3. **Given** a workgroup with no meetings, **When** querying that workgroup, **Then** an empty result set is returned

---

### User Story 2 - Track Action Items and Assignees (Priority: P1)

A user needs to see all action items assigned to a specific person across all meetings to track their responsibilities.

**Why this priority**: Essential for accountability and task management - enables tracking who is responsible for what actions across the organization.

**Independent Test**: Can be fully tested by creating meetings with action items assigned to different people, then querying all action items for a specific person. Delivers value by enabling personal task tracking.

**Acceptance Scenarios**:

1. **Given** meetings with action items assigned to Person A and Person B, **When** querying action items for Person A, **Then** only Person A's assignments are returned
2. **Given** an action item with assignee, due date, and status, **When** querying that action item, **Then** all associated fields are correctly returned
3. **Given** an action item with no assignee, **When** querying action items by person, **Then** unassigned items are excluded from person-specific queries

---

### User Story 3 - Link Documents to Meetings (Priority: P2)

A user needs to access working documents referenced during a meeting to get full context.

**Why this priority**: Important for context and reference - meetings often reference external documents that provide essential background.

**Independent Test**: Can be fully tested by creating a meeting with linked documents, then retrieving all documents for that meeting. Delivers value by providing quick access to meeting-related resources.

**Acceptance Scenarios**:

1. **Given** a meeting with 3 linked documents, **When** querying documents for that meeting, **Then** all 3 documents with titles and links are returned
2. **Given** a meeting with no documents, **When** querying documents for that meeting, **Then** an empty result set is returned
3. **Given** a document linked to a meeting, **When** accessing that document, **Then** both the document metadata and associated meeting context are available

---

### User Story 4 - Navigate Decisions and Their Context (Priority: P2)

A user needs to see decisions made in meetings along with their rationales and effects to understand the reasoning behind organizational choices.

**Why this priority**: Important for transparency and understanding - decisions with context help users understand organizational reasoning and impacts.

**Independent Test**: Can be fully tested by creating agenda items with decision items containing rationales and effects, then querying decisions with their full context. Delivers value by providing transparent decision-making records.

**Acceptance Scenarios**:

1. **Given** an agenda item with multiple decision items, **When** querying decisions for that agenda item, **Then** all decisions with their rationales and effects are returned
2. **Given** a decision with rationale and effect scope, **When** querying that decision, **Then** both rationale and effect information are included
3. **Given** decisions with "mayAffectOtherPeople" effect, **When** querying decisions that affect other workgroups, **Then** only decisions with that scope are returned

---

### User Story 5 - Filter by Tags and Topics (Priority: P3)

A user needs to find meetings by topics covered or emotional tone to discover related content across workgroups.

**Why this priority**: Nice-to-have enhancement - enables discovery and cross-workgroup topic analysis through metadata.

**Independent Test**: Can be fully tested by tagging meetings with topics and emotions, then querying meetings by tag values. Delivers value by enabling topic-based discovery.

**Acceptance Scenarios**:

1. **Given** meetings tagged with topics like "budget" and "planning", **When** querying meetings by topic "budget", **Then** all meetings with that topic tag are returned
2. **Given** meetings tagged with emotions like "collaborative" and "friendly", **When** querying by emotion, **Then** relevant meetings are returned
3. **Given** a meeting with no tags, **When** querying by tag, **Then** untagged meetings are excluded from tag-based queries

---

### Edge Cases

- When a person is deleted, all associated action items are cascade deleted (person-action item relationship)
- When a workgroup is deleted, all associated meetings (and their related entities: documents, agenda items, action items, decision items, tags) are cascade deleted
- System requires at least one participant per meeting for new meetings (validation fails if participant list is empty) - legacy meetings with no participants can be read/migrated but should be flagged
- Meetings with canceled summaries or no summaries given are stored with flags set (`canceled_summary=true` or `no_summary_given=true`), returned in queries, and marked appropriately in query results
- Agenda items without action items or decision items are valid - system allows empty agenda items as placeholder topics
- Document links are stored as-is during ingestion - validation occurs on access when documents are retrieved, broken links are detected but do not block ingestion

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support storing workgroups with unique identifiers and names
- **FR-002**: System MUST support storing meetings with associations to workgroups, hosts, and documenters
- **FR-003**: System MUST support storing person entities with display names and optional aliases
- **FR-024**: System MUST validate that meetings have at least one participant - meetings with empty participant lists are invalid (Note: Basic validation for new meetings is implemented in User Story 1; full many-to-many relationship validation with MeetingPerson junction table is implemented in Phase 8)
- **FR-004**: System MUST support linking documents to meetings with titles and URLs (links validated on access, not during ingestion)
- **FR-005**: System MUST support storing agenda items with status indicators (agenda items can exist without action items or decision items)
- **FR-006**: System MUST support storing action items with assignees, due dates, and status
- **FR-007**: System MUST support storing decision items with optional rationales and effect scopes
- **FR-008**: System MUST support tagging meetings with topics and emotions
- **FR-009**: System MUST support querying meetings by workgroup identifier
- **FR-010**: System MUST support querying action items by assignee
- **FR-011**: System MUST support querying all meetings attended by a specific person via many-to-many relationship (Note: Implementation of many-to-many relationship infrastructure is in Phase 8; basic query capability enabled after Phase 8 completion)
- **FR-023**: System MUST implement many-to-many relationship between meetings and people using junction table/entity to enable bidirectional queries (Note: This is implemented in Phase 8: Many-to-Many Relationship & Cascade Deletes, not as part of User Story 1)
- **FR-012**: System MUST support retrieving all documents linked to a meeting (broken/inaccessible links detected during retrieval but do not block retrieval operation)
- **FR-013**: System MUST support retrieving all agenda items for a meeting
- **FR-014**: System MUST support retrieving all action items for an agenda item
- **FR-015**: System MUST support retrieving all decision items for an agenda item
- **FR-016**: System MUST support querying meetings by tag values (topics or emotions)
- **FR-017**: System MUST maintain referential integrity between related entities (workgroups-meetings, meetings-people, etc.)
- **FR-021**: System MUST implement cascade delete: deleting a person deletes all associated action items
- **FR-022**: System MUST implement cascade delete: deleting a workgroup deletes all associated meetings and their related entities (documents, agenda items, action items, decision items, tags)
- **FR-018**: System MUST handle meetings with canceled summaries or no summaries given - meetings with `canceled_summary=true` or `no_summary_given=true` are stored with these flags set, returned in queries, and marked appropriately in query results
- **FR-019**: System MUST support storing meeting metadata including type, date, purpose, and video links
- **FR-020**: System MUST extract transcript content from decision items for RAG embedding purposes

### Key Entities

- **Workgroup**: Represents organizational groups responsible for meetings. Key attributes: unique identifier, name. Relationships: has many meetings, optionally contains people.

- **Meeting**: Represents documented meeting events. Key attributes: unique identifier, workgroup association, type, date, host, documenter, purpose, video link, timestamped video data, summary flags. Relationships: belongs to workgroup, attended by people (many-to-many via junction table/entity), has documents, has agenda items, has tags.

- **Person**: Represents participants, hosts, and documenters. Key attributes: unique identifier, display name, optional alias, optional role. Relationships: attends many meetings (many-to-many via junction table/entity), assigned many action items.

- **Document**: Represents working documents or reference links. Key attributes: unique identifier, meeting association, title, link. Relationships: belongs to meeting.

- **AgendaItem**: Represents topics or issues discussed. Key attributes: unique identifier, meeting association, status. Relationships: belongs to meeting, has action items, has decision items.

- **ActionItem**: Represents tasks arising from meetings. Key attributes: unique identifier, agenda item association, text, assignee, due date, status. Relationships: belongs to agenda item, assigned to person.

- **DecisionItem**: Represents decisions and rationales. Key attributes: unique identifier, agenda item association, decision text, optional rationale, effect scope. Relationships: belongs to agenda item.

- **Tag**: Represents topic and emotional metadata. Key attributes: unique identifier, meeting association, topics covered, emotions. Relationships: belongs to meeting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can query all meetings for a specific workgroup in under 2 seconds
- **SC-002**: Users can retrieve all action items assigned to a person across all meetings in under 3 seconds
- **SC-003**: Users can access all documents linked to a meeting in under 1 second
- **SC-004**: System maintains referential integrity for 100% of entity relationships
- **SC-005**: Users can query meetings by topic tags with 95% precision (95% of returned meetings contain the queried topic) AND 95% recall (95% of meetings with the topic are returned)
- **SC-006**: System supports storing and retrieving meetings with full entity relationships without data loss
- **SC-007**: Users can navigate from a meeting to all related entities (people, documents, agenda items) in under 2 seconds per relationship type
- **SC-008**: RAG system can extract and embed transcript content from decision items with 100% coverage of decision text (Validation: All decision text fields from DecisionItem entities must be extracted and available for RAG embedding; test coverage verifies no decision text is missed)
- **SC-009**: System handles legacy meetings with no participants or empty transcripts gracefully during migration (allows reading/migrating legacy data without errors, but new meetings must have at least one participant per FR-024). "Gracefully" means: (1) legacy meetings without participants are migrated with a warning flag, (2) no migration errors are raised for missing participants in legacy data, (3) new meetings (post-migration) must have at least one participant or validation fails
- **SC-010**: Migration from existing flat data structure to relational model preserves 100% of meeting content (transcript text), entity relationships (foreign keys), metadata (dates, types, flags), and external references (document links)

## Assumptions

- All entity identifiers will use UUID format for uniqueness
- Person entities can be referenced by either ID or display name for backward compatibility
- Meeting transcript content will continue to be extracted primarily from decision items for RAG purposes
- Existing data can be migrated to new relational structure while maintaining backward compatibility for read operations
- Tag topics and emotions can be stored as text or arrays depending on implementation needs
- Action item status will support standard workflow states (todo, in progress, done, etc.)
- Decision item effect scopes are limited to specified enumeration values
- System will maintain both structured graph relationships and flat embedding-ready content for RAG functionality

## Dependencies

- Existing RAG embedding system must continue to function with new data model
- Current indexing and querying capabilities must adapt to relational structure
- Migration path from current flat JSON structure to new entity-based model
- Support for both graph-based relationship queries and vector similarity search

## Notes

- The data model should support both relational queries (for structured relationships) and vector embeddings (for semantic search via RAG)
- Graph structure enables navigation of roles, responsibilities, and temporal meeting sequences
- Tag extraction through topic modeling and entity extraction will populate tag relationships
- Future ethics/governance layer can extend entities with audit trails, data provenance, and policy version bindings

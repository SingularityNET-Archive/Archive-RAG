# Data Model: Entity-Based Structure

**Feature**: Entity-Based Data Model  
**Date**: 2025-11-02  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

The Archive-RAG data model is refactored from a flat JSON structure to a relational entity-based model with proper relationships, referential integrity, and cascade delete behaviors. This enables efficient querying, relationship navigation, and data integrity while maintaining compatibility with existing RAG embedding and querying systems.

## Entity Relationships

```
Workgroup
  └─┬─ has many → Meeting
     │
Meeting
  ├─┬─ belongs to → Workgroup (FK)
  ├─┬─ attended by → Person (many-to-many via MeetingPerson)
  ├─┬─ has many → Document
  ├─┬─ has many → AgendaItem
  └─┬─ has many → Tag
     │
Person
  ├─┬─ attends many → Meeting (many-to-many via MeetingPerson)
  └─┬─ assigned many → ActionItem (FK)
     │
Document
  └─┬─ belongs to → Meeting (FK)
     │
AgendaItem
  ├─┬─ belongs to → Meeting (FK)
  ├─┬─ has many → ActionItem
  └─┬─ has many → DecisionItem
     │
ActionItem
  ├─┬─ belongs to → AgendaItem (FK)
  └─┬─ assigned to → Person (FK)
     │
DecisionItem
  └─┬─ belongs to → AgendaItem (FK)
     │
Tag
  └─┬─ belongs to → Meeting (FK)
     │
MeetingPerson (Junction Table)
  ├─┬─ belongs to → Meeting (FK)
  └─┬─ belongs to → Person (FK)
```

## Entity Definitions

### Workgroup

**Description**: Organizational groups responsible for meetings

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `name` (String, Required): Workgroup name

**Relationships**:
- One-to-many: Workgroup **has many** Meetings
- Optional: Workgroup **contains** People (via meeting attendance)

**Validation Rules**:
- `name` must not be empty

**Cascade Behavior**:
- Deleting Workgroup → Cascade delete all associated Meetings and their related entities (documents, agenda items, action items, decision items, tags)

---

### Meeting

**Description**: Documented meeting events

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `workgroup_id` (UUID, Foreign Key → Workgroup): Workgroup association
- `type` (Enum, Optional): Meeting type (`Monthly`, `Weekly`, `Biweekly`, `Custom`, `Standard`)
- `date` (Date, Required): Meeting date (ISO 8601 format)
- `host_id` (UUID, Foreign Key → Person): Meeting host
- `documenter_id` (UUID, Foreign Key → Person): Meeting documenter
- `purpose` (Text, Optional): Meeting purpose
- `video_link` (URL, Optional): Meeting video link
- `timestamped_video` (JSON/Dict, Optional): Timestamped video data
- `no_summary_given` (Boolean, Default: false): Flag indicating no summary provided
- `canceled_summary` (Boolean, Default: false): Flag indicating summary was canceled
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

**Relationships**:
- Many-to-one: Meeting **belongs to** Workgroup
- Many-to-many: Meeting **attended by** People (via MeetingPerson junction table)
- One-to-many: Meeting **has many** Documents
- One-to-many: Meeting **has many** AgendaItems
- One-to-many: Meeting **has many** Tags

**Validation Rules**:
- `workgroup_id` must reference existing Workgroup
- `date` must be valid ISO 8601 date format
- `host_id` must reference existing Person (optional but recommended)
- `documenter_id` must reference existing Person (optional but recommended)
- Meeting **MUST have at least one participant** via MeetingPerson relationship (FR-024)

**Cascade Behavior**:
- Deleting Meeting → Cascade delete all associated entities (documents, agenda items, tags, MeetingPerson records)
- Deleting Workgroup → Cascade delete all associated Meetings and their related entities

**Transcript Extraction**:
- Transcript content extracted from `agendaItems[].decisionItems[].decision` texts for RAG embedding purposes (FR-020)

---

### Person

**Description**: Participants, hosts, and documenters

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `display_name` (String, Required): Person's display name
- `alias` (String, Optional): Alternative name or alias
- `role` (String, Optional): Person's role (e.g., "host", "documenter", "participant")
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

**Relationships**:
- Many-to-many: Person **attends many** Meetings (via MeetingPerson junction table)
- One-to-many: Person **assigned many** ActionItems

**Validation Rules**:
- `display_name` must not be empty

**Cascade Behavior**:
- Deleting Person → Cascade delete all associated ActionItems (FR-021)

---

### MeetingPerson (Junction Table)

**Description**: Many-to-many relationship between Meetings and People (attendance)

**Fields**:
- `meeting_id` (UUID, Foreign Key → Meeting, Primary Key): Meeting reference
- `person_id` (UUID, Foreign Key → Person, Primary Key): Person reference
- `role` (String, Optional): Role in meeting (e.g., "host", "documenter", "participant")
- `created_at` (DateTime): Creation timestamp

**Relationships**:
- Many-to-one: MeetingPerson **belongs to** Meeting
- Many-to-one: MeetingPerson **belongs to** Person

**Validation Rules**:
- `meeting_id` must reference existing Meeting
- `person_id` must reference existing Person
- Composite primary key: (`meeting_id`, `person_id`)

**Cascade Behavior**:
- Deleting Meeting → Cascade delete all associated MeetingPerson records
- Deleting Person → Cascade delete all associated MeetingPerson records

---

### Document

**Description**: Working documents or reference links

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `meeting_id` (UUID, Foreign Key → Meeting): Meeting association
- `title` (String, Required): Document title
- `link` (URL, Required): Document link/URL
- `created_at` (DateTime): Creation timestamp

**Relationships**:
- Many-to-one: Document **belongs to** Meeting

**Validation Rules**:
- `meeting_id` must reference existing Meeting
- `title` must not be empty
- `link` must be valid URL format (validated on access, not during ingestion) (FR-004)

**Cascade Behavior**:
- Deleting Meeting → Cascade delete all associated Documents

**Link Validation**:
- Links stored as-is during ingestion
- Validation occurs on access when documents are retrieved
- Broken/inaccessible links detected but do not block retrieval operation (FR-012)

---

### AgendaItem

**Description**: Topics or issues discussed in meetings

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `meeting_id` (UUID, Foreign Key → Meeting): Meeting association
- `status` (Enum, Optional): Agenda item status (`carry over`, `complete`, etc.)
- `narrative` (Text, Optional): Narrative text describing agenda item
- `created_at` (DateTime): Creation timestamp

**Relationships**:
- Many-to-one: AgendaItem **belongs to** Meeting
- One-to-many: AgendaItem **has many** ActionItems
- One-to-many: AgendaItem **has many** DecisionItems

**Validation Rules**:
- `meeting_id` must reference existing Meeting
- AgendaItem **can exist without** ActionItems or DecisionItems (empty agenda items are valid) (FR-005)

**Cascade Behavior**:
- Deleting Meeting → Cascade delete all associated AgendaItems and their related entities (ActionItems, DecisionItems)

---

### ActionItem

**Description**: Tasks arising from meetings

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `agenda_item_id` (UUID, Foreign Key → AgendaItem): Agenda item association
- `text` (Text, Required): Action item description
- `assignee_id` (UUID, Foreign Key → Person, Optional): Person assigned to action item
- `due_date` (Date, Optional): Due date for action item
- `status` (Enum, Optional): Action item status (`todo`, `in progress`, `done`, etc.)
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

**Relationships**:
- Many-to-one: ActionItem **belongs to** AgendaItem
- Many-to-one: ActionItem **assigned to** Person (optional)

**Validation Rules**:
- `agenda_item_id` must reference existing AgendaItem
- `text` must not be empty
- `assignee_id` must reference existing Person (if provided)
- `status` must be valid enumeration value

**Cascade Behavior**:
- Deleting AgendaItem → Cascade delete all associated ActionItems
- Deleting Person → Cascade delete all associated ActionItems (FR-021)

---

### DecisionItem

**Description**: Decisions and rationales from meetings

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `agenda_item_id` (UUID, Foreign Key → AgendaItem): Agenda item association
- `decision` (Text, Required): Decision text (used for transcript extraction)
- `rationale` (Text, Optional): Rationale for decision
- `effect` (Enum, Optional): Effect scope (`affectsOnlyThisWorkgroup`, `mayAffectOtherPeople`)
- `created_at` (DateTime): Creation timestamp

**Relationships**:
- Many-to-one: DecisionItem **belongs to** AgendaItem

**Validation Rules**:
- `agenda_item_id` must reference existing AgendaItem
- `decision` must not be empty
- `effect` must be valid enumeration value (if provided)

**Cascade Behavior**:
- Deleting AgendaItem → Cascade delete all associated DecisionItems

**Transcript Extraction**:
- `decision` text is extracted and combined to form meeting transcript for RAG embedding (FR-020)

---

### Tag

**Description**: Topic and emotional metadata for meetings

**Fields**:
- `id` (UUID, Primary Key): Unique identifier
- `meeting_id` (UUID, Foreign Key → Meeting): Meeting association
- `topics_covered` (Text or Array, Optional): Topics covered in meeting
- `emotions` (Text or Array, Optional): Emotional tone of meeting
- `created_at` (DateTime): Creation timestamp

**Relationships**:
- Many-to-one: Tag **belongs to** Meeting

**Validation Rules**:
- `meeting_id` must reference existing Meeting
- `topics_covered` and `emotions` can be stored as text (comma-separated) or arrays depending on implementation needs

**Cascade Behavior**:
- Deleting Meeting → Cascade delete all associated Tags

---

## Referential Integrity Rules

### Cascade Delete Behaviors (File-Based)

1. **Person Deletion**:
   - Delete Person JSON file → Cascade delete all ActionItem JSON files assigned to that Person
   - Delete Person → Cascade delete all MeetingPerson records (update `_relations/meeting_person.json`)
   - Update index files to remove person references

2. **Workgroup Deletion**:
   - Delete Workgroup JSON file → Cascade delete all Meeting JSON files in that Workgroup
   - Delete Meetings → Cascade delete all related entity JSON files (Documents, AgendaItems, Tags)
   - Delete AgendaItems → Cascade delete all ActionItem and DecisionItem JSON files
   - Update relationship files and index files

3. **Meeting Deletion**:
   - Delete Meeting JSON file → Cascade delete all Document JSON files
   - Delete Meeting → Cascade delete all AgendaItem JSON files (and their ActionItems, DecisionItems)
   - Delete Meeting → Cascade delete all Tag JSON files
   - Delete Meeting → Cascade delete all MeetingPerson records (update `_relations/meeting_person.json`)
   - Update index files to remove meeting references

4. **AgendaItem Deletion**:
   - Delete AgendaItem JSON file → Cascade delete all ActionItem JSON files
   - Delete AgendaItem → Cascade delete all DecisionItem JSON files
   - Update index files to remove agenda item references

### Validation Rules

1. **Meeting Validation**:
   - Meeting MUST have at least one participant (via MeetingPerson relationship)
   - Meeting validation fails if participant list is empty (FR-024)

2. **AgendaItem Validation**:
   - AgendaItem can exist without ActionItems or DecisionItems (empty agenda items are valid)

3. **Document Link Validation**:
   - Document links validated on access, not during ingestion
   - Broken links detected during retrieval but do not block operation

## Query Patterns

### Common Queries

1. **Query Meetings by Workgroup**:
   ```python
   workgroup.meetings  # SQLAlchemy relationship
   # Or: SELECT * FROM meetings WHERE workgroup_id = ?
   ```

2. **Query Meetings Attended by Person**:
   ```python
   person.meetings  # SQLAlchemy relationship via MeetingPerson
   # Or: SELECT meetings.* FROM meetings 
   #     JOIN meeting_person ON meetings.id = meeting_person.meeting_id
   #     WHERE meeting_person.person_id = ?
   ```

3. **Query Action Items by Assignee**:
   ```python
   person.action_items  # SQLAlchemy relationship
   # Or: SELECT * FROM action_items WHERE assignee_id = ?
   ```

4. **Query Documents for Meeting**:
   ```python
   meeting.documents  # SQLAlchemy relationship
   # Or: SELECT * FROM documents WHERE meeting_id = ?
   ```

5. **Query Agenda Items for Meeting**:
   ```python
   meeting.agenda_items  # SQLAlchemy relationship
   # Or: SELECT * FROM agenda_items WHERE meeting_id = ?
   ```

6. **Query Decisions by Effect Scope**:
   ```python
   # SELECT * FROM decision_items WHERE effect = 'mayAffectOtherPeople'
   ```

7. **Query Meetings by Tag**:
   ```python
   # SELECT meetings.* FROM meetings 
   # JOIN tags ON meetings.id = tags.meeting_id
   # WHERE tags.topics_covered LIKE '%budget%'
   ```

## Migration from Flat JSON

### Legacy Format Mapping

**Legacy JSON Structure** → **Entity Model**:

- `id` → `Meeting.id`
- `date` → `Meeting.date`
- `participants: ["Alice", "Bob"]` → `MeetingPerson` records + `Person` entities
- `transcript` → Extracted from `DecisionItem.decision` texts
- `decisions: ["Decision 1"]` → `DecisionItem` entities
- `tags: ["budget"]` → `Tag` entity with `topics_covered`

### New Format Mapping

**Archives Workgroup Format** → **Entity Model**:

- `workgroup_id` → `Workgroup.id`
- `workgroup` → `Workgroup.name`
- `meetingInfo.date` → `Meeting.date`
- `meetingInfo.peoplePresent` → `MeetingPerson` records + `Person` entities
- `meetingInfo.host` → `Person` + `Meeting.host_id`
- `meetingInfo.documenter` → `Person` + `Meeting.documenter_id`
- `meetingInfo.workingDocs` → `Document` entities
- `agendaItems[].decisionItems[].decision` → `DecisionItem` entities
- `agendaItems[].actionItems` → `ActionItem` entities
- `tags.topicsCovered` → `Tag.topics_covered`
- `tags.emotions` → `Tag.emotions`

## Implementation Notes

- **Storage**: JSON files organized in directory structure (`entities/workgroups/`, `entities/meetings/`, etc.)
- **Query Layer**: File-based queries with index files for fast lookups
- **Validation**: Pydantic models for business logic validation
- **Cascade Deletes**: Implemented via file deletion operations with backup/restore pattern
- **Atomic Operations**: File-based atomic writes using temporary files + rename pattern, with backup/restore on errors
- **Performance**: Index files (JSON) enable O(1) or O(log n) lookups, ensuring <2-3 second targets for typical data volumes


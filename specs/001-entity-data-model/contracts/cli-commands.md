# CLI Commands: Entity-Based Data Model

**Feature**: Entity-Based Data Model  
**Date**: 2025-11-02  
**Spec**: [../spec.md](../spec.md)

## New Commands

### `archive-rag init-entities`

Initialize entity storage directory structure.

**Usage**:
```bash
archive-rag init-entities [OPTIONS]
```

**Options**:
- `--entities-dir PATH`: Path to entities directory (default: `entities/`)
- `--force`: Overwrite existing directory structure (⚠️ destructive)

**Behavior**:
- Creates directory structure (`entities/workgroups/`, `entities/meetings/`, `entities/people/`, etc.)
- Creates index directories (`entities/_index/`, `entities/_relations/`)
- Initializes empty index files for fast lookups
- Sets up relationship file structure

**Exit Codes**:
- `0`: Success
- `1`: Directory initialization failed
- `2`: Directory already exists (use `--force` to overwrite)

---

### `archive-rag migrate-entities`

Migrate existing flat JSON data to entity model.

**Usage**:
```bash
archive-rag migrate-entities [OPTIONS] SOURCE
```

**Arguments**:
- `SOURCE`: URL or directory path to source data

**Options**:
- `--source-url URL`: Source data URL (alternative to SOURCE argument)
- `--source-dir PATH`: Source data directory (alternative to SOURCE argument)
- `--target-dir PATH`: Target entity storage directory (default: `entities/`)
- `--dry-run`: Preview migration without executing
- `--validate`: Validate migration results after execution
- `--execute`: Execute migration (required after dry-run preview)

**Behavior**:
- Reads source data (JSON files or URL)
- **URL ingestion preserved**: Supports GitHub URL (`https://raw.githubusercontent.com/.../meeting-summaries-array.json`)
- Fetches JSON array from URL if URL provided
- Converts flat JSON structure to entity model (each meeting in array)
- Validates referential integrity
- Creates entity records with relationships
- Validates cascade delete behaviors

**Exit Codes**:
- `0`: Migration successful
- `1`: Migration failed (validation errors)
- `2`: Dry-run preview only (use `--execute` to apply)

---

### `archive-rag query-workgroup`

Query meetings by workgroup.

**Usage**:
```bash
archive-rag query-workgroup WORKGROUP_NAME [OPTIONS]
```

**Arguments**:
- `WORKGROUP_NAME`: Name or ID of workgroup to query

**Options**:
- `--workgroup-id UUID`: Workgroup UUID (alternative to name)
- `--output-format FORMAT`: Output format (`text`, `json`) (default: `text`)
- `--limit N`: Limit number of results (default: 100)

**Behavior**:
- Queries all meetings for specified workgroup
- Returns meeting list with metadata
- Performance target: <2 seconds (SC-001)

**Output**:
- Text format: List of meetings with dates and IDs
- JSON format: Array of meeting objects

---

### `archive-rag query-person`

Query person-related data (meetings, action items).

**Usage**:
```bash
archive-rag query-person PERSON_NAME [OPTIONS]
```

**Arguments**:
- `PERSON_NAME`: Display name or ID of person

**Options**:
- `--person-id UUID`: Person UUID (alternative to name)
- `--action-items`: Query action items assigned to person
- `--meetings`: Query meetings attended by person
- `--output-format FORMAT`: Output format (`text`, `json`) (default: `text`)
- `--limit N`: Limit number of results (default: 100)

**Behavior**:
- Queries person's meetings (via MeetingPerson relationship)
- Queries person's action items (via ActionItem.assignee_id)
- Performance target: <3 seconds for action items (SC-002)

**Output**:
- Text format: List of meetings/action items with details
- JSON format: Array of meeting/action item objects

---

### `archive-rag query-meeting`

Query meeting details and related entities.

**Usage**:
```bash
archive-rag query-meeting MEETING_ID [OPTIONS]
```

**Arguments**:
- `MEETING_ID`: UUID of meeting

**Options**:
- `--documents`: Show linked documents
- `--participants`: Show meeting participants
- `--agenda-items`: Show agenda items
- `--action-items`: Show action items
- `--decisions`: Show decision items
- `--tags`: Show tags
- `--output-format FORMAT`: Output format (`text`, `json`) (default: `text`)

**Behavior**:
- Retrieves meeting details
- Optionally retrieves related entities (documents, participants, agenda items, etc.)
- Performance target: <2 seconds per relationship type (SC-007)

**Output**:
- Text format: Meeting details with related entities
- JSON format: Meeting object with nested related entities

---

### `archive-rag validate-entities`

Validate entity relationships and referential integrity.

**Usage**:
```bash
archive-rag validate-entities [OPTIONS]
```

**Options**:
- `--entities-dir PATH`: Path to entity storage directory (default: `entities/`)
- `--check-cascade`: Test cascade delete behaviors
- `--fix`: Attempt to fix validation errors (if possible)

**Behavior**:
- Validates foreign key constraints
- Checks referential integrity
- Validates cascade delete behaviors
- Reports validation errors

**Exit Codes**:
- `0`: All validations pass
- `1`: Validation errors found
- `2`: Fixable errors were fixed (with `--fix`)

---

### `archive-rag test-cascade-delete`

Test cascade delete behaviors (for validation).

**Usage**:
```bash
archive-rag test-cascade-delete [OPTIONS]
```

**Options**:
- `--person-id UUID`: Test cascade delete for person
- `--workgroup-id UUID`: Test cascade delete for workgroup
- `--meeting-id UUID`: Test cascade delete for meeting
- `--dry-run`: Preview cascade delete without executing

**Behavior**:
- Tests cascade delete behavior for specified entity
- Lists entities that will be cascade deleted
- Validates referential integrity after cascade

**Exit Codes**:
- `0`: Cascade delete test successful
- `1`: Cascade delete test failed

---

## Updated Commands

### `archive-rag index` (Updated)

Enhanced to support entity model alongside legacy format.

**New Options**:
- `--use-entities`: Use entity model for storage (default: legacy format during transition)
- `--db-path PATH`: Path to entity database (default: `entities.db`)

**Behavior**:
- Detects data format (legacy or new)
- Stores in entity model if `--use-entities` flag provided
- Creates entity relationships during indexing
- Maintains backward compatibility with legacy format

---

### `archive-rag query` (Updated)

Enhanced to support entity-based queries alongside RAG queries.

**New Options**:
- `--use-entity-context`: Include entity relationship context in RAG queries
- `--filter-workgroup WORKGROUP`: Filter results by workgroup
- `--filter-person PERSON`: Filter results by person

**Behavior**:
- Standard RAG queries continue to work (unchanged)
- Optional entity context enhances query results with relationship data
- Filter options restrict results to specific workgroups or people

---

## Data Contracts

### Entity Storage Format

Entities are stored as JSON files organized in directory structure:

```
entities/
├── workgroups/
│   └── {id}.json
├── meetings/
│   └── {id}.json
├── people/
│   └── {id}.json
├── documents/
│   └── {id}.json
├── agenda_items/
│   └── {id}.json
├── action_items/
│   └── {id}.json
├── decision_items/
│   └── {id}.json
├── tags/
│   └── {id}.json
├── _index/
│   ├── workgroups.json          # {id: workgroup_data}
│   ├── meetings_by_workgroup.json  # {workgroup_id: [meeting_ids]}
│   ├── meeting_person_by_meeting.json  # {meeting_id: [person_ids]}
│   └── meeting_person_by_person.json  # {person_id: [meeting_ids]}
└── _relations/
    └── meeting_person.json       # [{meeting_id, person_id, role}]
```

### Entity File Format

Each entity stored as individual JSON file:

**Workgroup File** (`entities/workgroups/{id}.json`):
```json
{
  "id": "UUID",
  "name": "String",
  "created_at": "DateTime (ISO 8601)",
  "updated_at": "DateTime (ISO 8601)"
}
```

**Meeting File** (`entities/meetings/{id}.json`):
```json
{
  "id": "UUID",
  "workgroup_id": "UUID",
  "type": "Enum | null",
  "date": "Date (ISO 8601)",
  "host_id": "UUID | null",
  "documenter_id": "UUID | null",
  "purpose": "String | null",
  "video_link": "URL | null",
  "timestamped_video": {},
  "no_summary_given": false,
  "canceled_summary": false,
  "created_at": "DateTime (ISO 8601)",
  "updated_at": "DateTime (ISO 8601)"
}
```

**Person File** (`entities/people/{id}.json`):
```json
{
  "id": "UUID",
  "display_name": "String",
  "alias": "String | null",
  "role": "String | null",
  "created_at": "DateTime (ISO 8601)",
  "updated_at": "DateTime (ISO 8601)"
}
```

**MeetingPerson Junction File** (`entities/_relations/meeting_person.json`):
```json
[
  {
    "meeting_id": "UUID",
    "person_id": "UUID",
    "role": "String | null",
    "created_at": "DateTime (ISO 8601)"
  }
]
```

**Index Files** (`entities/_index/meetings_by_workgroup.json`):
```json
{
  "workgroup_id_1": ["meeting_id_1", "meeting_id_2"],
  "workgroup_id_2": ["meeting_id_3", "meeting_id_4"]
}
```

**Index Files** (`entities/_index/meeting_person_by_meeting.json`):
```json
{
  "meeting_id_1": ["person_id_1", "person_id_2"],
  "meeting_id_2": ["person_id_2", "person_id_3"]
}
```

**Index Files** (`entities/_index/meeting_person_by_person.json`):
```json
{
  "person_id_1": ["meeting_id_1", "meeting_id_3"],
  "person_id_2": ["meeting_id_1", "meeting_id_2"]
}
```

### Validation Contracts

**Meeting Validation**:
- ✅ MUST have at least one participant (via MeetingPerson)
- ✅ `workgroup_id` MUST reference existing Workgroup
- ✅ `date` MUST be valid ISO 8601 format

**AgendaItem Validation**:
- ✅ `meeting_id` MUST reference existing Meeting
- ✅ CAN exist without ActionItems or DecisionItems (empty agenda items valid)

**Document Validation**:
- ✅ `meeting_id` MUST reference existing Meeting
- ✅ `link` validated on access (not during ingestion)

### Cascade Delete Contracts

**Person Deletion**:
- ✅ Deletes all ActionItems assigned to Person
- ✅ Deletes all MeetingPerson records for Person

**Workgroup Deletion**:
- ✅ Deletes all Meetings in Workgroup
- ✅ Cascades to all related entities (Documents, AgendaItems, Tags, MeetingPerson records)
- ✅ Cascades to ActionItems and DecisionItems via AgendaItems

**Meeting Deletion**:
- ✅ Deletes all Documents
- ✅ Deletes all AgendaItems (and their ActionItems, DecisionItems)
- ✅ Deletes all Tags
- ✅ Deletes all MeetingPerson records

---

## Performance Contracts

### Query Performance Targets

- **Query meetings by workgroup**: <2 seconds (SC-001) - via index file lookup
- **Query action items by person**: <3 seconds (SC-002) - via directory scan with filtering
- **Query documents for meeting**: <1 second (SC-003) - via directory scan with filtering
- **Navigate meeting relationships**: <2 seconds per relationship type (SC-007) - via index file lookups

### Data Volume Contracts

- **Current scale**: 120+ meetings
- **Expected scale**: 100s-1000s of meetings
- **Participants per meeting**: 5-15 typical
- **Action items per meeting**: 1-10 typical
- **Decision items per meeting**: 3-10 typical


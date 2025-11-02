# Quick Start: Entity-Based Data Model

**Feature**: Entity-Based Data Model  
**Date**: 2025-11-02  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data Model**: [data-model.md](data-model.md)

## Overview

This guide provides quick start instructions for using the entity-based data model after implementation. The model supports relational queries, entity relationships, and maintains compatibility with existing RAG functionality.

## Prerequisites

- Python 3.11+ installed
- Archive-RAG repository cloned
- Virtual environment activated
- Dependencies installed (including SQLAlchemy for entity storage)

## Setup

### 1. Install Additional Dependencies

```bash
# No additional dependencies needed - uses Python standard library (json, pathlib)

### 2. Initialize Entity Storage

```bash
# Create entity storage directory structure
archive-rag init-entities
```

This creates the entity storage directories (`entities/workgroups/`, `entities/meetings/`, `entities/people/`, etc.) and index files (`entities/_index/`, `entities/_relations/`).

### 3. Migrate Existing Data (if applicable)

```bash
# Migrate existing flat JSON data to entity model
archive-rag migrate-entities --source-url "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" --dry-run

# Review migration preview, then run actual migration
archive-rag migrate-entities --source-url "..." --execute
```

## Basic Usage

### Index Meetings (Entity Model)

```bash
# Index meetings using entity model (from GitHub URL - PRESERVED)
archive-rag index --use-entities "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" indexes/entity-meetings.faiss --no-redact-pii

# Index from local directory (with entity support)
archive-rag index --use-entities data/my-meetings/ indexes/my-index.faiss
```

**Note**: URL ingestion from GitHub is fully preserved. The system will:
1. Fetch JSON array from URL
2. Convert each meeting to entity JSON files
3. Create related entities (Workgroup, Person, Document, etc.)
4. Update index files
5. Proceed with RAG indexing as before

### Query Entity Relationships

```bash
# Query meetings by workgroup
archive-rag query-workgroup "Archives Workgroup"

# Query action items by person
archive-rag query-person "Stephen [QADAO]" --action-items

# Query meetings attended by person
archive-rag query-person "CallyFromAuron" --meetings

# Query documents for meeting
archive-rag query-meeting <meeting-id> --documents
```

### Standard RAG Queries (unchanged)

```bash
# Standard RAG queries continue to work
archive-rag query indexes/entity-meetings.faiss "What decisions were made in the Archives Workgroup?"

# Query with entity context
archive-rag query indexes/entity-meetings.faiss "Who was assigned action items in January 2025?" --use-entity-context
```

## Entity Model Operations

### Create Workgroup

```python
from src.models.workgroup import Workgroup

workgroup = Workgroup(
    id="05ddaaf0-1dde-4d84-a722-f82c8479a8e9",
    name="Archives Workgroup"
)
```

### Create Person

```python
from src.models.person import Person

person = Person(
    id=uuid.uuid4(),
    display_name="Stephen [QADAO]",
    alias="QADAO",
    role="host"
)
```

### Create Meeting with Relationships

```python
from src.models.meeting import Meeting
from src.models.meeting_person import MeetingPerson

meeting = Meeting(
    id=uuid.uuid4(),
    workgroup_id="05ddaaf0-1dde-4d84-a722-f82c8479a8e9",
    date="2025-01-08T00:00:00Z",
    host_id=host_person.id,
    documenter_id=doc_person.id,
    purpose="Regular monthly meeting"
)

# Add participants via junction table
for participant in participants:
    MeetingPerson(
        meeting_id=meeting.id,
        person_id=participant.id,
        role="participant"
    )
```

### Query Relationships

```python
from src.services.entity_query import EntityQueryService

query_service = EntityQueryService()

# Query meetings by workgroup
workgroup_id = "05ddaaf0-1dde-4d84-a722-f82c8479a8e9"
meetings = query_service.get_meetings_by_workgroup(workgroup_id)

# Query action items by person
person_id = query_service.find_person_by_name("Stephen [QADAO]").id
action_items = query_service.get_action_items_by_person(person_id)

# Query meetings attended by person
meetings = query_service.get_meetings_by_person(person_id)  # Via MeetingPerson junction file
```

## Migration from Legacy Format

### Automatic Migration on Ingest

The system automatically detects format and migrates:

```bash
# Legacy format ingested → Auto-migrated to entity model
archive-rag index --use-entities data/legacy-format/ indexes/legacy-migrated.faiss

# New format ingested → Directly stored as entities
archive-rag index --use-entities data/new-format/ indexes/new-format.faiss

# URL ingestion (GitHub) → Auto-converted to entity model
archive-rag index --use-entities "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" indexes/github-entity.faiss
```

**URL Ingestion Flow**:
1. System detects URL and fetches JSON array
2. Each meeting object is parsed and converted to entity JSON files
3. Related entities are created/updated (Workgroup, Person, Document, AgendaItem, ActionItem, DecisionItem, Tag)
4. Index files are updated for fast lookups
5. RAG indexing proceeds as before

### Manual Migration

```bash
# Migrate specific data source
archive-rag migrate-entities \
  --source "https://..." \
  --output-db entities.db \
  --validate
```

## Validation and Testing

### Validate Entity Relationships

```bash
# Check referential integrity
archive-rag validate-entities

# Test cascade delete behaviors
archive-rag test-cascade-delete --person-id <uuid>

# Verify migration completeness
archive-rag verify-migration --source-url "..." --target-dir entities/
```

### Run Tests

```bash
# Test entity models
pytest tests/unit/test_entity_models.py

# Test entity relationships
pytest tests/integration/test_entity_relationships.py

# Test migration
pytest tests/integration/test_entity_migration.py
```

## Common Patterns

### Query Pattern: Find All Meetings for Workgroup

```python
workgroup = session.query(Workgroup).filter_by(name="Archives Workgroup").first()
meetings = session.query(Meeting).filter_by(workgroup_id=workgroup.id).all()
```

### Query Pattern: Find Action Items by Person

```python
person = session.query(Person).filter_by(display_name="Stephen [QADAO]").first()
action_items = session.query(ActionItem).filter_by(assignee_id=person.id).all()
```

### Query Pattern: Navigate Meeting Relationships

```python
meeting = session.query(Meeting).filter_by(id=meeting_id).first()

# Get all participants
participants = [mp.person for mp in meeting.meeting_persons]

# Get all documents
documents = meeting.documents

# Get all agenda items
agenda_items = meeting.agenda_items

# Get all decisions
decisions = []
for agenda_item in agenda_items:
    decisions.extend(agenda_item.decision_items)
```

## Troubleshooting

### Storage Issues

```bash
# Check entity storage directory exists
ls -la entities/

# Verify storage structure
archive-rag entity-info

# Reset entity storage (⚠️ deletes all data)
archive-rag reset-entities
```

### Migration Issues

```bash
# Dry-run migration to preview changes
archive-rag migrate-entities --source "..." --dry-run

# Validate migration results
archive-rag verify-migration --source "..." --target-db entities.db

# Rollback migration
archive-rag rollback-migration --backup-db entities.backup.db
```

### Performance Issues

```bash
# Check query performance
archive-rag query-workgroup "Archives Workgroup" --benchmark

# Analyze slow queries
archive-rag analyze-queries --workgroup-id <uuid>
```

## Next Steps

- See [data-model.md](data-model.md) for detailed entity definitions
- See [plan.md](plan.md) for implementation details
- See [spec.md](spec.md) for full specification and requirements


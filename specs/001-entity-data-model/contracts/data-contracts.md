# Data Contracts: Entity-Based Data Model

**Feature**: Entity-Based Data Model  
**Date**: 2025-11-02

## Entity Data Structures

### Workgroup

```python
{
    "id": "UUID",
    "name": "String",
    "created_at": "DateTime (ISO 8601)",
    "updated_at": "DateTime (ISO 8601)"
}
```

### Person

```python
{
    "id": "UUID",
    "display_name": "String",
    "alias": "String | None",
    "role": "String | None",
    "created_at": "DateTime (ISO 8601)",
    "updated_at": "DateTime (ISO 8601)"
}
```

### Meeting

```python
{
    "id": "UUID",
    "workgroup_id": "UUID",
    "type": "Enum | None",
    "date": "Date (ISO 8601)",
    "host_id": "UUID | None",
    "documenter_id": "UUID | None",
    "purpose": "String | None",
    "video_link": "URL | None",
    "timestamped_video": "Dict | None",
    "no_summary_given": "Boolean (default: False)",
    "canceled_summary": "Boolean (default: False)",
    "created_at": "DateTime (ISO 8601)",
    "updated_at": "DateTime (ISO 8601)"
}
```

### MeetingPerson (Junction Table)

```python
{
    "meeting_id": "UUID",
    "person_id": "UUID",
    "role": "String | None",
    "created_at": "DateTime (ISO 8601)"
}
```

### Document

```python
{
    "id": "UUID",
    "meeting_id": "UUID",
    "title": "String",
    "link": "URL",
    "created_at": "DateTime (ISO 8601)"
}
```

### AgendaItem

```python
{
    "id": "UUID",
    "meeting_id": "UUID",
    "status": "Enum | None",
    "narrative": "String | None",
    "created_at": "DateTime (ISO 8601)"
}
```

### ActionItem

```python
{
    "id": "UUID",
    "agenda_item_id": "UUID",
    "text": "String",
    "assignee_id": "UUID | None",
    "due_date": "Date | None",
    "status": "Enum | None",
    "created_at": "DateTime (ISO 8601)",
    "updated_at": "DateTime (ISO 8601)"
}
```

### DecisionItem

```python
{
    "id": "UUID",
    "agenda_item_id": "UUID",
    "decision": "String",
    "rationale": "String | None",
    "effect": "Enum | None",
    "created_at": "DateTime (ISO 8601)"
}
```

### Tag

```python
{
    "id": "UUID",
    "meeting_id": "UUID",
    "topics_covered": "String | Array | None",
    "emotions": "String | Array | None",
    "created_at": "DateTime (ISO 8601)"
}
```

## Relationship Contracts

### Meeting-Person (Many-to-Many)

**Contract**: Meeting attended by multiple People, Person attends multiple Meetings

**Storage**: MeetingPerson junction table

**Constraints**:
- Composite primary key: (`meeting_id`, `person_id`)
- Foreign keys: `meeting_id` → `meetings.id`, `person_id` → `people.id`
- Cascade delete: Deleting Meeting or Person deletes associated MeetingPerson records

### Workgroup-Meeting (One-to-Many)

**Contract**: Workgroup has many Meetings, Meeting belongs to one Workgroup

**Constraints**:
- Foreign key: `meetings.workgroup_id` → `workgroups.id`
- Cascade delete: Deleting Workgroup deletes all associated Meetings

### Person-ActionItem (One-to-Many)

**Contract**: Person assigned many ActionItems, ActionItem assigned to one Person

**Constraints**:
- Foreign key: `action_items.assignee_id` → `people.id`
- Cascade delete: Deleting Person deletes all associated ActionItems

### Meeting-Document (One-to-Many)

**Contract**: Meeting has many Documents, Document belongs to one Meeting

**Constraints**:
- Foreign key: `documents.meeting_id` → `meetings.id`
- Cascade delete: Deleting Meeting deletes all associated Documents

### Meeting-AgendaItem (One-to-Many)

**Contract**: Meeting has many AgendaItems, AgendaItem belongs to one Meeting

**Constraints**:
- Foreign key: `agenda_items.meeting_id` → `meetings.id`
- Cascade delete: Deleting Meeting deletes all associated AgendaItems

### AgendaItem-ActionItem (One-to-Many)

**Contract**: AgendaItem has many ActionItems, ActionItem belongs to one AgendaItem

**Constraints**:
- Foreign key: `action_items.agenda_item_id` → `agenda_items.id`
- Cascade delete: Deleting AgendaItem deletes all associated ActionItems

### AgendaItem-DecisionItem (One-to-Many)

**Contract**: AgendaItem has many DecisionItems, DecisionItem belongs to one AgendaItem

**Constraints**:
- Foreign key: `decision_items.agenda_item_id` → `agenda_items.id`
- Cascade delete: Deleting AgendaItem deletes all associated DecisionItems

### Meeting-Tag (One-to-Many)

**Contract**: Meeting has many Tags, Tag belongs to one Meeting

**Constraints**:
- Foreign key: `tags.meeting_id` → `meetings.id`
- Cascade delete: Deleting Meeting deletes all associated Tags

## Validation Contracts

### Required Field Validation

**Workgroup**:
- ✅ `name` required, must not be empty

**Person**:
- ✅ `display_name` required, must not be empty

**Meeting**:
- ✅ `workgroup_id` required, must reference existing Workgroup
- ✅ `date` required, must be valid ISO 8601 date
- ✅ **At least one participant required** (via MeetingPerson relationship)

**Document**:
- ✅ `meeting_id` required, must reference existing Meeting
- ✅ `title` required, must not be empty
- ✅ `link` required, must be valid URL format

**AgendaItem**:
- ✅ `meeting_id` required, must reference existing Meeting
- ✅ **Can exist without ActionItems or DecisionItems** (empty agenda items valid)

**ActionItem**:
- ✅ `agenda_item_id` required, must reference existing AgendaItem
- ✅ `text` required, must not be empty
- ✅ `assignee_id` optional, if provided must reference existing Person

**DecisionItem**:
- ✅ `agenda_item_id` required, must reference existing AgendaItem
- ✅ `decision` required, must not be empty

**Tag**:
- ✅ `meeting_id` required, must reference existing Meeting

### Referential Integrity Contracts

**Foreign Key Constraints**:
- ✅ All foreign keys must reference existing entities
- ✅ Cascade delete behaviors enforced (see Cascade Delete Contracts)
- ✅ NULL foreign keys allowed only where specified (e.g., `assignee_id`, `host_id`)

**Cascade Delete Contracts**:
- ✅ Person deletion → Cascade delete ActionItems, MeetingPerson records
- ✅ Workgroup deletion → Cascade delete Meetings and all related entities
- ✅ Meeting deletion → Cascade delete Documents, AgendaItems, Tags, MeetingPerson records
- ✅ AgendaItem deletion → Cascade delete ActionItems, DecisionItems

## Query Response Contracts

### Query Meetings by Workgroup

**Response Format**:
```json
{
    "workgroup": {
        "id": "UUID",
        "name": "String"
    },
    "meetings": [
        {
            "id": "UUID",
            "date": "Date (ISO 8601)",
            "type": "Enum | None",
            "purpose": "String | None"
        }
    ],
    "total": 5,
    "query_time_seconds": 0.5
}
```

### Query Action Items by Person

**Response Format**:
```json
{
    "person": {
        "id": "UUID",
        "display_name": "String"
    },
    "action_items": [
        {
            "id": "UUID",
            "text": "String",
            "due_date": "Date | None",
            "status": "Enum | None",
            "meeting_id": "UUID",
            "meeting_date": "Date (ISO 8601)"
        }
    ],
    "total": 12,
    "query_time_seconds": 0.8
}
```

### Query Meeting Details

**Response Format**:
```json
{
    "meeting": {
        "id": "UUID",
        "date": "Date (ISO 8601)",
        "workgroup": {
            "id": "UUID",
            "name": "String"
        },
        "participants": [
            {
                "id": "UUID",
                "display_name": "String",
                "role": "String | None"
            }
        ],
        "documents": [...],
        "agenda_items": [...],
        "tags": [...]
    }
}
```







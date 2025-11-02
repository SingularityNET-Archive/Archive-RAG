# Research: Entity-Based Data Model

**Feature**: Entity-Based Data Model  
**Date**: 2025-11-02  
**Purpose**: Resolve technical decisions for relational entity model implementation

## Key Research Questions

### 1. Storage Backend: JSON Files vs Relational Database

**Decision Required**: Choose storage backend for entity relationships

**Research Context**: 
- Current system: Flat JSON files + FAISS index for embeddings
- Requirement: Relational entity model with foreign keys, cascade deletes, many-to-many relationships
- Constraints: Python-only, local-first, no external API dependency, user preference for JSON files

**Decision**: **JSON File Storage with Directory-Based Organization**

**Rationale**: 
- JSON file storage provides:
  - Native Python support (json standard library)
  - Local file-based storage (no server required)
  - Simple migration path (direct from existing JSON format)
  - Easy to version control and audit
  - Human-readable for debugging
  - Compatible with existing FAISS index workflow
  - File-based relationships via directory structure and foreign key references
  - Referential integrity enforced through validation logic
- Directory structure enables:
  - Organized entity storage (`entities/workgroups/`, `entities/meetings/`, etc.)
  - Index files for fast lookups (workgroup index, person index, etc.)
  - Relationship files for many-to-many (meeting_person.json)
  - Simple query patterns via file reads and filtering
- Performance considerations:
  - Index files for O(1) lookups by ID
  - Directory-based organization for efficient filtering
  - Batch operations for cascade deletes
  - Within SC performance targets for 100s-1000s of meetings

**Alternatives Considered**:
1. **JSON Files** ✅ Selected - Best fit for user preference, existing codebase, local-first, simple relationships
2. **SQLite** ❌ Rejected - User preference against SQL databases
3. **PostgreSQL** ❌ Rejected - User preference against SQL databases, requires server
4. **Neo4j** ❌ Rejected - External dependency, more complex, unnecessary for current scale
5. **MongoDB** ❌ Rejected - External dependency, user preference for JSON files

### 2. JSON File Organization and Query Layer

**Decision Required**: Choose file organization pattern and query abstraction

**Research Context**:
- Existing codebase uses Pydantic for validation
- Need for type-safe queries and relationship navigation
- Python-only constraint
- JSON file storage (no database)

**Decision**: **Directory-Based JSON Storage with Pydantic Models and File-Based Query Layer**

**Rationale**:
- Directory structure provides:
  - Organized entity storage (`entities/workgroups/{id}.json`, `entities/meetings/{id}.json`, etc.)
  - Index files for fast lookups (`entities/_index/workgroups.json`, `entities/_index/meetings.json`)
  - Relationship files for many-to-many (`entities/_relations/meeting_person.json`)
  - Simple query patterns via file reads and filtering
- Pydantic models for:
  - Validation layer (business logic)
  - Type-safe entity handling
  - Serialization/deserialization
- File-based query layer provides:
  - Simple read/write operations
  - Relationship navigation via foreign key references
  - Cascade delete via file deletion operations
  - Referential integrity via validation before write operations
- Hybrid approach:
  - Pydantic for validation and business logic
  - File operations for persistence (json.dump/json.load)
  - Index files for fast lookups
  - Clear separation of concerns

**Alternatives Considered**:
1. **Directory-Based JSON + Pydantic** ✅ Selected - Type-safe, file-based, simple, aligns with user preference
2. **Single JSON File per Entity Type** - Simpler but slower for large datasets
3. **Nested JSON (all entities in one file)** - Easy to load but poor performance for updates
4. **JSON Lines (one entity per line)** - Good for streaming but more complex
5. **Database ORM** ❌ Rejected - User preference against SQL databases

### 3. Migration Strategy: Incremental vs Big Bang

**Decision Required**: How to migrate existing flat JSON data to entity model

**Research Context**:
- Current: 120+ meetings in flat JSON format from GitHub URL
- Existing FAISS indexes must continue to function
- Requirement: 100% data preservation (SC-010)
- Backward compatibility for read operations
- JSON file storage preference

**Decision**: **Incremental Dual-Mode Migration with JSON File Structure**

**Rationale**:
- Phase 1: Support both formats during transition
  - Entity model stored as JSON files in `entities/` directory structure
  - Legacy MeetingRecord for backward compatibility
  - Migration script converts flat JSON → entity JSON files on ingest
  - **URL ingestion preserved**: `ingest_meeting_url()` continues to work, fetches JSON array from URLs (e.g., GitHub), converts to entity JSON files
- Phase 2: Migrate existing indexes
  - Re-index using entity JSON files
  - Maintain old indexes until validation complete
- Phase 3: Deprecate legacy format
  - Remove legacy ingestion after validation
  - Keep migration script for emergency rollback
- JSON file structure:
  - `entities/workgroups/{id}.json` - Individual workgroup files
  - `entities/meetings/{id}.json` - Individual meeting files
  - `entities/people/{id}.json` - Individual person files
  - `entities/_index/` - Index files for fast lookups
  - `entities/_relations/` - Relationship files (e.g., `meeting_person.json`)
- **URL Ingestion Flow**:
  1. `ingest_meeting_directory(url)` detects URL and calls `ingest_meeting_url(url)`
  2. `ingest_meeting_url()` fetches JSON array from URL (e.g., `https://raw.githubusercontent.com/.../meeting-summaries-array.json`)
  3. Each meeting object in array is parsed as `MeetingRecord`
  4. `MeetingRecord` is converted to entity JSON files via `entity_storage.save_meeting_entity()`
  5. Related entities (Workgroup, Person, Document, etc.) are created/updated
  6. Index files are updated with new relationships
- Benefits:
  - No database dependency
  - Human-readable for debugging
  - Version control friendly
  - **URL ingestion from GitHub source preserved**
  - Validation at each step
  - Rollback capability
  - Zero data loss

**Alternatives Considered**:
1. **Incremental Dual-Mode with JSON** ✅ Selected - Safe, validated, rollback-capable, aligns with user preference
2. **Big Bang Migration** ❌ Rejected - High risk, no validation, difficult rollback
3. **Read-Only Legacy** - Keeps old format read-only, new format for writes
4. **One-Time Conversion** - Single migration script, no dual-mode

### 4. Junction File Implementation for Meeting-Person

**Decision Required**: Implementation pattern for many-to-many relationship

**Research Context**:
- Meeting-Person relationship is many-to-many
- Need bidirectional queries (meetings per person, people per meeting)
- Performance targets: <2 seconds per query type (SC-007)
- JSON file storage constraint

**Decision**: **Explicit Junction File with Index-Based Queries**

**Rationale**:
- Explicit `meeting_person.json` junction file provides:
  - Clear relationship storage as JSON array of `{meeting_id, person_id, role}` records
  - Cascade delete support via file updates (if meeting deleted, remove junction records)
  - Optional metadata storage (role, attendance status)
  - Index files for performance (`_index/meeting_person_by_meeting.json`, `_index/meeting_person_by_person.json`)
- File-based query pattern enables:
  - Bidirectional queries via indexed lookups
  - Fast filtering using pre-built indexes
  - Type safety via Pydantic models
- Performance:
  - Indexed lookups ensure fast queries (O(1) or O(log n) with binary search)
  - Batch operations for list operations
  - Within <2 second targets for typical data volumes (100s-1000s of meetings)

**Alternatives Considered**:
1. **Explicit Junction File + Indexes** ✅ Selected - Clear, performant, metadata-capable, JSON-based
2. **Embedded Arrays in Meeting JSON** ❌ Rejected - Poor queryability, duplicates person data
3. **Embedded Arrays in Person JSON** ❌ Rejected - Poor queryability, duplicates meeting data
4. **Single Junction File without Indexes** ❌ Rejected - O(n) queries, slow for large datasets
5. **Database Junction Table** ❌ Rejected - User preference against SQL databases

### 5. Transaction Boundaries and Error Handling (JSON Files)

**Decision Required**: How to handle cascade deletes and atomic operations with JSON files

**Research Context**:
- Cascade delete requirements (FR-021, FR-022)
- Need for atomic operations (delete person → delete action items)
- Error handling when operations fail
- JSON file storage (no database transactions)

**Decision**: **File-Based Atomic Operations with Backup/Restore Pattern**

**Rationale**:
- File-based atomic operations provide:
  - Atomic writes via temporary files + rename pattern (atomic on most filesystems)
  - Consistency via validation before write operations
  - Error handling with backup/restore on failures
  - Audit logging for cascade operations
- Explicit cascade logic:
  - Business logic validates before delete
  - Audit logging for cascade operations
  - Backup files before destructive operations
  - Restore from backup on error
  - Clear error messages for users
- Pattern:
  ```python
  # Backup affected files
  backup_files = backup_entity_and_children(entity_id)
  try:
      # Validate references
      # Log cascade operations
      # Delete child entity files
      # Delete parent entity file
      # Update relationship files
      # Update index files
  except Exception:
      # Restore from backup
      restore_files(backup_files)
      raise
  ```

**Alternatives Considered**:
1. **File-Based Atomic + Backup/Restore** ✅ Selected - Safe, auditable, recoverable, JSON-compatible
2. **Simple File Delete** ❌ Rejected - Data corruption risk on failures
3. **Database Transactions** ❌ Rejected - User preference against SQL databases
4. **Event Sourcing** - Overkill for current needs

## Implementation Patterns

### Entity Model Structure

```python
# Base entity pattern
class BaseEntity(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime

# Relationship pattern
class MeetingPerson(BaseModel):
    meeting_id: UUID (FK → Meeting)
    person_id: UUID (FK → Person)
    role: Optional[str]
    created_at: datetime

# File storage pattern
# entities/workgroups/{id}.json
# entities/meetings/{id}.json
# entities/people/{id}.json
# entities/_relations/meeting_person.json
# entities/_index/workgroups.json
```

### Query Patterns

```python
# Bidirectional queries via index files
# Person → Meetings
person_meetings = load_index("meeting_person_by_person", person.id)
meetings = [load_meeting(mid) for mid in person_meetings]

# Meeting → People
meeting_people = load_index("meeting_person_by_meeting", meeting.id)
people = [load_person(pid) for pid in meeting_people]

# Workgroup → Meetings
workgroup_meetings = load_index("meetings_by_workgroup", workgroup.id)
meetings = [load_meeting(mid) for mid in workgroup_meetings]
```

### Migration Pattern

```python
# Dual-mode ingestion with JSON storage
def ingest_meeting(data):
    if is_legacy_format(data):
        meeting_record = MeetingRecord(**data)  # Legacy
        migrate_to_entity_json(meeting_record)  # Convert to entity JSON files
    else:
        create_entity_json(data)  # New format, store as JSON files
```

## Validation

- ✅ All technical decisions align with constitution (Python-only, local-first)
- ✅ Performance targets achievable (SC-001 through SC-007)
- ✅ Migration strategy preserves 100% data (SC-010)
- ✅ Referential integrity maintained (SC-004)
- ✅ Backward compatibility supported during transition

## References

- Python JSON Documentation: https://docs.python.org/3/library/json.html
- Pydantic Models: https://docs.pydantic.dev/
- File-Based Data Storage Patterns: Directory organization for entity storage
- Migration Best Practices: Incremental migration with validation


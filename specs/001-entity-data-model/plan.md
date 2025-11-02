# Implementation Plan: Entity-Based Data Model

**Branch**: `001-entity-data-model` | **Date**: 2025-11-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-entity-data-model/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Refactor the Archive-RAG data model from a flat JSON structure to a relational entity-based model supporting Workgroup, Meeting, Person, Document, AgendaItem, ActionItem, DecisionItem, and Tag entities with proper relationships, referential integrity, and cascade delete behaviors. Maintain compatibility with existing RAG embedding and querying systems while enabling graph-based relationship navigation.

**Research Decisions** (from research.md):
- **Storage**: JSON files with directory-based organization (entities/workgroups/, entities/meetings/, etc.)
- **Query Layer**: File-based query layer with index files for fast lookups
- **Migration**: Incremental dual-mode migration with validation
- **Junction File**: Explicit MeetingPerson junction file (meeting_person.json) with index files
- **Atomic Operations**: File-based atomic operations with backup/restore pattern

## Technical Context

**Language/Version**: Python 3.11+ (tested with Python 3.11, 3.12, 3.13)

**Primary Dependencies**: 
- Pydantic 2.x (data validation and models) - existing
- json (standard library, for entity storage) - existing
- pathlib (standard library, for file operations) - existing
- Existing dependencies: sentence-transformers, faiss-cpu, structlog, typer, spacy, gensim

**Storage**: 
- Current: FAISS index + JSON metadata files
- Proposed: **JSON files with directory-based organization** (entities/workgroups/, entities/meetings/, entities/people/, etc.)
- Decision: JSON files provide local-first, Python-only solution with human-readable storage, easy version control, and simple migration path
- Rationale: No external dependency, excellent performance for 100s-1000s of meetings, easy migration path

**Testing**: pytest, pytest-cov (existing test framework)

**Target Platform**: Python CLI application (cross-platform: Linux, macOS, Windows)

**Project Type**: single (existing CLI application structure)

**Performance Goals**: 
- Query meetings by workgroup: <2 seconds (SC-001)
- Retrieve action items by person: <3 seconds (SC-002)
- Access documents for meeting: <1 second (SC-003)
- Navigate meeting relationships: <2 seconds per relationship type (SC-007)
- Maintain compatibility with existing RAG query performance

**Constraints**: 
- Python-only (constitution requirement)
- Local embeddings + FAISS (constitution requirement)
- No external API dependency for core (constitution requirement)
- Must preserve backward compatibility for read operations during migration
- Must support both relational queries and vector similarity search
- **Must preserve URL ingestion**: Continue to support ingestion from GitHub URL (`https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json`)

**Scale/Scope**: 
- Current: 120+ meetings from GitHub source
- Expected: 100s-1000s of meetings across multiple workgroups
- Multiple workgroups (Archives, Governance, Education, African Guild, etc.)
- Multiple people per meeting (typically 5-15 participants)
- 100s-1000s of documents, action items, decision items

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with Archive-RAG Constitution principles:

- ✅ **I. Truth-Bound Intelligence**: All outputs grounded in archived meeting data with traceable sources? **YES** - Entity model preserves meeting data and adds relationship navigation without changing RAG grounding.
- ✅ **II. Evidence & Citation First**: Required citation format `[meeting_id | date | speaker]` supported? **YES** - Entity model maintains meeting_id, date, and speaker (person) relationships for citation extraction.
- ✅ **III. Reproducibility & Determinism**: Version-locked embeddings, deterministic seeds, reproducible inference? **YES** - Data model refactoring does not change embedding or inference logic; deterministic behavior preserved.
- ✅ **IV. Test-First Governance**: Benchmark suite, retrieval accuracy, citation validity, factuality checks included? **YES** - Existing test framework will validate new data model structure; migration validation tests required.
- ✅ **V. Auditability & Transparency**: Immutable logs, audit records, traceable topic/entity extraction implemented? **YES** - Entity relationships enhance traceability; existing audit logging continues to function.
- ✅ **Additional Constraints**: 
  - ✅ Python-only? **YES** - Implementation in Python
  - ✅ Local embeddings + FAISS? **YES** - FAISS index preserved; entity model supports extraction from decision items
  - ✅ No external API dependency for core? **YES** - Relational storage can be local SQLite or local graph DB
  - ✅ SHA-256 hashing for tamper detection? **YES** - Continue existing hashing approach
  - ✅ PII redaction? **YES** - Existing PII detection/redaction continues
  - ✅ Bounded retrieval latency? **YES** - Success criteria specify performance targets (<2-3 seconds)
  - ✅ Safe degradation? **YES** - Migration preserves data; validation prevents invalid states
  - ✅ Explainability? **YES** - Entity relationships improve traceability of sources

**Constitution Compliance**: ✅ **PASS** - All principles satisfied. Entity model enhances rather than violates constitution requirements.

## Project Structure

### Documentation (this feature)

```text
specs/001-entity-data-model/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── models/              # Data models
│   ├── meeting_record.py    # Legacy MeetingRecord (backward compatibility)
│   ├── workgroup.py         # New: Workgroup entity
│   ├── meeting.py           # New: Meeting entity
│   ├── person.py           # New: Person entity
│   ├── document.py         # New: Document entity
│   ├── agenda_item.py      # New: AgendaItem entity
│   ├── action_item.py      # New: ActionItem entity
│   ├── decision_item.py    # New: DecisionItem entity
│   ├── tag.py             # New: Tag entity
│   └── meeting_person.py  # New: Junction entity for many-to-many relationship
├── services/
│   ├── ingestion.py       # Update: Preserve URL ingestion, add entity conversion
│   ├── chunking.py        # Update: Extract from decision items via entities
│   ├── embedding.py       # No changes (uses extracted transcript)
│   ├── retrieval.py       # Update: Support entity-based queries
│   ├── rag_generator.py   # No changes (uses chunks)
│   ├── migration.py       # New: Migration from flat JSON to entity model
│   ├── entity_storage.py  # New: JSON file-based entity storage operations
│   └── entity_query.py    # New: Query layer for entity relationships
├── cli/
│   ├── index.py           # Update: Support entity-based indexing
│   ├── query.py           # Update: Support entity-based queries
│   └── migrate.py         # New: Migration command
└── lib/
    ├── config.py          # Update: Add entity storage configuration (directory paths)
    └── validation.py      # Update: Add entity validation rules

tests/
├── contract/
│   ├── test_index_command.py  # Update: Test entity-based indexing
│   └── test_query_command.py  # Update: Test entity-based queries
├── integration/
│   ├── test_entity_migration.py  # New: Test migration from flat to entity model
│   └── test_entity_relationships.py  # New: Test cascade deletes, relationships
└── unit/
    ├── test_entity_models.py      # New: Test entity validation
    └── test_entity_queries.py     # New: Test query operations
```

**Structure Decision**: Single project structure maintained. New entity models added to `src/models/`, entity storage service (`entity_storage.py`) and query service (`entity_query.py`) added for JSON file operations, migration service added, existing services updated to work with entities. **URL ingestion preserved**: `ingestion.py` continues to support GitHub URL ingestion, with entity conversion added after MeetingRecord parsing. Test coverage expanded for entity model validation and migration.

**URL Ingestion Preservation**: See [INGESTION_PRESERVATION.md](INGESTION_PRESERVATION.md) for details on preserving GitHub URL ingestion (`https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json`).

**Storage Structure**:
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
│   ├── workgroups.json
│   ├── meetings_by_workgroup.json
│   ├── meeting_person_by_meeting.json
│   └── meeting_person_by_person.json
└── _relations/
    └── meeting_person.json
```

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations. Entity model enhances existing system without introducing external dependencies or violating Python-only, local-first principles.

# Implementation Plan: Refine Entity Extraction

**Branch**: `004-refine-entity-extraction` | **Date**: 2025-01-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-refine-entity-extraction/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Refine entity extraction from source JSON to treat JSON objects as candidate entities, extract fields representing nouns/real-world objects, capture entity relationships (Workgroup→Meeting, Meeting→People, Meeting→Decisions, ActionItem→Assignee, Decision→Effect), apply Named Entity Recognition (NER) to text fields, normalize entity references to avoid splits (e.g., "Stephen" and "Stephen [QADAO]" → canonical "Stephen"), and chunk text by semantic unit before embedding. Technical approach: Enhance existing entity extraction service with NER integration (spaCy), entity normalization algorithms (pattern matching + similarity), relationship triple generation, and semantic chunking by JSON structure boundaries.

## Technical Context

**Language/Version**: Python 3.11+ (aligned with existing project requirements, tested with Python 3.11, 3.12, 3.13)

**Primary Dependencies**: 
- Existing: `spacy>=3.6.0` (NER), `pydantic>=2.0.0` (data validation), `sentence-transformers>=2.2.0` (embeddings), `faiss-cpu>=1.7.4` (vector storage)
- New/enhanced: `rapidfuzz>=3.0.0` (entity name similarity matching), `re` (standard library for pattern-based normalization)
- Integration with existing services: `EntityExtractionService`, `EntityStorage`, `MeetingToEntity` conversion

**Storage**: 
- Existing: Local JSON files in `entities/` directory structure (workgroups, meetings, people, documents, agenda items, action items, decision items)
- New: Relationship triples embedded in entity JSON files (existing pattern), generated on-demand for output
- Chunk metadata embedded in chunk JSON structure (entities, relationships, normalized references)

**Testing**: `pytest>=7.4.0`, `pytest-cov>=4.1.0` (existing test framework)

**Target Platform**: Python CLI application (cross-platform: Linux, macOS, Windows)

**Project Type**: single (extends existing Archive-RAG codebase)

**Performance Goals**: 
- Process meeting records with entity extraction and normalization in <2 seconds per meeting record (target for batch processing)
- NER processing typically <100ms per text field (spaCy is fast)
- Total processing time for 120 meetings: ~4 minutes (acceptable for batch ingestion)

**Constraints**: 
- Must maintain determinism (same meeting record produces identical entity structure)
- Must preserve traceability to source meeting records
- Must comply with Archive-RAG Constitution (Python-only, local storage, no external DB dependencies)

**Scale/Scope**: 
- Process 120+ existing meeting records
- Extract entities from all meeting records (workgroups, meetings, people, documents, decisions, action items)
- Normalize entity name variations across all records
- Generate relationship triples for all entity relationships
- Create semantic chunks for embedding generation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with Archive-RAG Constitution principles:

- **I. Truth-Bound Intelligence**: All outputs grounded in archived meeting data with traceable sources?
- **II. Evidence & Citation First**: Required citation format `[meeting_id | date | speaker]` supported?
- **III. Reproducibility & Determinism**: Version-locked embeddings, deterministic seeds, reproducible inference?
- **IV. Test-First Governance**: Benchmark suite, retrieval accuracy, citation validity, factuality checks included?
- **V. Auditability & Transparency**: Immutable logs, audit records, traceable topic/entity extraction implemented?
- **Additional Constraints**: 
  - Python-only? **YES** - Implementation in Python
  - Remote embeddings allowed? **YES** - Remote embeddings via API endpoints are permitted but optional (local fallback required)
  - Remote LLM inference allowed? **YES** - Remote LLM via API endpoints are permitted but optional (local fallback required)
  - FAISS storage local? **YES** - FAISS vector storage remains local for performance and determinism
  - Entity storage local? **YES** - Entity storage uses local JSON files (no external database dependencies)
  - Structured data extraction? **YES** - Entity extraction preserves traceability, maintains referential integrity, supports dual querying (structured + vector search)
  - SHA-256 hashing for tamper detection? **YES** - Existing functionality preserved
  - PII redaction? **YES** - Existing PII detection and redaction preserved
  - Bounded retrieval latency? **YES** - Entity extraction should not significantly impact ingestion performance
  - Safe degradation? **YES** - Missing entity fields handled gracefully (FR-016)
  - Explainability? **YES** - Entity extraction traceable to source meeting records

**Constitution Compliance**: ✅ **PASS** - All requirements met. No violations detected.

Flag any violations in Complexity Tracking section below.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: Option 1: Single project structure - extends existing Archive-RAG codebase. New functionality will be added to:
- `src/services/` - Enhanced entity extraction service, new normalization service, relationship triple generator, semantic chunking service
- `src/models/` - Data models for relationship triples, chunk metadata
- `src/cli/` - CLI commands for entity extraction refinement (if needed)
- `src/lib/` - Utility functions for entity normalization, similarity matching
- `tests/` - Unit and integration tests for new services

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - all implementation follows Archive-RAG Constitution principles.

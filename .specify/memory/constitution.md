<!--
  Sync Impact Report:
  
  Version change: 2.2.0 → 2.3.0 (MINOR: Added Structured Data & Entity Discipline section)
  
  Modified principles:
    - V. Auditability & Transparency: Enhanced entity extraction guidance to reflect structured entity model
    - Technology Discipline: Added entity storage requirements (local JSON files, no external database dependencies)
  
  Added sections:
    - Structured Data & Entity Discipline (new section under Additional Constraints)
  
  Removed sections: None
  
  Templates requiring updates:
    ✅ plan-template.md (constitution check section should reference entity discipline for data model features)
    ✅ spec-template.md (no direct constitution references, compatible)
    ✅ tasks-template.md (no direct constitution references, compatible)
    ✅ checklist-template.md (no direct constitution references, compatible)
  
  Documentation requiring updates:
    ✅ README.md (entity extraction section already documents local JSON storage and entity model)
  
  Follow-up TODOs: None
-->

# Archive-RAG Constitution

## Core Principles

### I. Truth-Bound Intelligence

The system must ground all outputs strictly in archived meeting data.

- No hallucination beyond retrieved context
- Every factual claim must have a traceable source inside the archive
- Archived text is the highest authority; the model is a reader, not a narrator

### II. Evidence & Citation First

Every generated statement shall be supported by verifiable citation.

- Required format: [meeting_id | date | speaker]
- Each answer includes retrieved text + provenance metadata
- Citations are non-optional, non-negotiable

### III. Reproducibility & Determinism

Behavior must be repeatable under fixed configuration.

- Version-locked embeddings and model
- Deterministic seeds and FAISS index
- Inference must reproduce identical output on same input + data state

### IV. Test-First Governance

Evaluation precedes deployment.

- Benchmark suite maintained and versioned
- Changes must pass: retrieval accuracy, citation validity, and factuality checks
- Regression tests guard against hallucination creep

### V. Auditability & Transparency

All actions must be visible and reviewable.

- Immutable logs: query, retrieved sources, model version, output
- Every run produces an audit record
- Topic/entity extraction is advisory and traceable, never authoritative
- Entity extraction and structured data relationships must be traceable to source meeting records

## Additional Constraints

### Responsible Data & Privacy Discipline

- Only approved meeting JSON data may be ingested
- **Single Data Source**: All meeting data MUST be sourced exclusively from: `https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json`
- SHA-256 hashing for tamper detection
- Personal private information must be flagged and redacted
- Topic modeling & entity extraction must not infer missing personal data

### Technology Discipline

- Python-only execution environment
- **Remote embeddings allowed** for memory-efficient processing (embeddings via API endpoints are permitted but optional)
- Remote LLM inference allowed for memory-efficient processing (LLM via API endpoints are permitted but optional)
- Remote processing MUST be configured via environment variables when used (API URLs and keys)
- Local fallback for embeddings and LLM inference MUST be available when remote processing is not configured
- FAISS vector storage remains local for performance and determinism
- Entity storage MUST use local JSON files (no external database dependencies)
- CLI support for all major pipeline stages

### Structured Data & Entity Discipline

- System MUST extract structured entities from meeting records (meetings, workgroups, people, documents, agenda items, decision items, action items)
- Entity storage MUST be local-first: JSON files in `entities/` directory structure (no external database dependencies)
- Entity relationships MUST maintain referential integrity (foreign key validation, cascade delete behaviors)
- Entity extraction MUST preserve traceability to source meeting records (meeting_id, date, speaker relationships)
- System MUST support dual querying: structured entity queries (quantitative counts, relationship navigation) AND vector similarity search (qualitative RAG queries)
- Entity extraction MUST be deterministic: same meeting record produces identical entity structure and relationships
- Entity storage operations MUST be atomic (temporary file + rename pattern for writes, backup/restore for deletes)

### Performance & Reliability

- Retrieval latency should remain bounded
- Model must degrade safely—no silent failure or silent hallucination
- Explainability required for every output

## Governance

This constitution supersedes all other practices and conventions. Amendments require:

1. **Documentation**: Clear rationale for the change, impact assessment, and migration plan
2. **Versioning**: Semantic versioning (MAJOR.MINOR.PATCH) where:
   - MAJOR: Backward incompatible governance/principle removals or redefinitions
   - MINOR: New principle/section added or materially expanded guidance
   - PATCH: Clarifications, wording, typo fixes, non-semantic refinements
3. **Compliance Review**: All PRs and reviews must verify compliance with these principles
4. **Complexity Justification**: Any violations of simplicity or determinism principles must be documented and justified

All development work must align with these principles. When conflicts arise between practices, the constitution takes precedence.

**Version**: 2.3.0 | **Ratified**: 2025-11-02 | **Last Amended**: 2025-11-03
<!--
  Sync Impact Report:
  
  Version change: 1.1.0 → 2.0.0 (MAJOR: Removed local processing, remote-only allowed)
  
  Modified principles:
    - Technology Discipline: Changed from local-first with opt-in remote to remote-only requirement
  
  Added sections: None
  
  Removed sections:
    - Technology Discipline: Local embeddings + FAISS storage option removed
    - Technology Discipline: Automatic fallback to local processing requirement removed
    - Technology Discipline: Local-first principle removed
    - Technology Discipline: "No external API dependency for core functionality by default" removed
  
  Templates requiring updates:
    ⚠️ plan-template.md (constitution check section needs update - local processing references removed)
    ✅ spec-template.md (no direct constitution references, compatible)
    ✅ tasks-template.md (no direct constitution references, compatible)
    ✅ checklist-template.md (no direct constitution references, compatible)
  
  Documentation requiring updates:
    ⚠️ REMOTE_PROCESSING.md (update to reflect remote-only requirement)
    ⚠️ REMOTE_SETUP_QUICKSTART.md (update to reflect remote-only requirement)
    ⚠️ Code references: src/services/embedding.py, src/services/rag_generator.py (remove local fallback logic)
  
  Follow-up TODOs:
    - Update all documentation to reflect remote-only requirement
    - Remove local processing code paths (fallback logic)
    - Update migration guide for users currently using local processing
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

## Additional Constraints

### Responsible Data & Privacy Discipline

- Only approved meeting JSON data may be ingested
- SHA-256 hashing for tamper detection
- Personal private information must be flagged and redacted
- Topic modeling & entity extraction must not infer missing personal data

### Technology Discipline

- Python-only execution environment
- **Remote model connections required** for memory-efficient processing (embeddings and LLM inference via API endpoints)
- Remote processing MUST be configured via environment variables (API URLs and keys)
- FAISS vector storage remains local for performance and determinism
- CLI support for all major pipeline stages

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

**Version**: 2.0.0 | **Ratified**: 2025-11-02 | **Last Amended**: 2025-11-02
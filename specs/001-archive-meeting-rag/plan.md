# Implementation Plan: Archive Meeting Retrieval & Grounded Interpretation RAG

**Branch**: `001-archive-meeting-rag` | **Date**: 2025-11-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-archive-meeting-rag/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a Python-only, audit-friendly RAG pipeline to interpret archived meeting JSON logs with evidence-bound answers, verifiable citations, offline reproducibility, and human auditability. Technical approach: local embedding models (sentence-transformers) + FAISS vector database for retrieval, deterministic inference (transformers or llama.cpp), comprehensive query audit logging, topic modeling (gensim/BERTopic-lite) + entity extraction (spaCy), and benchmark scoring harness for evaluation.

## Technical Context

**Language/Version**: Python 3.11 (locked)

**Primary Dependencies**:
- Embeddings: sentence-transformers (local model)
- Vector DB: faiss
- Model runtime: transformers or llama.cpp (local execution)
- Topic modeling: gensim or BERTopic-lite (local)
- Entity extraction: spaCy (local)
- CLI: typer
- Logging: structlog / JSON logs
- Hashing: hashlib

**Storage**:
- JSON input files (meeting archives)
- Local FAISS index
- Local audit logs directory

**Testing**: pytest, deterministic seeds, golden file tests for citations

**Target Platform**: Linux/macOS CLI (air-gap friendly)

**Project Type**: Single Python project, CLI-focused

**Performance Goals**:
- <2s retrieval for 10k docs
- 100% reproducible answers given same data & seed

**Constraints**:
- Offline-capable, no external inference calls
- No cloud or hosted vector DB
- Tamper detection required via SHA-256
- Bounded memory (<4GB RAM use target)

**Scale/Scope**:
- Up to 100k meeting docs in first milestone
- Multi-year internal governance data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with Archive-RAG Constitution principles:

- ✅ **I. Truth-Bound Intelligence**: All outputs grounded in archived meeting data with traceable sources
  - Design: RAG architecture enforces retrieval-first; local LLM generates only from retrieved context
  - Audit: Query logs capture retrieved sources for every answer

- ✅ **II. Evidence & Citation First**: Required citation format `[meeting_id | date | speaker]` supported
  - Design: Citation extraction from meeting metadata; format enforced in response generation
  - Audit: Citations stored in query logs and returned with every answer

- ✅ **III. Reproducibility & Determinism**: Version-locked embeddings, deterministic seeds, reproducible inference
  - Design: Model versions pinned; deterministic seeds for embeddings and inference; FAISS index versioned
  - Audit: Version tracking in audit logs and index metadata

- ✅ **IV. Test-First Governance**: Benchmark suite, retrieval accuracy, citation validity, factuality checks included
  - Design: Evaluation harness with benchmark questions; scoring script validates citations and factuality
  - Audit: Golden file tests ensure regression detection

- ✅ **V. Auditability & Transparency**: Immutable logs, audit records, traceable topic/entity extraction implemented
  - Design: Structured JSON logs (structlog); every query produces immutable audit record; topic/entity extraction logged but marked advisory
  - Audit: Logs include query, retrieved sources, model version, output, user ID (from SSO)

- ✅ **Additional Constraints**: 
  - ✅ Python-only execution environment (Python 3.11)
  - ✅ Local embeddings + FAISS storage (no external vector DB)
  - ✅ No external API dependency for core functionality (local models only)
  - ✅ SHA-256 hashing for tamper detection (hashlib)
  - ✅ PII redaction in topic/entity extraction
  - ✅ Bounded retrieval latency (<2s target)
  - ✅ Safe degradation ("no evidence found" response)
  - ✅ Explainability (citations + retrieved text in every output)

**Status**: All constitution principles satisfied. No violations detected.

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

```text
src/
├── models/              # Data models: MeetingRecord, RAGQuery, EmbeddingIndex, EvaluationCase
├── services/            # Core services: embedding, retrieval, RAG generation, audit logging
├── cli/                 # CLI commands: index, query, topic-model, evaluate, audit-view
└── lib/                 # Utilities: hashing, PII detection, citation parsing

tests/
├── contract/            # Contract tests for CLI commands
├── integration/        # End-to-end integration tests with real meeting JSON
└── unit/                # Unit tests for services and models

data/                    # Example meeting JSON files for testing
├── sample/              # Sample meeting archives
└── benchmarks/          # Evaluation benchmark questions and ground truth

audit_logs/              # Generated audit logs (git-ignored)
indexes/                 # Generated FAISS indexes (git-ignored)
```

**Structure Decision**: Single Python project structure chosen for CLI-focused application. Clear separation of models, services, and CLI entry points. Test structure supports contract, integration, and unit testing as required by Test-First Governance principle.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. All design decisions align with constitution principles.

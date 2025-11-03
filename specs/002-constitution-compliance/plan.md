# Implementation Plan: Constitution Compliance

**Branch**: `002-constitution-compliance` | **Date**: 2025-11-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-constitution-compliance/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement constitution compliance verification and enforcement for the entity data model implementation. Ensure all entity operations (storage, querying, embeddings, LLM inference) comply with Archive-RAG Constitution v1.0.0 requirements: Python-only execution, local embeddings + FAISS storage, and no external API dependencies for core functionality. Implement multiple-layer compliance checks: automated tests during development, runtime checks during execution, and manual verification processes.

**Research Decisions** (from research.md):
- **Compliance Detection**: Static analysis + runtime monitoring + test coverage
- **Violation Handling**: Fail-fast with clear error messages, no silent fallbacks
- **Testing Strategy**: Unit tests for compliance checks, integration tests for violation detection

## Technical Context

**Language/Version**: Python 3.11+ (tested with Python 3.11, 3.12, 3.13)

**Primary Dependencies**: 
- pytest, pytest-cov (existing test framework)
- Existing dependencies: sentence-transformers (local), transformers (local), faiss-cpu (local), pydantic, structlog, typer
- Python standard library: json, pathlib, inspect, ast (for static analysis)
- No new external dependencies required (compliance feature)

**Storage**: 
- Current: JSON file-based entity storage (entities/workgroups/, entities/meetings/, etc.)
- Proposed: No changes to storage - verification only
- FAISS indexes stored locally (no changes)

**Testing**: pytest, pytest-cov (existing test framework)

**Target Platform**: Python CLI application (cross-platform: Linux, macOS, Windows)

**Project Type**: single (existing CLI application structure)

**Performance Goals**: 
- Compliance checks should not significantly impact existing performance targets
- Runtime checks: <10ms overhead per operation
- Development tests: complete within CI/CD pipeline time limits

**Constraints**: 
- Python-only (constitution requirement)
- Local embeddings + FAISS (constitution requirement)
- No external API dependency for core (constitution requirement)
- Must not break existing functionality (backward compatibility)
- Compliance checks must be verifiable and auditable

**Scale/Scope**: 
- Verify compliance for all entity operations (100s-1000s of operations)
- Check compliance for embedding generation (100s-1000s of embeddings)
- Validate LLM inference compliance (100s-1000s of inferences)
- Monitor FAISS index operations (all index operations)
- Cover all CLI commands for entity data model

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with Archive-RAG Constitution principles:

- ✅ **I. Truth-Bound Intelligence**: All outputs grounded in archived meeting data with traceable sources? **YES** - Compliance verification ensures entity model maintains RAG grounding without changing data model behavior.
- ✅ **II. Evidence & Citation First**: Required citation format `[meeting_id | date | speaker]` supported? **YES** - Compliance checks verify entity model maintains citation relationships without changing citation extraction.
- ✅ **III. Reproducibility & Determinism**: Version-locked embeddings, deterministic seeds, reproducible inference? **YES** - Compliance verification ensures local models maintain determinism; no changes to reproducibility behavior.
- ✅ **IV. Test-First Governance**: Benchmark suite, retrieval accuracy, citation validity, factuality checks included? **YES** - Compliance checks add new test layer (constitution compliance tests) to existing test framework.
- ✅ **V. Auditability & Transparency**: Immutable logs, audit records, traceable topic/entity extraction implemented? **YES** - Compliance violations logged in audit trail; existing audit logging enhanced with compliance status.
- ✅ **Additional Constraints**: 
  - ✅ Python-only? **YES** - Compliance checks use Python-only tools (ast, inspect, pytest)
  - ✅ Local embeddings + FAISS? **YES** - Compliance checks verify local-only usage; no remote fallbacks
  - ✅ No external API dependency for core? **YES** - Compliance verification itself uses only local Python tools
  - ✅ SHA-256 hashing for tamper detection? **YES** - Continue existing hashing approach
  - ✅ PII redaction? **YES** - Existing PII detection/redaction continues
  - ✅ Bounded retrieval latency? **YES** - Compliance checks designed for minimal overhead
  - ✅ Safe degradation? **YES** - Compliance violations fail fast with clear errors
  - ✅ Explainability? **YES** - Compliance violations provide clear error messages explaining what was detected

**Constitution Compliance**: ✅ **PASS** - All principles satisfied. Compliance verification feature ensures existing entity model complies with constitution without violating any principles.

## Project Structure

### Documentation (this feature)

```text
specs/002-constitution-compliance/
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
├── lib/
│   ├── compliance.py    # New: Constitution compliance verification utilities
│   └── static_analysis.py  # New: Static analysis for detecting external API calls
├── services/
│   ├── compliance_checker.py  # New: Runtime compliance checking service
│   └── entity_storage.py      # Update: Add compliance checks to entity operations
│   └── embedding.py            # Update: Add compliance checks to embedding operations
│   └── rag_generator.py       # Update: Add compliance checks to LLM inference
├── cli/
│   └── compliance.py    # New: CLI commands for compliance verification
└── (existing entity model files unchanged)

tests/
├── unit/
│   └── test_compliance.py  # New: Unit tests for compliance checking utilities
├── integration/
│   └── test_compliance_checks.py  # New: Integration tests for compliance detection
└── contract/
    └── test_compliance_cli.py  # New: Contract tests for compliance CLI commands
```

**Structure Decision**: Single project structure (existing Archive-RAG CLI application). Compliance verification adds new modules (`lib/compliance.py`, `services/compliance_checker.py`, `cli/compliance.py`) and test files without modifying core entity model implementation. This keeps compliance checks separate and testable.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

(No violations - compliance verification feature aligns with all constitution principles)

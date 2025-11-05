# Implementation Plan: Discord Bot Interface for Archive-RAG

**Branch**: `003-discord-bot-access` | **Date**: 2025-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-discord-bot-access/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a Discord bot interface that allows community members to query the Archive-RAG system using natural language slash commands. The bot integrates with the existing RAG pipeline to provide citation-grounded answers, supports role-based access control (public/contributor/admin), enforces per-user rate limits, and maintains full audit logging for compliance. Technical approach: Python Discord bot library (discord.py) with slash command support, integration with existing QueryService for RAG processing, in-memory rate limiting, and message splitting for long responses.

## Technical Context

**Language/Version**: Python 3.11+ (aligned with existing project requirements)

**Primary Dependencies**: 
- `discord.py>=2.3.0` - Discord bot API library with slash command support
- `aiohttp>=3.9.0` - Async HTTP client (dependency of discord.py, also used for rate limiting)
- Existing Archive-RAG dependencies (sentence-transformers, faiss-cpu, transformers, etc.)
- Integration with existing services: `QueryService`, `AuditWriter`, `EntityQueryService`

**Storage**: 
- Local JSON files for audit logs (existing `audit_logs/` directory)
- In-memory rate limiting state (Redis/persistent storage optional for future scaling)
- FAISS indexes (existing `indexes/` directory)

**Testing**: 
- `pytest>=7.4.0` (existing)
- `pytest-asyncio>=0.21.0` - For async Discord bot tests
- Mock Discord API responses for unit tests

**Target Platform**: 
- Linux/macOS server (where Discord bot runs continuously)
- Same platform as existing Archive-RAG CLI

**Project Type**: Single Python project - extends existing Archive-RAG codebase

**Performance Goals**: 
- 95% of queries respond in under 3 seconds (SC-001)
- Handle 100 concurrent users without degradation (SC-005)
- Bot acknowledgment message sent immediately (<100ms)
- Rate limit checks <10ms overhead

**Constraints**: 
- Must integrate with existing RAG pipeline (no modifications to core RAG services)
- Python-only implementation (constitution requirement)
- Local-only processing by default (constitution-compliant)
- Message size limits: 2000 characters per Discord message (split long responses)
- Per-user rate limit: 10 queries per minute per user
- Bot must handle Discord API rate limits gracefully

**Scale/Scope**: 
- 100 concurrent users (SC-005)
- Single Discord server deployment
- Three slash commands: `/archive query`, `/archive topics`, `/archive people`
- Three user roles: public, contributor, admin

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with Archive-RAG Constitution principles:

- **I. Truth-Bound Intelligence**: ✅ All outputs grounded in archived meeting data with traceable sources - Bot uses existing QueryService which enforces this
- **II. Evidence & Citation First**: ✅ Required citation format `[meeting_id | date | speaker]` supported - Bot formats citations from QueryService results
- **III. Reproducibility & Determinism**: ✅ Version-locked embeddings, deterministic seeds, reproducible inference - Bot uses existing QueryService with same seed/config
- **IV. Test-First Governance**: ⚠️ Benchmark suite, retrieval accuracy, citation validity, factuality checks included? - Bot tests will verify integration with existing test suite
- **V. Auditability & Transparency**: ✅ Immutable logs, audit records, traceable topic/entity extraction implemented - Bot uses existing AuditWriter for all queries
- **Additional Constraints**: 
  - Python-only? **YES** - Implementation in Python using discord.py
  - Remote embeddings allowed? **YES** - Inherits from existing RAG pipeline configuration
  - Remote LLM inference allowed? **YES** - Inherits from existing RAG pipeline configuration
  - FAISS storage local? **YES** - Uses existing local FAISS indexes
  - Entity storage local? **YES** - Uses existing local entity storage
  - Structured data extraction? **YES** - Uses existing entity query services for `/archive topics` and `/archive people`
  - SHA-256 hashing for tamper detection? **YES** - Inherited from existing audit logging
  - PII redaction? **YES** - Inherited from existing RAG pipeline (FR-007)
  - Bounded retrieval latency? **YES** - SC-001: 95% under 3 seconds
  - Safe degradation? **YES** - FR-008: Graceful error handling, FR-013: Acknowledgment messages
  - Explainability? **YES** - Citations always included (FR-003, SC-002)

**Constitution Compliance**: ✅ All principles satisfied. Bot extends existing compliant RAG system without modifying core services.

**Post-Phase 1 Re-evaluation**:
- All Phase 1 design artifacts (data-model.md, contracts/, quickstart.md) maintain constitution compliance
- Bot integration uses existing QueryService and AuditWriter (no modifications to core services)
- Rate limiting and message splitting are bot-specific concerns (no constitution impact)
- Role-based access control uses Discord's native permission system (no custom auth needed)
- All queries logged via existing audit system (100% compliance with Auditability principle)

## Project Structure

### Documentation (this feature)

```text
specs/003-discord-bot-access/
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
├── models/              # Existing models (RAGQuery, etc.)
├── services/            # Existing services
│   ├── query_service.py # Existing - used by bot
│   ├── entity_query.py  # Existing - used for /archive topics and /archive people
│   └── audit_writer.py  # Existing - used for logging
├── cli/                 # Existing CLI commands
├── lib/                 # Existing utilities
└── bot/                 # NEW: Discord bot module
    ├── __init__.py
    ├── bot.py           # Main bot class (Discord client)
    ├── commands/        # Slash command handlers
    │   ├── __init__.py
    │   ├── query.py     # /archive query command
    │   ├── topics.py    # /archive topics command
    │   └── people.py    # /archive people command
    ├── services/        # Bot-specific services
    │   ├── __init__.py
    │   ├── rate_limiter.py  # Per-user rate limiting
    │   ├── message_formatter.py  # Format RAG results for Discord
    │   └── permission_checker.py  # Role-based access control
    └── utils/           # Bot utilities
        ├── __init__.py
        └── message_splitter.py  # Split long messages across Discord limits

tests/
├── contract/            # Existing
├── integration/         # Existing
├── unit/                # Existing
└── bot/                 # NEW: Bot tests
    ├── __init__.py
    ├── test_bot.py      # Bot initialization tests
    ├── test_commands.py  # Slash command tests
    ├── test_rate_limiter.py  # Rate limiting tests
    └── test_permissions.py  # Permission checking tests
```

**Structure Decision**: Single project structure - Discord bot is a new module (`src/bot/`) that integrates with existing services. Follows existing project patterns (services, models, CLI structure).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. All constitution principles satisfied.

# Research & Technology Decisions

**Created**: 2025-11-02  
**Feature**: Archive Meeting Retrieval & Grounded Interpretation RAG

## Technology Stack Decisions

### Embeddings: sentence-transformers

**Decision**: Use sentence-transformers library with local embedding models (e.g., all-MiniLM-L6-v2 or all-mpnet-base-v2)

**Rationale**:
- Local execution aligns with offline-capable requirement (FR-009)
- No external API dependency (constitution constraint)
- Deterministic embeddings with fixed seeds (reproducibility requirement)
- Efficient models suitable for 100k document scale
- Python-only library (constitution constraint)

**Alternatives considered**:
- OpenAI embeddings API: Rejected - external dependency, not offline-capable
- Transformers library directly: Rejected - sentence-transformers provides better API for semantic search
- Word embeddings (Word2Vec, GloVe): Rejected - contextual embeddings perform better for meeting transcripts

### Vector Database: FAISS

**Decision**: Use FAISS (Facebook AI Similarity Search) for local vector storage and retrieval

**Rationale**:
- Local storage (no cloud/hosted vector DB - constitution constraint)
- Fast approximate nearest neighbor search (<2s for 10k docs)
- Deterministic index structure (reproducibility requirement)
- Python bindings for seamless integration
- Supports version-locked indexes (constitution requirement)

**Alternatives considered**:
- Pinecone / Weaviate: Rejected - cloud/hosted services, not offline-capable
- Chroma: Rejected - adds complexity, FAISS sufficient for deterministic needs
- PostgreSQL + pgvector: Rejected - database overhead unnecessary for CLI tool
- Simple cosine similarity: Rejected - FAISS provides optimized search at scale

### Model Runtime: transformers or llama.cpp

**Decision**: Support both transformers library (HuggingFace) and llama.cpp for local LLM inference

**Rationale**:
- Local execution only (offline-capable requirement)
- transformers: Full control, Python-native, good for smaller models
- llama.cpp: Optimized C++ runtime for larger models, better memory efficiency
- Deterministic inference with fixed seeds (reproducibility requirement)
- Version-locked models (constitution requirement)

**Alternatives considered**:
- OpenAI API: Rejected - external dependency, not offline-capable
- Anthropic API: Rejected - external dependency, not offline-capable
- Local OpenAI-compatible server: Rejected - adds complexity, direct model loading preferred

### Topic Modeling: gensim or BERTopic-lite

**Decision**: Use gensim (LDA) or BERTopic-lite for topic modeling

**Rationale**:
- Local execution (offline-capable requirement)
- gensim: Mature, lightweight, deterministic with seeds
- BERTopic-lite: Semantic topic modeling using local embeddings
- Both support reproducible results with fixed seeds
- Advisory only (constitution: topic extraction never authoritative)

**Alternatives considered**:
- Cloud topic modeling APIs: Rejected - external dependency
- Full BERTopic: Rejected - may be overkill, lite version sufficient
- Manual topic extraction: Rejected - automated tools more consistent

### Entity Extraction: spaCy

**Decision**: Use spaCy for named entity recognition

**Rationale**:
- Local execution (offline-capable requirement)
- Python-native library
- Reproducible with version-locked models
- Efficient NER suitable for meeting transcripts
- Advisory only (constitution: entity extraction never authoritative)
- Supports PII detection for redaction (FR-012)

**Alternatives considered**:
- NLTK: Rejected - spaCy more modern and efficient
- Stanford NER: Rejected - Java dependency, Python preferred
- Cloud NER APIs: Rejected - external dependency

### CLI Framework: typer

**Decision**: Use typer for CLI command implementation

**Rationale**:
- Modern Python CLI framework with type hints
- Good integration with Python 3.11
- Supports subcommands (index, query, topic-model, evaluate, audit-view)
- Clean API for command-line interfaces
- Well-documented and maintainable

**Alternatives considered**:
- Click: Rejected - typer provides better type hints and modern Python support
- argparse: Rejected - typer provides better developer experience
- fire: Rejected - typer provides more explicit control

### Logging: structlog

**Decision**: Use structlog for structured JSON logging

**Rationale**:
- Structured logs essential for auditability (FR-005)
- JSON format enables parsing and analysis
- Immutable log entries (constitution requirement)
- Good Python integration
- Supports contextual logging (user ID, model version, etc.)

**Alternatives considered**:
- Standard logging: Rejected - structured JSON logs needed for auditability
- Python logging + JSON formatter: Rejected - structlog provides better structured logging API
- Custom logging: Rejected - structlog is well-maintained standard

### Hashing: hashlib

**Decision**: Use Python standard library hashlib for SHA-256 tamper detection

**Rationale**:
- Standard library (no external dependency)
- SHA-256 required by constitution
- Tamper detection for meeting JSON (FR-011)
- Deterministic hashing suitable for versioning

**Alternatives considered**:
- External hashing libraries: Rejected - standard library sufficient
- MD5: Rejected - SHA-256 provides better security
- CRC32: Rejected - SHA-256 required by constitution

## Architecture Patterns

### RAG Architecture: Retrieval-Augmented Generation

**Decision**: Implement retrieval-first RAG pipeline

**Rationale**:
- Enforces truth-bound intelligence (constitution principle I)
- Retrieval ensures all outputs grounded in archived data
- Citation extraction from retrieved sources
- "No evidence found" response when retrieval fails (FR-008)

**Pattern**: 
1. Query embedding
2. FAISS similarity search
3. Top-k chunk retrieval
4. LLM generation with retrieved context only
5. Citation extraction from retrieved sources
6. Audit logging of query, sources, output

### Deterministic Inference

**Decision**: Use fixed seeds for all random operations

**Rationale**:
- Reproducibility requirement (constitution principle III)
- Same input + data state → identical output
- Essential for auditability and testing

**Implementation**:
- Embedding model: fixed random seed
- LLM inference: fixed random seed
- FAISS index: deterministic construction
- Topic modeling: fixed random seed

### Version Locking

**Decision**: Pin all model versions and dependency versions

**Rationale**:
- Reproducibility requirement (constitution principle III)
- Ensures consistent behavior across environments
- Essential for audit trail (FR-005)

**Implementation**:
- requirements.txt with pinned versions
- Model version tracking in index metadata
- Version logging in audit records

## Integration Decisions

### SSO Integration

**Decision**: Support SSO authentication for user identification

**Rationale**:
- FR-013 requires SSO authentication
- User ID needed for audit logs (constitution principle V)
- Integration with existing identity provider

**Implementation**: 
- Use standard SSO libraries (e.g., python-jose, authlib)
- Extract user ID from SSO token
- Include user ID in audit logs
- Do not store SSO tokens (security best practice)

### Audit Log Retention

**Decision**: Implement 3-year retention policy for audit logs (FR-014)

**Rationale**:
- FR-014 specifies 3-year retention
- Standard compliance window
- Moderate storage requirements

**Implementation**:
- Log rotation after 3 years
- Archive old logs
- Storage planning for multi-year data

## Performance Considerations

### Retrieval Latency Target: <2 seconds

**Decision**: Optimize FAISS index and retrieval for <2s latency

**Rationale**:
- SC-003 specifies <2s for 10k-record dataset
- Bounded latency required by constitution
- Good user experience for CLI tool

**Optimization strategies**:
- FAISS IndexFlatIP or IndexIVFFlat for faster search
- Batch embedding operations
- Cache frequently accessed data

### Memory Bounds: <4GB RAM

**Decision**: Target <4GB RAM usage

**Rationale**:
- Memory constraint from technical context
- Enables deployment on standard hardware
- Air-gap compatible hardware constraints

**Optimization strategies**:
- Use quantized models where possible
- Lazy loading of models
- Efficient FAISS index storage

## Security & Privacy Decisions

### PII Detection & Redaction

**Decision**: Use spaCy NER + custom rules for PII detection

**Rationale**:
- FR-012 requires privacy filters
- Constitution requires PII redaction
- Topic/entity extraction must not infer missing personal data

**Implementation**:
- spaCy NER for entity detection
- Custom patterns for meeting-specific PII
- Redaction before topic modeling/entity extraction
- Log redaction actions for auditability

### Tamper Detection: SHA-256 Hashing

**Decision**: Hash all meeting JSON input files with SHA-256

**Rationale**:
- FR-011 requires tamper detection
- Constitution specifies SHA-256 hashing
- Ensures data integrity for audit trail

**Implementation**:
- Hash at ingestion time
- Store hash in index metadata
- Verify hash on index access
- Log hash mismatches as security events

## Testing Strategy

### Deterministic Tests with Golden Files

**Decision**: Use golden file tests for citation validation

**Rationale**:
- Test-First Governance (constitution principle IV)
- Ensures citation format compliance (constitution principle II)
- Regression detection for hallucination

**Implementation**:
- Fixed seed for all tests
- Golden file outputs for expected citations
- Citation format validation in tests
- Regression test suite for evaluation

### Integration Test Data

**Decision**: Use real meeting JSON samples for integration testing

**Rationale**:
- Real data validates end-to-end pipeline
- Tests actual retrieval and citation behavior
- Validates against constitution principles

**Implementation**:
- Sample meeting JSON in `data/sample/`
- Anonymized real meeting data
- Test queries with known expected results

---

## Summary

All technology choices align with constitution principles:
- ✅ Python-only execution
- ✅ Local models (no external API dependencies)
- ✅ Deterministic and reproducible
- ✅ Offline-capable
- ✅ Audit-friendly with structured logging
- ✅ Privacy-aware with PII redaction
- ✅ Tamper detection with SHA-256 hashing

No external dependencies for core functionality. All models run locally, ensuring offline operation and full auditability.

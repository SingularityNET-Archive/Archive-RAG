# CLI Commands Contract

**Created**: 2025-11-02  
**Feature**: Archive Meeting Retrieval & Grounded Interpretation RAG

## CLI Interface

All commands use Typer for CLI implementation. Commands follow standard CLI patterns: `command [OPTIONS] [ARGS]`

### Base Command: `archive-rag`

All commands are subcommands of `archive-rag`:

```
archive-rag [COMMAND] [OPTIONS] [ARGS]
```

---

## Command: `index`

**Purpose**: Ingest meeting JSON files and create FAISS vector index.

**Usage**:
```bash
archive-rag index [OPTIONS] INPUT_DIR OUTPUT_INDEX
```

**Arguments**:
- `INPUT_DIR` (required): Directory containing meeting JSON files
- `OUTPUT_INDEX` (required): Path to output FAISS index file

**Options**:
- `--embedding-model` (string, optional): Embedding model name (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `--chunk-size` (integer, optional): Chunk size for document splitting (default: 512)
- `--chunk-overlap` (integer, optional): Overlap between chunks (default: 50)
- `--seed` (integer, optional): Random seed for reproducibility (default: 42)
- `--hash-only` (flag): Only compute SHA-256 hashes, do not index (for validation)
- `--verify-hash` (string, optional): Verify SHA-256 hash of input files
- `--redact-pii` (flag): Enable PII detection and redaction (default: true)

**Behavior**:
1. Scan INPUT_DIR for JSON files
2. Validate JSON structure (MeetingRecord format)
3. Compute SHA-256 hash for each file (FR-011)
4. Detect and redact PII if `--redact-pii` enabled (FR-012)
5. Chunk transcript text
6. Generate embeddings using specified model
7. Build FAISS index with embeddings
8. Store metadata mapping (chunk → meeting_id, date, participants, etc.)
9. Write index to OUTPUT_INDEX
10. Log indexing operation to audit logs

**Output**:
- FAISS index file at OUTPUT_INDEX
- Index metadata file at OUTPUT_INDEX.metadata.json
- Audit log entry for indexing operation

**Errors**:
- Invalid JSON → error message, skip file, continue processing
- Hash mismatch → error message, abort if `--verify-hash` provided
- PII detection failure → warning message, continue with redaction

**Examples**:
```bash
# Index meeting JSON files
archive-rag index data/meetings/ indexes/meetings.faiss

# Index with custom embedding model
archive-rag index --embedding-model sentence-transformers/all-mpnet-base-v2 data/meetings/ indexes/meetings.faiss

# Verify hashes before indexing
archive-rag index --verify-hash <hash> data/meetings/ indexes/meetings.faiss

# Compute hashes only (no indexing)
archive-rag index --hash-only data/meetings/ -
```

---

## Command: `query`

**Purpose**: Query the RAG system and get evidence-bound answers with citations.

**Usage**:
```bash
archive-rag query [OPTIONS] INDEX_FILE QUERY
```

**Arguments**:
- `INDEX_FILE` (required): Path to FAISS index file
- `QUERY` (required): User question string

**Options**:
- `--model` (string, optional): LLM model name (default: local model path)
- `--model-version` (string, optional): LLM model version (required for reproducibility)
- `--top-k` (integer, optional): Number of chunks to retrieve (default: 5)
- `--seed` (integer, optional): Random seed for deterministic inference (default: 42)
- `--output-format` (string, optional): Output format: `text` or `json` (default: `text`)
- `--no-audit` (flag): Skip audit logging (not recommended, violates constitution)
- `--user-id` (string, optional): SSO user ID (from authentication context)

**Behavior**:
1. Load FAISS index from INDEX_FILE
2. Load index metadata
3. Embed user query using same embedding model as index
4. Retrieve top-k similar chunks from FAISS
5. Assemble retrieved context with metadata (meeting_id, date, participants, text)
6. Generate answer using LLM with retrieved context only
7. Extract citations from retrieved chunks in format `[meeting_id | date | speaker]`
8. Check for credible evidence (FR-008)
9. Format output with citations
10. Create immutable audit log entry (FR-005)
11. Return answer and citations

**Output** (text format):
```
Answer: [Generated answer text]

Citations:
- [meeting_001 | 2024-03-15 | Speaker Name]: [Excerpt text]
- [meeting_002 | 2024-04-20 | Another Speaker]: [Excerpt text]
```

**Output** (JSON format):
```json
{
  "query_id": "uuid",
  "query": "user question",
  "answer": "generated answer",
  "citations": [
    {
      "meeting_id": "meeting_001",
      "date": "2024-03-15",
      "speaker": "Speaker Name",
      "excerpt": "relevant text excerpt"
    }
  ],
  "evidence_found": true,
  "model_version": "model-name-v1.0",
  "embedding_version": "all-MiniLM-L6-v2",
  "retrieved_chunks": [
    {
      "meeting_id": "meeting_001",
      "chunk_index": 0,
      "text": "full chunk text",
      "score": 0.85
    }
  ],
  "audit_log_path": "audit_logs/query-uuid.json"
}
```

**Errors**:
- Index not found → error message, exit with code 1
- No evidence found → return "No evidence found" message (FR-008)
- Model loading failure → error message, exit with code 1

**Examples**:
```bash
# Query with text output
archive-rag query indexes/meetings.faiss "What decisions were made about budget allocation?"

# Query with JSON output
archive-rag query --output-format json indexes/meetings.faiss "What decisions were made?"

# Query with custom model version
archive-rag query --model-version llama-7b-v1.0 indexes/meetings.faiss "What decisions were made?"

# Query with specific user ID
archive-rag query --user-id user@example.com indexes/meetings.faiss "What decisions were made?"
```

---

## Command: `topic-model`

**Purpose**: Run topic modeling on meeting archive to discover high-level topics.

**Usage**:
```bash
archive-rag topic-model [OPTIONS] INDEX_FILE OUTPUT_DIR
```

**Arguments**:
- `INDEX_FILE` (required): Path to FAISS index file
- `OUTPUT_DIR` (required): Directory to write topic modeling results

**Options**:
- `--num-topics` (integer, optional): Number of topics to discover (default: 10)
- `--method` (string, optional): Topic modeling method: `lda` or `bertopic` (default: `lda`)
- `--seed` (integer, optional): Random seed for reproducibility (default: 42)
- `--no-pii` (flag): Skip PII detection and redaction before topic modeling (not recommended)

**Behavior**:
1. Load FAISS index and metadata
2. Extract document text from metadata
3. Apply PII redaction if enabled (FR-012)
4. Run topic modeling (LDA via gensim or BERTopic-lite)
5. Generate topic clusters
6. Extract top keywords per topic
7. Write topic modeling results to OUTPUT_DIR
8. Log topic modeling operation to audit logs

**Output**:
- Topic clusters JSON file: `OUTPUT_DIR/topics.json`
- Topic visualization (optional): `OUTPUT_DIR/topics.png`
- Audit log entry for topic modeling operation

**Output Format** (topics.json):
```json
{
  "topics": [
    {
      "topic_id": 0,
      "keywords": ["budget", "allocation", "funding"],
      "documents": ["meeting_001", "meeting_005"],
      "representative_text": "budget allocation discussion"
    }
  ],
  "method": "lda",
  "num_topics": 10,
  "timestamp": "2024-11-02T10:00:00Z"
}
```

**Notes**:
- Topic extraction is advisory only (constitution principle V)
- No personal data inferred or invented
- Results logged for auditability

**Examples**:
```bash
# Run topic modeling with default settings
archive-rag topic-model indexes/meetings.faiss results/topics/

# Run with 20 topics using BERTopic
archive-rag topic-model --num-topics 20 --method bertopic indexes/meetings.faiss results/topics/
```

---

## Command: `extract-entities`

**Purpose**: Extract named entities from meeting archive.

**Usage**:
```bash
archive-rag extract-entities [OPTIONS] INDEX_FILE OUTPUT_DIR
```

**Arguments**:
- `INDEX_FILE` (required): Path to FAISS index file
- `OUTPUT_DIR` (required): Directory to write entity extraction results

**Options**:
- `--model` (string, optional): spaCy model name (default: `en_core_web_sm`)
- `--entity-types` (string, optional): Comma-separated entity types to extract (default: all)
- `--min-frequency` (integer, optional): Minimum frequency for entity inclusion (default: 2)
- `--no-pii` (flag): Skip PII detection and redaction before extraction (not recommended)

**Behavior**:
1. Load FAISS index and metadata
2. Extract document text from metadata
3. Apply PII redaction if enabled (FR-012)
4. Run spaCy NER on document text
5. Aggregate entities by type and frequency
6. Filter entities by minimum frequency
7. Write entity extraction results to OUTPUT_DIR
8. Log entity extraction operation to audit logs

**Output**:
- Entity list JSON file: `OUTPUT_DIR/entities.json`
- Audit log entry for entity extraction operation

**Output Format** (entities.json):
```json
{
  "entities": [
    {
      "text": "Budget Committee",
      "type": "ORG",
      "frequency": 15,
      "meetings": ["meeting_001", "meeting_003"]
    }
  ],
  "model": "en_core_web_sm",
  "timestamp": "2024-11-02T10:00:00Z"
}
```

**Notes**:
- Entity extraction is advisory only (constitution principle V)
- No personal data inferred or invented
- PII entities redacted before extraction

**Examples**:
```bash
# Extract all entities
archive-rag extract-entities indexes/meetings.faiss results/entities/

# Extract only organizations and persons
archive-rag extract-entities --entity-types ORG,PERSON indexes/meetings.faiss results/entities/
```

---

## Command: `evaluate`

**Purpose**: Run evaluation suite to measure factuality and citation compliance.

**Usage**:
```bash
archive-rag evaluate [OPTIONS] INDEX_FILE BENCHMARK_FILE OUTPUT_DIR
```

**Arguments**:
- `INDEX_FILE` (required): Path to FAISS index file
- `BENCHMARK_FILE` (required): Path to evaluation benchmark JSON file (EvaluationCase format)
- `OUTPUT_DIR` (required): Directory to write evaluation results

**Options**:
- `--model` (string, optional): LLM model name (default: local model path)
- `--model-version` (string, optional): LLM model version
- `--seed` (integer, optional): Random seed for reproducibility (default: 42)
- `--output-format` (string, optional): Results format: `json` or `report` (default: `report`)

**Behavior**:
1. Load FAISS index and metadata
2. Load benchmark file (EvaluationCase format)
3. For each evaluation case:
   a. Run query against RAG system
   b. Compare output against ground truth
   c. Validate citations against expected citations
   d. Compute metrics: citation_accuracy, factuality, hallucination_count
4. Aggregate metrics across all cases
5. Write evaluation results to OUTPUT_DIR
6. Log evaluation operation to audit logs

**Output** (report format):
```
Evaluation Results:
- Total Cases: 100
- Citation Accuracy: 92%
- Factuality Score: 88%
- Hallucination Count: 0
- Retrieval Latency: 1.5s avg

Per-Case Results: [see output JSON for details]
```

**Output** (JSON format):
```json
{
  "total_cases": 100,
  "citation_accuracy": 0.92,
  "factuality_score": 0.88,
  "hallucination_count": 0,
  "retrieval_latency_avg": 1.5,
  "cases": [
    {
      "case_id": "case_001",
      "prompt": "test query",
      "citation_accuracy": 1.0,
      "factuality": 0.9,
      "hallucination_count": 0
    }
  ],
  "timestamp": "2024-11-02T10:00:00Z"
}
```

**Validation**:
- Citation accuracy ≥90% (SC-001)
- Hallucination count = 0 (SC-002)
- Retrieval latency <2s (SC-003)

**Examples**:
```bash
# Run evaluation suite
archive-rag evaluate indexes/meetings.faiss data/benchmarks/eval.json results/evaluation/

# Run with JSON output
archive-rag evaluate --output-format json indexes/meetings.faiss data/benchmarks/eval.json results/evaluation/
```

---

## Command: `audit-view`

**Purpose**: View and analyze audit logs.

**Usage**:
```bash
archive-rag audit-view [OPTIONS] [LOG_FILE]
```

**Arguments**:
- `LOG_FILE` (optional): Path to specific audit log file (if not provided, list all logs)

**Options**:
- `--query-id` (string, optional): Filter by query ID
- `--user-id` (string, optional): Filter by user ID
- `--date-from` (string, optional): Filter logs from date (ISO 8601)
- `--date-to` (string, optional): Filter logs to date (ISO 8601)
- `--format` (string, optional): Output format: `text` or `json` (default: `text`)
- `--export` (string, optional): Export filtered logs to file

**Behavior**:
1. If LOG_FILE provided, display specific log entry
2. Otherwise, scan audit_logs/ directory
3. Apply filters (query-id, user-id, date range)
4. Display filtered audit logs
5. Export logs if `--export` specified

**Output** (text format):
```
Audit Logs:
- Query ID: uuid-123
  User: user@example.com
  Timestamp: 2024-11-02T10:00:00Z
  Query: "What decisions were made?"
  Evidence Found: true
  Citations: 3
  Model Version: model-v1.0
  [Full log details...]
```

**Output** (JSON format):
```json
{
  "logs": [
    {
      "query_id": "uuid-123",
      "user_id": "user@example.com",
      "timestamp": "2024-11-02T10:00:00Z",
      "query": "What decisions were made?",
      "answer": "Generated answer...",
      "citations": [...],
      "model_version": "model-v1.0",
      "embedding_version": "all-MiniLM-L6-v2"
    }
  ]
}
```

**Examples**:
```bash
# List all audit logs
archive-rag audit-view

# View specific log file
archive-rag audit-view audit_logs/query-uuid.json

# Filter by user ID
archive-rag audit-view --user-id user@example.com

# Export logs from date range
archive-rag audit-view --date-from 2024-01-01 --date-to 2024-12-31 --export logs_2024.json
```

---

## Common Options (All Commands)

- `--verbose` / `-v`: Enable verbose logging
- `--quiet` / `-q`: Suppress non-error output
- `--version`: Show version information
- `--help` / `-h`: Show command help

## Error Codes

- `0`: Success
- `1`: General error (invalid input, file not found, etc.)
- `2`: Configuration error (invalid model, missing dependency, etc.)
- `3`: Runtime error (model loading failure, index corruption, etc.)

## Exit Behavior

All commands follow standard CLI conventions:
- Success: Exit code 0, output to stdout
- Errors: Exit code >0, error messages to stderr
- Structured output: JSON format available for programmatic use
- Human-readable output: Text format for interactive use

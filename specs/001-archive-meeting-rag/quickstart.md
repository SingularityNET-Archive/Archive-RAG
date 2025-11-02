# Quickstart Guide: Archive Meeting RAG

**Created**: 2025-11-02  
**Feature**: Archive Meeting Retrieval & Grounded Interpretation RAG

## Prerequisites

- Python 3.11 (locked version)
- pip package manager
- 4GB+ RAM available
- Meeting JSON files in required format (see MeetingRecord in data-model.md)

## Installation

```bash
# Clone repository
git clone <repository-url>
cd Archive-RAG

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (for entity extraction)
python -m spacy download en_core_web_sm

# Download embedding model (sentence-transformers will auto-download on first use)
# Or download manually: sentence-transformers all-MiniLM-L6-v2
```

## Basic Usage

### Step 1: Prepare Meeting JSON Files

Create a directory with meeting JSON files in the following format:

```json
{
  "id": "meeting_001",
  "date": "2024-03-15T10:00:00Z",
  "participants": ["Alice", "Bob", "Charlie"],
  "transcript": "Meeting transcript text here...",
  "decisions": ["Decision 1", "Decision 2"],
  "tags": ["budget", "planning"]
}
```

Example directory structure:
```
data/
└── meetings/
    ├── meeting_001.json
    ├── meeting_002.json
    └── meeting_003.json
```

### Step 2: Index Meeting Files

Create a FAISS vector index from meeting JSON files:

```bash
# Basic indexing
archive-rag index data/meetings/ indexes/meetings.faiss

# Index with custom embedding model
archive-rag index --embedding-model sentence-transformers/all-mpnet-base-v2 data/meetings/ indexes/meetings.faiss

# Index with PII redaction (recommended)
archive-rag index --redact-pii data/meetings/ indexes/meetings.faiss
```

**Expected Output**:
- FAISS index file: `indexes/meetings.faiss`
- Index metadata: `indexes/meetings.faiss.metadata.json`
- Audit log: `audit_logs/index-{timestamp}.json`

### Step 3: Query the RAG System

Query the indexed meetings:

```bash
# Basic query with text output
archive-rag query indexes/meetings.faiss "What decisions were made about budget allocation?"

# Query with JSON output (for programmatic use)
archive-rag query --output-format json indexes/meetings.faiss "What decisions were made?"
```

**Expected Output** (text format):
```
Answer: Based on the meeting records, the following decisions were made about budget allocation...

Citations:
- [meeting_001 | 2024-03-15 | Alice]: "The budget committee decided to allocate $100k to the marketing department."
- [meeting_002 | 2024-04-20 | Bob]: "Additional funding of $50k was approved for Q2 projects."
```

**Expected Output** (JSON format):
```json
{
  "query_id": "uuid-123",
  "query": "What decisions were made about budget allocation?",
  "answer": "Based on the meeting records...",
  "citations": [
    {
      "meeting_id": "meeting_001",
      "date": "2024-03-15",
      "speaker": "Alice",
      "excerpt": "The budget committee decided..."
    }
  ],
  "evidence_found": true,
  "model_version": "model-name-v1.0",
  "audit_log_path": "audit_logs/query-uuid-123.json"
}
```

### Step 4: View Audit Logs

View audit logs for compliance and transparency:

```bash
# List all audit logs
archive-rag audit-view

# View specific query log
archive-rag audit-view audit_logs/query-uuid-123.json

# Filter by user ID
archive-rag audit-view --user-id user@example.com

# Export logs from date range
archive-rag audit-view --date-from 2024-01-01 --date-to 2024-12-31 --export logs_2024.json
```

## Advanced Usage

### Topic Modeling

Discover high-level topics in the meeting archive:

```bash
# Run topic modeling with default settings
archive-rag topic-model indexes/meetings.faiss results/topics/

# Run with 20 topics using BERTopic
archive-rag topic-model --num-topics 20 --method bertopic indexes/meetings.faiss results/topics/
```

**Output**: `results/topics/topics.json` with topic clusters and keywords.

### Entity Extraction

Extract named entities from meetings:

```bash
# Extract all entities
archive-rag extract-entities indexes/meetings.faiss results/entities/

# Extract only organizations and persons
archive-rag extract-entities --entity-types ORG,PERSON indexes/meetings.faiss results/entities/
```

**Output**: `results/entities/entities.json` with entity list and frequencies.

### Evaluation

Run evaluation suite to measure factuality and citation compliance:

```bash
# Prepare benchmark file (data/benchmarks/eval.json)
# Format: Array of EvaluationCase objects (see data-model.md)

# Run evaluation
archive-rag evaluate indexes/meetings.faiss data/benchmarks/eval.json results/evaluation/
```

**Expected Output**:
```
Evaluation Results:
- Total Cases: 100
- Citation Accuracy: 92% (≥90% required per SC-001)
- Factuality Score: 88%
- Hallucination Count: 0 (required per SC-002)
- Retrieval Latency: 1.5s avg (<2s required per SC-003)
```

## Reproducibility

For reproducible results, use fixed seeds:

```bash
# Index with fixed seed
archive-rag index --seed 42 data/meetings/ indexes/meetings.faiss

# Query with fixed seed
archive-rag query --seed 42 indexes/meetings.faiss "What decisions were made?"

# Topic modeling with fixed seed
archive-rag topic-model --seed 42 indexes/meetings.faiss results/topics/
```

**Note**: Same input + data state + seed → identical output (constitution principle III).

## Security & Privacy

### PII Redaction

Enable PII redaction during indexing:

```bash
archive-rag index --redact-pii data/meetings/ indexes/meetings.faiss
```

PII entities are redacted before indexing and entity extraction (FR-012).

### Tamper Detection

Verify SHA-256 hashes of input files:

```bash
# Compute hashes only
archive-rag index --hash-only data/meetings/ -

# Verify hash during indexing
archive-rag index --verify-hash <expected-hash> data/meetings/ indexes/meetings.faiss
```

Hash mismatches are logged as security events (FR-011).

## Troubleshooting

### Common Issues

1. **Index not found**
   - Error: `Index file not found: indexes/meetings.faiss`
   - Solution: Run `archive-rag index` first to create index

2. **No evidence found**
   - Response: `"No evidence found"`
   - Reason: Query does not match any indexed content (FR-008)
   - Solution: Try rephrasing query or check index contents

3. **Model loading failure**
   - Error: `Failed to load model: model-name`
   - Solution: Verify model path and version, check dependencies

4. **Memory limit exceeded**
   - Error: `Memory limit exceeded (<4GB target)`
   - Solution: Use smaller embedding model or reduce batch size

### Getting Help

```bash
# Show command help
archive-rag --help
archive-rag query --help

# Show version
archive-rag --version
```

## Directory Structure

After initial setup and usage:

```
Archive-RAG/
├── src/                    # Source code
├── tests/                  # Test suite
├── data/                   # Meeting JSON files
│   ├── meetings/          # Input meeting JSON
│   └── benchmarks/        # Evaluation benchmarks
├── indexes/                # Generated FAISS indexes (git-ignored)
│   ├── meetings.faiss
│   └── meetings.faiss.metadata.json
├── audit_logs/             # Audit logs (git-ignored)
│   ├── index-{timestamp}.json
│   └── query-{uuid}.json
└── results/                # Output results
    ├── topics/            # Topic modeling results
    ├── entities/          # Entity extraction results
    └── evaluation/         # Evaluation results
```

## Next Steps

1. **Review Constitution**: Understand Archive-RAG principles (see `.specify/memory/constitution.md`)
2. **Run Tests**: Execute test suite to verify setup
3. **Index Your Data**: Prepare meeting JSON files and create index
4. **Query System**: Start querying with example questions
5. **Review Audit Logs**: Ensure auditability and transparency

## Validation Checklist

After following this quickstart, verify:

- ✅ Index created successfully
- ✅ Queries return answers with citations in format `[meeting_id | date | speaker]`
- ✅ Audit logs created for each query
- ✅ "No evidence found" returned when no matches
- ✅ Citations traceable to retrieved chunks
- ✅ Topic modeling and entity extraction work correctly
- ✅ Evaluation suite runs successfully
- ✅ Reproducible results with fixed seeds

## Support

For issues or questions:
- Review feature specification: `specs/001-archive-meeting-rag/spec.md`
- Review data model: `specs/001-archive-meeting-rag/data-model.md`
- Review CLI contracts: `specs/001-archive-meeting-rag/contracts/cli-commands.md`
- Check audit logs for debugging: `archive-rag audit-view`

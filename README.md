# Archive-RAG

**Archive Meeting Retrieval & Grounded Interpretation RAG**

A Python-only, audit-friendly RAG pipeline to interpret archived meeting JSON logs with evidence-bound answers, verifiable citations, offline reproducibility, and human auditability.

## Features

- **Evidence-Bound Answers**: All outputs grounded in archived meeting data with traceable sources
- **Verifiable Citations**: Citation format `[meeting_id | date | speaker]` with full provenance
- **Offline Reproducibility**: Local embedding models (sentence-transformers) + FAISS vector database
- **Human Auditability**: Comprehensive query audit logging for compliance and transparency
- **Topic Modeling**: Discover high-level topics using gensim/BERTopic-lite
- **Entity Extraction**: Extract named entities using spaCy with PII redaction
- **Evaluation Suite**: Benchmark questions + scoring script for factuality & citation compliance

## Quickstart

See [quickstart.md](specs/001-archive-meeting-rag/quickstart.md) for detailed setup and usage instructions.

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Archive-RAG

# Create virtual environment (Python 3.11+ required, tested with Python 3.13)
python3 -m venv venv  # or python3.11 -m venv venv if you have Python 3.11
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (for entity extraction)
python -m spacy download en_core_web_sm
```

### Basic Usage

```bash
# Index sample data from official GitHub source (120+ meetings)
archive-rag index "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" indexes/sample-meetings.faiss --no-redact-pii

# Query the RAG system
archive-rag query indexes/sample-meetings.faiss "What decisions were made about budget allocation?"

# Or index your own meeting JSON files
archive-rag index data/meetings/ indexes/meetings.faiss

# View audit logs
archive-rag audit-view
```

## Project Structure

```
Archive-RAG/
├── src/                    # Source code
│   ├── models/            # Data models
│   ├── services/          # Core services
│   ├── cli/               # CLI commands
│   └── lib/               # Utilities
├── tests/                  # Test suite
│   ├── contract/          # Contract tests
│   ├── integration/       # Integration tests
│   └── unit/              # Unit tests
├── data/                   # Meeting JSON files
│   ├── benchmarks/        # Evaluation benchmarks
│   └── README.md         # Data usage guide (see official GitHub source for sample data)
├── indexes/                # Generated FAISS indexes (git-ignored)
└── audit_logs/             # Audit logs (git-ignored)
```

## Documentation

- **Specification**: [specs/001-archive-meeting-rag/spec.md](specs/001-archive-meeting-rag/spec.md)
- **Implementation Plan**: [specs/001-archive-meeting-rag/plan.md](specs/001-archive-meeting-rag/plan.md)
- **Data Model**: [specs/001-archive-meeting-rag/data-model.md](specs/001-archive-meeting-rag/data-model.md)
- **Quickstart Guide**: [specs/001-archive-meeting-rag/quickstart.md](specs/001-archive-meeting-rag/quickstart.md)
- **CLI Contracts**: [specs/001-archive-meeting-rag/contracts/cli-commands.md](specs/001-archive-meeting-rag/contracts/cli-commands.md)

## Constitution Principles

This project adheres to the Archive-RAG Constitution:

1. **Truth-Bound Intelligence**: All outputs grounded in archived meeting data
2. **Evidence & Citation First**: Required citation format `[meeting_id | date | speaker]`
3. **Reproducibility & Determinism**: Version-locked, deterministic behavior
4. **Test-First Governance**: Benchmark suite and regression tests
5. **Auditability & Transparency**: Immutable logs and audit records

See [.specify/memory/constitution.md](.specify/memory/constitution.md) for details.

## Requirements

- Python 3.11+ (tested with Python 3.11, 3.12, and 3.13)
- 4GB+ RAM available
- Meeting JSON files in required format (see data-model.md)

## License

[To be specified]

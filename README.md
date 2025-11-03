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

## Entity Extraction

The Archive-RAG system automatically extracts structured entities from meeting records during ingestion, creating a relational entity-based data model for efficient querying and relationship navigation.

### Overview

When you ingest meetings, the system automatically extracts and saves the following entities:
- **Meetings**: 120 meetings extracted
- **Workgroups**: 30 workgroups
- **People**: 136 people (hosts, documenters, participants)
- **Documents**: 380 documents (working docs from meetings)
- **Agenda Items**: Extracted from meeting records
- **Decision Items**: 234 decisions
- **Action Items**: Extracted from agenda items

### How Entity Extraction Works

When you ingest meetings using `archive-rag ingest-entities`, the system:

1. **Parses meeting records** from JSON source files
2. **Extracts and creates entities** for meetings, workgroups, people, documents, agenda items, decisions, and action items
3. **Establishes relationships** between entities (e.g., meetings belong to workgroups, documents belong to meetings)
4. **Saves entities** to JSON files in `entities/` directory structure
5. **Maintains referential integrity** with foreign key validation

All entities are stored locally as JSON files, enabling fast queries and relationship traversal without database dependencies.

### Extracted Entities

The following entities are automatically extracted and stored:

#### 1. **Meetings** (`entities/meetings/`)
- **Source**: Meeting records with `workgroup_id`, `date`, `meetingInfo`
- **Fields**: `id`, `workgroup_id`, `meeting_type`, `date`, `host_id`, `documenter_id`, `purpose`, `video_link`, `timestamped_video`
- **Relationships**: Belongs to Workgroup, has many Documents/AgendaItems
- **Example Queries**:
  ```bash
  # Count meetings
  archive-rag query indexes/sample-meetings.faiss "How many meetings are there?"
  
  # Query meetings by workgroup
  archive-rag query-workgroup <workgroup_id>
  
  # Query specific meeting
  archive-rag query-meeting <meeting_id> --documents --decisions
  ```

#### 2. **Workgroups** (`entities/workgroups/`)
- **Source**: Workgroup information from `workgroup_id` and `workgroup` fields
- **Fields**: `id`, `name`
- **Relationships**: Has many Meetings
- **Example Queries**:
  ```bash
  # Count workgroups
  archive-rag query indexes/sample-meetings.faiss "How many workgroups are there?"
  
  # List meetings for a workgroup
  archive-rag query-workgroup <workgroup_id>
  ```

#### 3. **People** (`entities/people/`)
- **Source**: Host, documenter, and participants from `meetingInfo`
- **Fields**: `id`, `display_name`, `alias`, `role`
- **Relationships**: Assigned to ActionItems, attends Meetings (via MeetingPerson)
- **Example Queries**:
  ```bash
  # Count people
  archive-rag query indexes/sample-meetings.faiss "How many people participated in meetings?"
  
  # Query person and their action items
  archive-rag query-person <person_id> --action-items
  ```

#### 4. **Documents** (`entities/documents/`)
- **Source**: `meetingInfo.workingDocs` array
- **Fields**: `id`, `meeting_id`, `title`, `link`
- **Relationships**: Belongs to Meeting
- **Example Queries**:
  ```bash
  # Count documents
  archive-rag query indexes/sample-meetings.faiss "How many documents are there?"
  
  # List all documents
  archive-rag query indexes/sample-meetings.faiss "List all documents"
  
  # List documents by workgroup
  archive-rag query indexes/sample-meetings.faiss "List documents for Governance workgroup"
  archive-rag query indexes/sample-meetings.faiss "Show documents for Archives workgroup"
  ```

#### 5. **Agenda Items** (`entities/agenda_items/`)
- **Source**: `agendaItems` array in meeting records
- **Fields**: `id`, `meeting_id`, `status`, `narrative`
- **Relationships**: Belongs to Meeting, has many DecisionItems/ActionItems
- **Example Queries**:
  ```bash
  # Query agenda items via meeting
  archive-rag query-meeting <meeting_id>
  ```

#### 6. **Decision Items** (`entities/decision_items/`)
- **Source**: `agendaItems[].decisionItems` array
- **Fields**: `id`, `agenda_item_id`, `decision`, `rationale`, `effect`
- **Relationships**: Belongs to AgendaItem
- **Example Queries**:
  ```bash
  # Count decisions
  archive-rag query indexes/sample-meetings.faiss "How many decisions were made from all workgroups?"
  
  # Query decisions by text
  archive-rag query-decisions indexes/sample-meetings.faiss "budget allocation"
  
  # Query decisions for a meeting
  archive-rag query-meeting <meeting_id> --decisions
  ```

#### 7. **Action Items** (`entities/action_items/`)
- **Source**: `agendaItems[].actionItems` array
- **Fields**: `id`, `agenda_item_id`, `text`, `assignee_id`, `due_date`, `status`
- **Relationships**: Belongs to AgendaItem, assigned to Person
- **Example Queries**:
  ```bash
  # Query action items for a person
  archive-rag query-person <person_id> --action-items
  ```

### Entity Storage Structure

```
entities/
├── workgroups/          # Workgroup entities (30 workgroups)
├── meetings/            # Meeting entities (120 meetings)
├── people/              # Person entities (136 people)
├── documents/           # Document entities (380 documents)
├── agenda_items/        # Agenda item entities
├── decision_items/      # Decision item entities (234 decisions)
├── action_items/        # Action item entities
├── _index/              # Index files for fast lookups
│   └── meetings_by_workgroup.json
└── _relations/          # Junction tables for many-to-many relationships
```

### Ingesting Entities

To extract and save entities from meeting records:

```bash
# Ingest from URL
archive-rag ingest-entities "https://raw.githubusercontent.com/.../meeting-summaries-array.json"

# This will:
# - Extract all meetings, workgroups, people, documents, agenda items, decisions, and action items
# - Save them to entities/ directory
# - Create relationships between entities
# - Generate index files for fast queries
```

### Query Capabilities

The system supports both:

1. **Quantitative Queries**: Direct counts and statistics from entity storage
   - "How many meetings are there?"
   - "How many decisions were made?"
   - "List all documents for Governance workgroup"

2. **Qualitative RAG Queries**: Semantic search and LLM-based answers
   - "What decisions were made about budget allocation?"
   - "What topics were discussed in recent meetings?"

All queries include proper citations with data sources and calculation methods.

## Requirements

- Python 3.11+ (tested with Python 3.11, 3.12, and 3.13)
- 4GB+ RAM available
- Meeting JSON files in required format (see data-model.md)

## License

[To be specified]

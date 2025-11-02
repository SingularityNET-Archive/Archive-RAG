# Using Meeting Data

## Official Sample Data Source

The Archive-RAG system uses the **SingularityNET Archive** GitHub repository as the official source for sample data:

**Source URL**: `https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json`

This URL contains 120+ meetings from various workgroups (Archives, Governance, Education, African Guild, etc.) in the official Archives Workgroup format.

## Quick Start with Sample Data

### Index Sample Data from GitHub

```bash
# Index all meetings from the official GitHub source
archive-rag index "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" indexes/sample-meetings.faiss --no-redact-pii

# Query the indexed data
archive-rag query indexes/sample-meetings.faiss "What decisions were made in the Archives Workgroup?"
```

## Using Your Own Data

You can still use your own meeting data files. The system supports both the **Archives Workgroup Format** (used in the GitHub source) and a **Legacy Format**.

### Supported Formats

#### Format 1: Archives Workgroup Format (Recommended)

This is the format used in the GitHub source. See the [data model specification](../../specs/001-entity-data-model/spec.md) for details.

#### Format 2: Legacy Format

For backward compatibility with simpler meeting records:

```json
{
  "id": "meeting_001",
  "date": "2024-03-15T10:00:00Z",
  "participants": ["Alice", "Bob", "Charlie"],
  "transcript": "Full meeting transcript text here...",
  "decisions": ["Decision 1", "Decision 2"],
  "tags": ["tag1", "tag2"]
}
```

### Indexing Your Own Data

```bash
# From a local directory
archive-rag index your-data-directory/ indexes/my-index.faiss

# From a URL (single file or array)
archive-rag index "https://example.com/meetings.json" indexes/my-index.faiss

# With PII redaction (recommended for production)
archive-rag index --redact-pii your-data-directory/ indexes/my-index.faiss
```

## Data Format Details

### Archives Workgroup Format

The GitHub source uses this format, which includes:
- **Workgroup** information
- **Meeting metadata** (host, documenter, participants, purpose, video links)
- **Agenda items** with action items and decision items
- **Documents** (working docs linked to meetings)
- **Tags** (topics and emotions)

The system automatically:
- Extracts `id` from `workgroup_id`
- Converts `date` from YYYY-MM-DD to ISO 8601
- Parses `participants` from comma-separated `peoplePresent` string
- Builds `transcript` from `agendaItems[].decisionItems[].decision` texts
- Extracts `decisions` from decision items

### Legacy Format

For simpler use cases:
- Direct `transcript` field
- Array of `participants`
- ISO 8601 `date` format
- Optional `decisions` and `tags` arrays

## Querying Indexed Data

```bash
# Query by question
archive-rag query indexes/sample-meetings.faiss "What were the key topics in January 2025?"

# Query with output format
archive-rag query indexes/sample-meetings.faiss "Who participated in governance meetings?" --output-format json
```

## Notes

- You can mix both formats in the same directory - the system detects and handles them automatically
- Empty or missing transcripts are automatically skipped during indexing
- The GitHub source is updated regularly with new meeting summaries
- For production use, always use PII redaction: `--redact-pii`

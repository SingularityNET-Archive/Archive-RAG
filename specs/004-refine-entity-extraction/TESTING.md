# Testing Entity Extraction Implementation Phases

This document describes how to test each phase of the entity extraction implementation using the terminal test command.

## Quick Start

Test all phases with a single meeting from the GitHub source:

```bash
archive-rag test-entity-extraction \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  --phases all
```

Test specific phases:

```bash
archive-rag test-entity-extraction \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  --phases US1,US2,US3
```

Test a different meeting (by index):

```bash
archive-rag test-entity-extraction \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  --phases all \
  --meeting-index 5
```

Save results to JSON file:

```bash
archive-rag test-entity-extraction \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  --phases all \
  --output test-results.json
```

## Available Phases

### US1: Extract Entities from JSON Structure
- Tests entity extraction from JSON objects
- Verifies entity filtering criteria
- Shows extracted entities (workgroup, meeting, people, documents, decisions, actions)

### US2: Capture Entity Relationships
- Tests relationship triple generation
- Verifies relationship types (Workgroup → Meeting, Meeting → People, etc.)
- Shows sample relationship triples

### US3: Normalize Entity References
- Tests entity name normalization
- Verifies fuzzy similarity matching (>95%)
- Shows normalization examples (e.g., "Stephen [QADAO]" → "Stephen")

### US4: Apply Named Entity Recognition to Text Fields
- Tests NER extraction from unstructured text
- Verifies entity extraction from meeting purpose, decision text, etc.
- Shows extracted NER entities with confidence scores

### US5: Chunk Text by Semantic Unit Before Embedding
- Tests semantic chunking (meeting summary, action items, decisions, etc.)
- Verifies entity context preservation in chunks
- Shows chunk types and counts

### US6: Generate Structured Entity Output
- Tests complete structured output generation
- Verifies all components (entities, normalized labels, relationship triples, chunks)
- Shows summary statistics

## Command Options

- `source_url` (required): URL to source JSON file containing meetings
- `--phases`: Comma-separated list of phases to test (e.g., "US1,US2,US3") or "all" (default: all)
- `--meeting-index`: Index of meeting to test (0-based, default: 0)
- `--output`: Path to JSON file to save test results
- `--verify-hash`: Optional SHA-256 hash to verify source file integrity

## Example Output

```
============================================================
Entity Extraction Implementation Test
============================================================

Source URL: https://raw.githubusercontent.com/...

Fetching meeting data...
Using meeting at index 0

============================================================
Phase: US1
Extract Entities from JSON Structure
============================================================
✓ Entity extraction completed
  Extracted 2 entities
  Workgroup: Archives Workgroup (05ddaaf0-1dde-4d84-a722-f82c8479a8e9)
  Meeting: Meeting 2025-01-08 (880e8400-e29b-41d4-a716-446655440000)

============================================================
Phase: US2
Capture Entity Relationships
============================================================
✓ Relationship extraction completed
  Generated 3 relationship triples

  Sample relationships:
    Archives Workgroup (Workgroup) --[held]--> Meeting 2025-01-08 (Meeting)
    Meeting (Meeting) --[has]--> Action Item (ActionItem)
    Decision (Decision) --[has_effect]--> mayAffectOtherPeople (Effect)

...
```

## Troubleshooting

### spaCy Model Not Found
If you see an error about a missing spaCy model:
```bash
python -m spacy download en_core_web_sm
```

### Entity Storage Not Found
If entities aren't found, make sure you've ingested meetings first:
```bash
archive-rag ingest-entities "https://raw.githubusercontent.com/..."
```

### No Relationships Found
If US2 shows no relationships, this may be expected if:
- The meeting doesn't have action items or decisions
- Relationship triple generation is not yet fully implemented
- Entities need to be loaded from storage first

## Next Steps

After testing, you can:
1. Review the test results to verify each phase is working
2. Check entity storage directories to see created entities
3. Use `query-entity` commands to query extracted entities
4. Continue with implementation of remaining phases


# Quickstart: Refine Entity Extraction

**Feature**: Refine Entity Extraction  
**Date**: 2025-01-21  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

This feature enhances entity extraction from meeting records with:
- **Entity normalization**: Merges name variations (e.g., "Stephen" and "Stephen [QADAO]") into canonical entities
- **NER integration**: Extracts additional entities from unstructured text fields using Named Entity Recognition
- **Relationship triples**: Generates relationship triples (e.g., "Person -> attended -> Meeting")
- **Semantic chunking**: Chunks meeting content by semantic units with embedded entity metadata

## Prerequisites

- Python 3.11+ installed
- Archive-RAG dependencies installed (`pip install -r requirements.txt`)
- spaCy model installed: `python -m spacy download en_core_web_sm`
- New dependency: `rapidfuzz>=3.0.0` (for entity name similarity matching)

## Installation

```bash
# Install new dependency
pip install rapidfuzz>=3.0.0

# Verify spaCy model is installed
python -m spacy download en_core_web_sm
```

## Usage

### Automatic Entity Extraction with Normalization

Entity extraction and normalization happens automatically during meeting record ingestion:

```bash
# Ingest meetings with enhanced entity extraction
archive-rag ingest-entities \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json"

# Ingest meetings and generate structured output JSON
archive-rag ingest-entities \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  --output-json structured-output.json
```

**What happens automatically**:
1. Extracts entities from JSON structure (workgroups, meetings, people, documents, decisions, action items)
2. Applies NER to text fields (purpose, decision text, action descriptions)
3. Normalizes entity name variations (merges "Stephen" and "Stephen [QADAO]" into canonical "Stephen")
4. Generates relationship triples (Workgroup → Meeting, Person → Meeting, Workgroup → Decision/Action)
5. Creates semantic chunks with entity metadata
6. Tracks processing time (target: <2 seconds per meeting)
7. Handles missing fields gracefully (skips without failing)

### Test Entity Extraction

Test entity extraction features:

```bash
# Test all phases of entity extraction
archive-rag test-entity-extraction \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json"

# Test specific meeting by index
archive-rag test-entity-extraction \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  --meeting-index 0

# Test multiple random meetings
archive-rag test-entity-extraction \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  --random 5

# Test semantic chunking impact on queries
archive-rag test-semantic-chunking \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json"
```

### Generate Structured Output

Generate complete structured output including relationship triples:

```bash
# Generate structured output JSON
archive-rag ingest-entities \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  --output-json output.json

# Output includes:
# - structured_entity_list: All extracted entities
# - normalized_cluster_labels: Canonical names and variations
# - relationship_triples: All relationship triples (Workgroup → Meeting, Person → Meeting, Workgroup → Decision/Action, etc.)
# - chunks_for_embedding: Semantic chunks with entity metadata
```

### Semantic Chunking with Entity Metadata

Semantic chunks are created automatically during indexing with embedded entity metadata:

```bash
# Index meetings with semantic chunking
archive-rag index \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  indexes/meetings.faiss \
  --semantic-chunking
```

**Chunk structure**:
- Meeting summary chunks: `meetingInfo.purpose` → single chunk
- Action item chunks: Each `actionItems[]` item → separate chunk
- Decision record chunks: Each `decisionItems[]` item → separate chunk
- Attendance chunks: `peoplePresent` list → single chunk
- Resource chunks: Each `workingDocs[]` item → separate chunk

Each chunk includes:
- Entity mentions in chunk text
- Normalized entity references
- Relationship context

### View Normalized Entity Clusters

View how entity name variations are normalized:

```bash
# View normalization clusters
archive-rag view-normalization-clusters

# Output:
# Entity Cluster: Stephen
#   Variations: ["Stephen", "Stephen [QADAO]", "Stephen QADAO"]
#   Canonical: "Stephen"
#   Entity ID: uuid
#   Appears in: 15 meetings
```

## Configuration

### Normalization Settings

Configure entity normalization behavior:

```python
# In config.py or environment variables
ENTITY_NORMALIZATION = {
    "similarity_threshold": 0.95,  # Minimum similarity for fuzzy matching
    "pattern_rules": [
        r"\[QADAO\]",  # Remove [QADAO] suffix
        r"\[ORG\]",     # Remove [ORG] suffix
    ],
    "enable_fuzzy_matching": True,
    "enable_context_disambiguation": True
}
```

### NER Settings

Configure NER extraction:

```python
NER_CONFIG = {
    "model_name": "en_core_web_sm",
    "entity_types": ["PERSON", "ORG", "GPE", "DATE"],
    "min_confidence": 0.7,
    "filter_criteria": "any"  # OR logic: extract if meets any criterion
}
```

### Chunking Settings

Configure semantic chunking:

```python
CHUNKING_CONFIG = {
    "max_tokens_per_chunk": 512,
    "split_at_sentence_boundaries": True,
    "preserve_entity_context": True,
    "chunk_types": [
        "meeting_summary",
        "action_item",
        "decision_record",
        "attendance",
        "resource"
    ]
}
```

## Examples

### Example 1: Normalize Person Name Variations

**Input** (meeting records):
- Meeting 1: `peoplePresent: "Stephen, Alice, Bob"`
- Meeting 2: `peoplePresent: "Stephen [QADAO], Alice, Charlie"`
- Meeting 3: `peoplePresent: "Stephen QADAO, Alice, Bob"`

**Output** (normalized entities):
- Person: `{id: uuid, display_name: "Stephen", normalized_variations: ["Stephen", "Stephen [QADAO]", "Stephen QADAO"]}`
- Person: `{id: uuid, display_name: "Alice", normalized_variations: ["Alice"]}`

**Query result**:
```bash
archive-rag query-person "Stephen"  # Returns all 3 meetings
archive-rag query-person "Stephen [QADAO]"  # Same result
```

### Example 2: NER Entity Extraction

**Input** (meeting purpose):
```
"Discuss QADAO budget proposal and coordinate with SingularityNET team"
```

**NER Extracted Entities**:
- `QADAO` (ORG)
- `SingularityNET` (ORG)

**Output**: These entities are normalized and merged with structured JSON entities if they match.

### Example 3: Relationship Triples

**Input**: Meeting with workgroup, attendees, decisions, action items

**Output** (relationship triples):
```json
{
  "triples": [
    {"subject": "Workgroup", "relationship": "held", "object": "Meeting"},
    {"subject": "Person", "relationship": "attended", "object": "Meeting"},
    {"subject": "Meeting", "relationship": "produced", "object": "Decision"},
    {"subject": "ActionItem", "relationship": "assigned_to", "object": "Person"}
  ]
}
```

### Example 4: Semantic Chunk with Entity Metadata

**Input**: Action item from meeting

**Output** (chunk):
```json
{
  "text": "Stephen will review budget proposal by next week",
  "entities": [
    {
      "entity_id": "uuid",
      "entity_type": "Person",
      "normalized_name": "Stephen",
      "mentions": ["Stephen"]
    }
  ],
  "metadata": {
    "meeting_id": "uuid",
    "chunk_type": "action_item",
    "source_field": "agendaItems[0].actionItems[0]",
    "relationships": [
      {"subject": "Person", "relationship": "assigned_to", "object": "ActionItem"}
    ]
  }
}
```

## Troubleshooting

### Entity Normalization Issues

**Problem**: Entities not being normalized correctly

**Solution**:
```bash
# Check normalization rules
archive-rag check-normalization-rules

# Manual normalization override (future feature)
archive-rag normalize-entity --name "Stephen [QADAO]" --canonical "Stephen"
```

### NER Extraction Issues

**Problem**: NER not extracting expected entities

**Solution**:
```bash
# Verify spaCy model is installed
python -m spacy download en_core_web_sm

# Test NER extraction
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); doc = nlp('Discuss QADAO budget'); print([(ent.text, ent.label_) for ent in doc.ents])"
```

### Chunk Splitting Issues

**Problem**: Chunks exceeding token limits not being split correctly

**Solution**:
- Verify `split_at_sentence_boundaries` is enabled
- Check chunk metadata includes entity context after splitting
- Review chunk splitting logic in logs

## Performance

**Expected Processing Time**:
- <2 seconds per meeting record for complete entity extraction, normalization, and chunking
- ~4 minutes total for 120 meeting records (batch processing)
- Performance is logged automatically - warnings are issued if processing exceeds 2 seconds per meeting

**Optimization Features**:
- Entity normalization uses caching for faster lookups (T082)
- NER processing is fast (<100ms per text field)
- Chunking is efficient (JSON structure-based boundaries)
- Context-based disambiguation uses workgroup associations for better entity matching (T080)

**Error Handling**:
- Missing entity fields are handled gracefully (skipped without failing) (T077)
- Malformed JSON is handled with detailed error logging (T078)
- Incomplete relationship data (missing assignee, effect) is handled gracefully (T079)
- Comprehensive logging with traceability to source meeting records (T083)

## Next Steps

1. **Ingest meetings** with enhanced entity extraction
2. **Query normalized entities** using any name variation
3. **Generate relationship triples** for analysis
4. **Use semantic chunks** for improved embedding quality

For detailed implementation information, see [plan.md](plan.md) and [data-model.md](data-model.md).


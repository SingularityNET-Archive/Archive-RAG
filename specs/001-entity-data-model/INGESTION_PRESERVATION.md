# URL Ingestion Preservation

**Feature**: Entity-Based Data Model  
**Date**: 2025-11-02  
**Purpose**: Ensure URL ingestion from GitHub source continues to work

## Overview

The entity-based data model must preserve existing URL ingestion functionality, specifically the ability to ingest meeting data directly from the GitHub URL:

**GitHub Source URL**:  
`https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json`

## Current URL Ingestion Flow

### Existing Implementation

The current ingestion service (`src/services/ingestion.py`) already supports URL ingestion:

1. **`ingest_meeting_directory()`** - Detects if input is URL or directory path
2. **`ingest_meeting_url()`** - Fetches JSON array from URL
3. **`MeetingRecord`** - Parses each meeting object in array
4. **Chunking & Embedding** - Processes for RAG indexing

### Current URL Support

- ✅ Detects URLs (http://, https://, handles Path normalization)
- ✅ Fetches JSON from URL with timeout (30 seconds)
- ✅ Handles JSON arrays or single objects
- ✅ Parses each meeting as `MeetingRecord` (supports both legacy and new format)
- ✅ Computes SHA-256 hash for tamper detection
- ✅ Error handling with continued processing on individual failures

## Entity-Based Model Integration

### Updated Flow (Preserving URL Ingestion)

The entity-based model will enhance the ingestion flow without breaking URL support:

1. **URL Detection** (unchanged):
   ```python
   # ingest_meeting_directory() detects URL
   is_url = directory_str.startswith("http://") or directory_str.startswith("https://")
   if is_url:
       return ingest_meeting_url(directory_str, verify_hash)
   ```

2. **URL Fetching** (unchanged):
   ```python
   # ingest_meeting_url() fetches JSON array
   with urllib.request.urlopen(url, timeout=30) as response:
       data_bytes = response.read()
       data_text = data_bytes.decode('utf-8')
   data = json.loads(data_text)  # Array of meeting objects
   ```

3. **Entity Conversion** (NEW):
   ```python
   # For each meeting in array:
   for meeting_data in data:
       # Parse as MeetingRecord (supports both formats)
       meeting_record = MeetingRecord(**meeting_data)
       
       # Convert to entity JSON files (NEW)
       entity_storage.save_meeting_entity(meeting_record)
       # - Creates/updates Workgroup JSON file
       # - Creates/updates Meeting JSON file
       # - Creates/updates Person JSON files (from peoplePresent)
       # - Creates/updates Document JSON files (from workingDocs)
       # - Creates/updates AgendaItem, ActionItem, DecisionItem JSON files
       # - Creates/updates Tag JSON file
       # - Updates index files
   ```

4. **RAG Indexing** (unchanged):
   ```python
   # Extract transcript from DecisionItems (via entities)
   transcript = extract_transcript_from_entities(meeting_record)
   chunks = chunk_transcript(meeting_record, transcript)
   # Continue with embedding and indexing
   ```

## Implementation Requirements

### Must Preserve

- ✅ URL ingestion from GitHub source
- ✅ JSON array parsing
- ✅ Both legacy and new format support
- ✅ Error handling (continue on individual failures)
- ✅ Hash verification (optional)
- ✅ CLI command compatibility (`archive-rag index <url>`)

### New Functionality

- ✅ Convert MeetingRecord to entity JSON files
- ✅ Create related entity JSON files (Workgroup, Person, etc.)
- ✅ Update index files for fast lookups
- ✅ Maintain referential integrity during URL ingestion

## Example Usage (Unchanged)

```bash
# URL ingestion continues to work
archive-rag index \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  indexes/github-meetings.faiss \
  --no-redact-pii

# With entity model (NEW flag)
archive-rag index \
  --use-entities \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" \
  indexes/github-entity-meetings.faiss \
  --no-redact-pii
```

## Data Flow

### GitHub JSON Structure

```json
[
  {
    "workgroup": "Archives Workgroup",
    "workgroup_id": "05ddaaf0-1dde-4d84-a722-f82c8479a8e9",
    "meetingInfo": {
      "date": "2025-01-08",
      "peoplePresent": "André, CallyFromAuron, Stephen [QADAO], ...",
      "workingDocs": [...],
      ...
    },
    "agendaItems": [
      {
        "decisionItems": [
          {
            "decision": "...",
            "effect": "mayAffectOtherPeople"
          }
        ],
        "actionItems": [...]
      }
    ],
    "tags": {
      "topicsCovered": "...",
      "emotions": "..."
    }
  },
  ...
]
```

### Entity JSON Files Created

For each meeting in the array, the system creates:

1. **`entities/workgroups/{workgroup_id}.json`** - Workgroup entity
2. **`entities/meetings/{meeting_id}.json`** - Meeting entity
3. **`entities/people/{person_id}.json`** - Person entities (from peoplePresent)
4. **`entities/documents/{document_id}.json`** - Document entities (from workingDocs)
5. **`entities/agenda_items/{agenda_item_id}.json`** - AgendaItem entities
6. **`entities/action_items/{action_item_id}.json`** - ActionItem entities
7. **`entities/decision_items/{decision_item_id}.json`** - DecisionItem entities
8. **`entities/tags/{tag_id}.json`** - Tag entity
9. **`entities/_relations/meeting_person.json`** - Meeting-Person relationships
10. **`entities/_index/*.json`** - Index files for fast lookups

## Validation

### Test Cases

1. ✅ **URL Ingestion Test**: Fetch from GitHub URL, verify all meetings ingested
2. ✅ **Entity Creation Test**: Verify entity JSON files created correctly
3. ✅ **Relationship Test**: Verify Meeting-Person relationships via junction file
4. ✅ **RAG Compatibility Test**: Verify RAG indexing works after entity conversion
5. ✅ **Error Handling Test**: Verify individual failures don't stop entire ingestion

### Success Criteria

- ✅ URL ingestion from GitHub source works identically to current implementation
- ✅ All meetings from GitHub array are converted to entity JSON files
- ✅ Related entities (Workgroup, Person, etc.) are created correctly
- ✅ Index files are updated for fast lookups
- ✅ RAG indexing continues to work after entity conversion
- ✅ Error handling preserves existing behavior (continue on failures)

## References

- **GitHub Source**: [meeting-summaries-array.json](https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json)
- **Current Ingestion Service**: `src/services/ingestion.py`
- **MeetingRecord Model**: `src/models/meeting_record.py`
- **Plan**: `plan.md`
- **Data Model**: `data-model.md`





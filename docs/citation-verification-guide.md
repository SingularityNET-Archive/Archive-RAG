# Citation Verification Guide

This guide explains how citation verification ensures queries are only returned when they have specific citations verified by entity extraction.

## Overview

Citation verification ensures that:
1. **Queries have valid citations** - Citations must reference actual meeting records (not "no-evidence" or system operations)
2. **Citations have entity extraction** - For RAG queries, citations must include entity extraction metadata (chunk_type, chunk_entities, chunk_relationships)
3. **Informative error messages** - Users receive clear explanations when verification fails

## How It Works

### Verification Process

When a query is executed:

1. **Query Execution** - Query is processed and results are retrieved
2. **Citation Verification** - Citations are verified before returning results:
   - Check if citations exist
   - Validate citation meeting IDs (must be valid UUIDs, not "no-evidence")
   - Verify entity extraction metadata is present (for RAG queries)
3. **Result Handling**:
   - ✅ **If verified**: Results are returned to the user
   - ❌ **If not verified**: Informative error message is returned instead

### Verification Rules

#### For RAG Queries (Standard Queries)
- **Requires**: Entity extraction metadata in citations
- **Checks**: `chunk_type`, `chunk_entities`, or `chunk_relationships` must be present
- **Purpose**: Ensures information can be traced to specific entities and relationships

#### For Entity-Based Queries (Topic Queries, Quantitative Queries)
- **Requires**: Valid citations with meeting IDs
- **Entity extraction**: Optional (may not be available for all entity queries)
- **Purpose**: Ensures results reference actual meeting records

## Error Messages

### No Citations Found

**Message:**
```
**No citations found.**

The query did not retrieve any specific meeting records to support the answer. 
This could mean:
- The query doesn't match any content in the archive
- The search terms need to be adjusted
- The relevant meetings may not be indexed yet

Please try rephrasing your question or using more specific search terms.
```

**When it occurs:**
- Query returns empty citation list
- No meeting records matched the query

### Invalid Citations

**Message:**
```
**No valid citations found.**

The query retrieved results, but they don't reference specific meeting records. 
This usually means:
- The search didn't find matching content in archived meetings
- The results are from system operations rather than meeting data

Please try:
- Using different search terms
- Being more specific about what you're looking for
- Checking if the relevant meetings have been indexed
```

**When it occurs:**
- Citations have invalid meeting IDs ("no-evidence", "entity-storage", etc.)
- Citations don't have valid UUID format

### Missing Entity Extraction

**Message:**
```
**Citations lack entity extraction verification.**

The query found meeting records, but they don't have entity extraction metadata 
to verify the information. This means:
- The citations cannot be verified against extracted entities
- Entity relationships and context are not available

This may occur if:
- The index was built without semantic chunking
- Entity extraction metadata is missing from the index

Please contact an administrator if this persists.
```

**When it occurs:**
- Citations exist but lack `chunk_type`, `chunk_entities`, or `chunk_relationships`
- Only affects RAG queries (not entity-based queries)

## Implementation Details

### Citation Verification Service

**File**: `src/services/citation_verifier.py`

**Key Functions:**
- `verify_citations_with_entity_extraction()` - Main verification function
- `get_verification_error_message()` - Generates user-friendly error messages

**Verification Steps:**
1. Check if citations exist
2. Filter invalid citations (no-evidence, entity-storage, etc.)
3. Validate meeting IDs (must be valid UUIDs)
4. Check entity extraction metadata (if required)
5. Return verification result with detailed status

### Integration Points

**Bot Command** (`src/bot/commands/query.py`):
- Verifies citations after query execution
- Returns error message if verification fails
- Only returns results if verification passes

**Query Service** (`src/services/query_service.py`):
- Creates citations with entity extraction metadata
- Ensures citations reference valid meetings

## Configuration

### Requiring Entity Extraction

By default, RAG queries require entity extraction metadata. This can be controlled:

```python
# Require entity extraction (default for RAG queries)
verification_result = verify_citations_with_entity_extraction(
    citations,
    require_entity_extraction=True
)

# Don't require entity extraction (for entity-based queries)
verification_result = verify_citations_with_entity_extraction(
    citations,
    require_entity_extraction=False
)
```

### Query Type Detection

The bot automatically detects query types:
- **RAG queries**: Require entity extraction
- **Entity queries** (`model_version="entity-query"`): Entity extraction optional
- **Quantitative queries** (`model_version="quantitative-query"`): Entity extraction optional

## Examples

### ✅ Verified Query

**Query**: "What decisions were made in the Archives Workgroup?"

**Result**: 
- Citations found: 3
- All citations have valid meeting IDs
- All citations have entity extraction metadata
- ✅ **Verified** - Results returned

### ❌ Missing Citations

**Query**: "What is the meaning of life?"

**Result**:
- Citations found: 0
- ❌ **Not verified** - Error message returned:
  ```
  **No citations found.**
  The query did not retrieve any specific meeting records...
  ```

### ❌ Invalid Citations

**Query**: "Count all meetings"

**Result** (if improperly handled):
- Citations found: 1
- Citation meeting_id: "quantitative-analysis"
- ❌ **Not verified** - Error message returned:
  ```
  **No valid citations found.**
  The query retrieved results, but they don't reference specific meeting records...
  ```

### ❌ Missing Entity Extraction

**Query**: "What topics were discussed?"

**Result** (if index lacks entity extraction):
- Citations found: 5
- All citations have valid meeting IDs
- No citations have `chunk_type` or `chunk_entities`
- ❌ **Not verified** - Error message returned:
  ```
  **Citations lack entity extraction verification.**
  The query found meeting records, but they don't have entity extraction metadata...
  ```

## Troubleshooting

### Citations Not Being Verified

**Symptoms**: Queries return results without verification

**Solutions**:
1. Check that `verify_citations_with_entity_extraction()` is called in `query.py`
2. Verify `require_entity_extraction` parameter is set correctly
3. Check logs for `citation_verification_failed` messages

### False Positives (Valid Queries Rejected)

**Symptoms**: Valid queries with proper citations are rejected

**Solutions**:
1. Check if entity extraction metadata is being included in citations
2. Verify index was built with semantic chunking enabled
3. Check if query type detection is working correctly
4. Review citation creation in `query_service.py`

### Missing Entity Extraction Metadata

**Symptoms**: Citations exist but lack entity extraction

**Solutions**:
1. Rebuild index with semantic chunking enabled
2. Verify `chunk_type`, `chunk_entities` are populated in citations
3. Check `citation_extractor.py` includes entity metadata
4. Ensure Phase 7 implementation is complete

## Best Practices

1. **Always verify citations** - Never return results without citation verification
2. **Provide clear error messages** - Help users understand what went wrong
3. **Log verification failures** - Track when and why verification fails
4. **Test with various query types** - Ensure verification works for all query types
5. **Monitor verification rates** - Track how often verification fails

## Related Documentation

- [Phase 7: Semantic Chunk Context](./discord-bot-phase6-testing-guide.md)
- [Citation Format Specification](../specs/001-archive-meeting-rag/data-model.md)
- [Entity Extraction](../specs/004-refine-entity-extraction/spec.md)


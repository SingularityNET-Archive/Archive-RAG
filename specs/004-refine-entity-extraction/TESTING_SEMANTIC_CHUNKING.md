# Testing Semantic Chunking vs Token-Based Chunking

This document describes how to test the effect of semantic chunking on query results.

## Overview

The `test-semantic-chunking` command allows you to:
1. Index meetings using both semantic chunking and token-based chunking
2. Run test queries on both indices
3. Compare results showing entity metadata, relationships, and retrieval scores

## Usage

### Basic Usage with Official Source

```bash
# Use the official SingularityNET Archive source (120+ meetings)
archive-rag test-semantic-chunking \
  "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json"
```

### Basic Usage with Custom Source

```bash
archive-rag test-semantic-chunking <source_url>
```

### With Custom Queries

```bash
archive-rag test-semantic-chunking <source_url> \
  --queries "What decisions were made?,Who attended?,What action items?"
```

### With Options

```bash
archive-rag test-semantic-chunking <source_url> \
  --queries "What decisions were made?" \
  --top-k 10 \
  --meeting-limit 5 \
  --output-dir ./my_test_indices \
  --chunk-size 512 \
  --chunk-overlap 50
```

## Command Options

- `source_url` (required): URL to source JSON file containing meetings
- `--queries`: Comma-separated list of queries to test (default: built-in test queries)
- `--top-k`: Number of chunks to retrieve per query (default: 5)
- `--embedding-model`: Embedding model name (default: "sentence-transformers/all-MiniLM-L6-v2")
- `--chunk-size`: Chunk size for token-based chunking (default: 512)
- `--chunk-overlap`: Overlap for token-based chunking (default: 50)
- `--meeting-limit`: Limit number of meetings to process (for faster testing)
- `--output-dir`: Directory to save index files (default: ./test_indices)

## Default Test Queries

If no custom queries are provided, the following queries are used:
1. "What decisions were made?"
2. "Who attended the meetings?"
3. "What action items were assigned?"
4. "What workgroups are involved?"
5. "What documents were discussed?"

## Output

The command provides:
1. **Indexing Results**: Shows how many chunks were created for each method
2. **Query Results**: For each query, shows:
   - Retrieved chunks from semantic chunking
   - Retrieved chunks from token-based chunking
   - Comparison of average scores
   - Entity metadata in semantic chunks
   - Relationship metadata in semantic chunks
3. **Summary**: Total statistics and index file locations

## Example Output

```
======================================================================
Semantic Chunking Query Test
======================================================================

Step 1: Indexing with Semantic Chunking
  ✓ Meeting 1/5: 12 semantic chunks
  ✓ Meeting 2/5: 8 semantic chunks
  ...
  ✓ Created 45 semantic chunks total

Step 2: Indexing with Token-Based Chunking
  ✓ Meeting 1/5: 15 token chunks
  ✓ Meeting 2/5: 10 token chunks
  ...
  ✓ Created 60 token chunks total

Step 3: Running Test Queries
----------------------------------------------------------------------
Query: What decisions were made?
----------------------------------------------------------------------

[Semantic Chunking Results]
  Retrieved 5 chunks:
    [1] Score: 0.8234
        Text: The team decided to implement...
        Meeting ID: abc-123-def
        Chunk Type: decision_record
        Source Field: agendaItems[0].decisionItems[0]
        Entities: 3 entity(ies) mentioned
          - Archives Workgroup (Workgroup)
          - Stephen (Person)
          - Meeting Decision (DecisionItem)
        Relationships: 2 relationship(s)
          - Workgroup -> made -> Decision
          - Person -> attended -> Meeting

[Token-Based Chunking Results]
  Retrieved 5 chunks:
    [1] Score: 0.7812
        Text: The team decided to implement...
        Meeting ID: abc-123-def

[Comparison]
  Average semantic chunk score: 0.8234
  Average token chunk score: 0.7812
  Difference: +0.0422
  Semantic chunks with entities: 5/5
```

## Understanding the Results

### Semantic Chunking Advantages

1. **Entity Metadata**: Semantic chunks include embedded entity information, making it easier to understand context
2. **Relationship Information**: Chunks include relationship triples showing how entities relate
3. **Better Retrieval**: Semantic chunks may have higher retrieval scores for entity-focused queries
4. **Structured Context**: Each chunk is aligned with semantic units (decisions, actions, etc.) rather than arbitrary token boundaries

### Token-Based Chunking Characteristics

1. **Simple Splitting**: Chunks are split at fixed token boundaries
2. **No Entity Metadata**: Chunks don't include structured entity information
3. **Consistent Sizing**: Chunks are more uniform in size

## Index Files

The command creates two index files:
- `{output_dir}/semantic_index.faiss` - Semantic chunking index
- `{output_dir}/token_index.faiss` - Token-based chunking index

These can be reused for further testing or analysis.

## Tips

1. **Start Small**: Use `--meeting-limit` to test with a few meetings first
2. **Custom Queries**: Provide queries relevant to your use case
3. **Compare Scores**: Look at the difference in average scores - positive differences indicate semantic chunking is better for that query
4. **Entity Coverage**: Check how many semantic chunks have entities embedded - this shows the effectiveness of entity extraction

## Troubleshooting

- **No chunks created**: Ensure meetings have content (purpose, action items, decisions, etc.)
- **Empty results**: Check that meetings have been properly ingested and entities extracted
- **Import errors**: Ensure all dependencies are installed (`pip install -r requirements.txt`)


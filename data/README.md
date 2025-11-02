# Using Your Own Meeting Data

## Data Format

Each meeting must be a JSON file following this format:

```json
{
  "id": "unique-meeting-id",
  "date": "2024-03-15T10:00:00Z",
  "participants": ["Participant 1", "Participant 2"],
  "transcript": "Full meeting transcript text here...",
  "decisions": ["Decision 1", "Decision 2"],
  "tags": ["tag1", "tag2"]
}
```

### Required Fields

- **`id`** (string): Unique meeting identifier (e.g., "meeting_001", "2024-03-15-board-meeting")
- **`date`** (string): ISO 8601 datetime format (e.g., "2024-03-15T10:00:00Z")
- **`participants`** (array): List of participant names or IDs (must have at least one)
- **`transcript`** (string): Full meeting transcript text (cannot be empty)

### Optional Fields

- **`decisions`** (array): List of decisions made in the meeting
- **`tags`** (array): Categorization tags for the meeting

## Step-by-Step Instructions

### 1. Prepare Your Meeting JSON Files

Create JSON files following the format above. You can:

- Replace files in `data/sample/` directory
- Create a new directory (e.g., `data/my-meetings/`)
- Use any directory structure you prefer

### 2. Index Your Data

```bash
# Replace sample data
archive-rag index data/sample/ indexes/my-index.faiss

# Or use your own directory
archive-rag index data/my-meetings/ indexes/my-index.faiss

# With PII redaction (recommended)
archive-rag index --redact-pii data/my-meetings/ indexes/my-index.faiss
```

### 3. Query Your Data

```bash
archive-rag query indexes/my-index.faiss "Your question here"
```

## Date Format Examples

Valid ISO 8601 formats:
- `"2024-03-15T10:00:00Z"`
- `"2024-03-15T10:00:00+00:00"`
- `"2024-03-15"` (date only)

## Tips

1. **Multiple Files**: Put all your meeting JSON files in one directory - the indexer will process all `.json` files
2. **Large Transcripts**: The system automatically chunks long transcripts (default: 512 characters with 50 character overlap)
3. **PII Redaction**: Use `--redact-pii` flag if your transcripts contain personal information
4. **Validation**: Invalid JSON files will be skipped with error messages - check the output for warnings

## Example Directory Structure

```
data/
├── my-meetings/
│   ├── meeting_2024_01_15.json
│   ├── meeting_2024_02_20.json
│   └── meeting_2024_03_10.json
└── sample/  (example files)
    ├── meeting_001.json
    └── meeting_002.json
```

Then index with:
```bash
archive-rag index data/my-meetings/ indexes/my-meetings.faiss
```


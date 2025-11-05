# Discord Bot List Command Guide

## Overview

The `/archive list` command allows users to request lists of entities using natural language queries. This feature enables users to discover what topics, meetings, and other entities exist in the archive.

## Command Syntax

```
/archive list query:"<natural language query>"
```

## Supported List Queries

### List Topics

**Examples:**
```
/archive list query:"List extant topics"
/archive list query:"List all topics"
/archive list query:"List topics"
/archive list query:"Show me all topics"
```

**Response Format:**
```
Topics: (45 total)

1. budget allocation
2. collaboration
3. decision making
4. governance
5. meeting documentation
...
(Showing first 50 of 45 topics)
```

**Requirements:**
- Tags must exist in `entities/tags/` directory
- Tags must have `topics_covered` field populated
- If no tags exist, you'll need to backfill tags from source data (see below)

### List Meetings by Date

**Examples:**
```
/archive list query:"List meetings in March 2025"
/archive list query:"List meetings in 2025"
/archive list query:"Show meetings from January 2024"
/archive list query:"List meetings in March"
```

**Response Format:**
```
Meetings: (12 total)

1. [meeting_id_1 | 2025-03-15 | Archives Workgroup]
2. [meeting_id_2 | 2025-03-08 | Governance Workgroup]
3. [meeting_id_3 | 2025-03-01 | Education Workgroup]
...
(Showing first 20 of 12 meetings)
```

**Date Parsing:**
- Supports full month names: "January", "February", "March", etc.
- Supports abbreviated names: "Jan", "Feb", "Mar", etc.
- Supports year-only: "2025" returns all meetings in that year
- Supports month + year: "March 2025" returns meetings in that month
- If month is specified without year, uses current year

## Features

### Natural Language Processing
- Automatically detects list type (topics vs meetings) from query text
- Parses dates from natural language phrases
- Handles various query phrasings

### Rate Limiting
- Same 10 queries/minute limit as other commands
- Applies across all bot commands (shared limit)

### Timeout Protection
- 30-second timeout for all operations
- User-friendly timeout error messages

### Error Handling
- Clear error messages for unknown list types
- Helpful suggestions when queries don't match
- Graceful handling of missing data

## Setup Requirements

### Prerequisites

1. **Tags must exist**: For topic listing, tag entities must be created
2. **Meetings must exist**: For meeting listing, meeting entities must exist

### Creating Tags

If you see "No topics found in the archive", you need to create tag entities. Tags are extracted from meeting source data during ingestion.

**Option 1: Re-ingest with tag extraction (Recommended)**

If your source data includes tags, use the backfill command:

```bash
archive-rag backfill-tags "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json"
```

This will:
- Process all meetings from the source URL
- Extract tags from meeting records
- Create tag entities in `entities/tags/`
- Preserve existing meetings (won't duplicate)

**Option 2: Full re-ingestion**

If you want to re-ingest everything:

```bash
archive-rag ingest-entities "https://raw.githubusercontent.com/..."
```

**Verify tags were created:**

```bash
# Count tag files
find entities/tags -name "*.json" | wc -l

# List a few tag files
ls entities/tags/ | head -5

# Check a tag file content
cat entities/tags/$(ls entities/tags/ | head -1) | python -m json.tool
```

## Troubleshooting

### "No topics found in the archive"

**Cause**: No tag entities exist in `entities/tags/` directory.

**Solution**: 
1. Check if source data has tags: Look for `tags` field in source JSON
2. Run backfill command: `archive-rag backfill-tags <source_url>`
3. Verify tags created: `ls entities/tags/`

### "No meetings found matching your criteria"

**Cause**: No meetings match the date criteria.

**Solutions**:
- Try a different date range
- Check what meetings exist: `ls entities/meetings/ | head -10`
- Verify date format in query (e.g., "March 2025" not "3/2025")

### "Unable to determine list type"

**Cause**: Query doesn't match known patterns for topics or meetings.

**Solution**: 
- Use clearer queries:
  - Topics: "List topics", "List all topics", "List extant topics"
  - Meetings: "List meetings in March 2025", "List meetings in 2025"

### Commands not appearing in Discord

**Cause**: Discord hasn't synced commands yet.

**Solutions**:
- Wait up to 1 hour for global command sync
- Restart bot to force sync
- Re-invite bot with OAuth2 URL

## Usage Examples

### Example 1: List All Topics

```
User: /archive list query:"List extant topics"
Bot: Processing your list query...

Bot: Topics: (45 total)

1. budget allocation
2. collaboration
3. decision making
4. governance
5. meeting documentation
...
(Showing first 50 of 45 topics)
```

### Example 2: List Meetings by Month

```
User: /archive list query:"List meetings in March 2025"
Bot: Processing your list query...

Bot: Meetings: (12 total)

1. [37d27c81-1073-5299-4d67-69b6470b69a8 | 2025-03-15 | Archives Workgroup]
2. [8a2f3b12-9876-5432-1abc-def012345678 | 2025-03-08 | Governance Workgroup]
...
(Showing first 20 of 12 meetings)
```

### Example 3: List Meetings by Year

```
User: /archive list query:"List meetings in 2025"
Bot: Processing your list query...

Bot: Meetings: (120 total)

1. [meeting_id | 2025-12-15 | Workgroup]
2. [meeting_id | 2025-11-20 | Workgroup]
...
(Showing first 20 of 120 meetings)
```

## Implementation Details

### EntityQueryService Methods

- `get_all_topics()`: Extracts all unique topics from tag entities
- `get_meetings_by_date_range()`: Filters meetings by year, month, or date range

### List Command Handler

- `ListCommand` class in `src/bot/commands/list.py`
- Natural language parsing for list type detection
- Date parsing from natural language
- Formatted response generation

## Related Commands

- `/archive query` - Natural language questions (public)
- `/archive topics` - Search by topic (contributor+)
- `/archive people` - Search by person (contributor+)
- `/archive list` - List entities (public)

## Next Steps

After setting up tags:
1. Test topic listing: `/archive list query:"List topics"`
2. Test meeting listing: `/archive list query:"List meetings in 2025"`
3. Verify results match your expectations
4. Use topics to explore the archive via `/archive topics`


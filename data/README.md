# Using Your Own Meeting Data

## Supported Formats

The Archive-RAG system now supports **two formats**:

### Format 1: Legacy Format (Simple)

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

### Format 2: New Format (Archives Workgroup Format)

```json
{
  "workgroup": "Archives Workgroup",
  "workgroup_id": "05ddaaf0-1dde-4d84-a722-f82c8479a8e9",
  "meetingInfo": {
    "typeOfMeeting": "Monthly",
    "date": "2025-01-08",
    "host": "Stephen [QADAO]",
    "documenter": "CallyFromAuron",
    "peoplePresent": "André, CallyFromAuron, Stephen [QADAO]",
    "purpose": "Regular monthly meeting",
    "meetingVideoLink": "https://...",
    "workingDocs": [
      {
        "title": "Document Title",
        "link": "https://..."
      }
    ]
  },
  "agendaItems": [
    {
      "status": "carry over",
      "actionItems": [
        {
          "text": "Action item text",
          "assignee": "Name",
          "dueDate": "Date",
          "status": "todo"
        }
      ],
      "decisionItems": [
        {
          "decision": "Decision text extracted as transcript content",
          "effect": "mayAffectOtherPeople"
        }
      ]
    }
  ],
  "tags": {
    "topicsCovered": "topic1, topic2",
    "emotions": "interesting, friendly"
  },
  "type": "Custom",
  "noSummaryGiven": false,
  "canceledSummary": false
}
```

## How It Works

The system automatically detects which format you're using:

- **If you provide `workgroup_id` and `meetingInfo`**: Uses new format
  - Extracts `id` from `workgroup_id`
  - Extracts `date` from `meetingInfo.date` (converts YYYY-MM-DD to ISO 8601)
  - Extracts `participants` from `meetingInfo.peoplePresent` (comma-separated string)
  - Extracts `transcript` from all `agendaItems[].decisionItems[].decision` texts
  - Extracts `decisions` from decision items

- **If you provide `id`, `date`, `participants`, `transcript`**: Uses legacy format

## Step-by-Step Instructions

### 1. Prepare Your Meeting JSON Files

Create JSON files following either format above.

### 2. Index Your Data

```bash
# Index your files
archive-rag index your-data-directory/ indexes/my-index.faiss

# With PII redaction (recommended)
archive-rag index --redact-pii your-data-directory/ indexes/my-index.faiss
```

### 3. Query Your Data

```bash
archive-rag query indexes/my-index.faiss "Your question here"
```

## Date Format

- **Legacy format**: ISO 8601 datetime (e.g., `"2024-03-15T10:00:00Z"`)
- **New format**: YYYY-MM-DD date (e.g., `"2025-01-08"`) - automatically converted to ISO 8601

## Participants Format

- **Legacy format**: Array of strings (e.g., `["Alice", "Bob"]`)
- **New format**: Comma-separated string (e.g., `"André, CallyFromAuron, Stephen [QADAO]"`) - automatically parsed into array

## Transcript Content

- **Legacy format**: Direct `transcript` field
- **New format**: Extracted from `agendaItems[].decisionItems[].decision` - all decision texts are combined into a single transcript

## Example Directory Structure

```
data/
├── my-meetings/
│   ├── meeting-2024-01-15.json  (legacy format)
│   ├── meeting-2025-01-08.json   (new format)
│   └── ...
└── sample/  (example files)
    ├── meeting_001.json
    └── meeting_002.json
```

You can mix both formats in the same directory - the system handles them automatically!

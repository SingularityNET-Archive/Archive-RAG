# Entity Extraction and RAG Integration Guide

**Purpose**: This guide explains how entity extraction works with RAG retrieval, and provides a recommended approach for integrating a new JSON source to ensure all entities are identified, relationships are established, and RAG prompts are controlled with auditable citations.

---

## Overview: How RAG and Entity Extraction Work Together

### The Two-Path Query System

Archive-RAG uses a **dual-path query system** that combines semantic search (RAG) with structured entity queries:

1. **Semantic RAG Path** (for qualitative questions):
   - Query → Embedding → FAISS similarity search → Top chunks → LLM generation → Answer + Citations
   - Best for: "What decisions were made about budget allocation?"

2. **Entity Query Path** (for quantitative/structured questions):
   - Query → Entity detection → Direct entity storage lookup → Structured response
   - Best for: "List all decisions made by Governance workgroup in March 2025"

### Why Entity Extraction Matters

Entity extraction serves three critical functions:

1. **Query Routing**: Detects when a query should use entity storage (faster, more accurate) vs. semantic search
2. **Enhanced Citations**: Adds normalized entity names, relationships, and chunk context to citations
3. **Audit Trail**: Provides structured, verifiable references that can be traced back to source JSON

---

## The RAG Retrieval Process

### Step 1: Indexing (One-Time Setup)

```
Meeting JSON Files
    ↓
[Entity Extraction] → Structured entities saved to entities/ directory
    ↓
[Semantic Chunking] → Chunks: summary, decision, action, attendance, resource
    ↓
[Embedding Generation] → Vector embeddings (sentence-transformers)
    ↓
[FAISS Index Creation] → Vector database for similarity search
```

**Key Point**: Entity extraction happens **during indexing**, not during queries. This ensures:
- All entities are normalized and deduplicated upfront
- Relationships are established and stored
- Entity metadata is available for citation enhancement

### Step 2: Query Execution

```
User Query
    ↓
[Query Classification] → Is this an entity query or semantic query?
    ↓
    ├─→ Entity Query Path → Entity Storage → Structured Response
    └─→ Semantic Query Path → FAISS Search → LLM Generation → Answer
    ↓
[Citation Extraction] → Enhanced with entity metadata
    ↓
Response with Auditable Citations
```

### Step 3: Citation Enhancement

Every citation includes:
- **Basic**: `[meeting_id | date | workgroup_name]`
- **Enhanced**: `[meeting_id | date | workgroup_name] (decision) - Entities: Budget, Allocation - Stephen → attended → Meeting`

This enhancement comes from:
- Entity extraction metadata (normalized names, relationships)
- Semantic chunk metadata (chunk type, entities mentioned)

---

## Recommended Approach for New JSON Source

### Phase 1: Analyze Your JSON Structure

**Goal**: Identify all potential entities and their locations in the JSON.

#### Step 1.1: Map Entity Types to JSON Fields

Create a mapping document:

```markdown
## Entity Mapping for [Your Source]

### Workgroups
- **Source**: `workgroup_id` (UUID) or `workgroup` (name)
- **Location**: Top-level field
- **Example**: `{"workgroup_id": "123e4567-...", "workgroup": "Governance WG"}`

### Meetings
- **Source**: Combination of `workgroup_id` + `date`
- **Location**: Top-level object
- **Key Fields**: `id`, `workgroup_id`, `date`, `meetingInfo`

### People
- **Source**: 
  - Structured: `meetingInfo.host`, `meetingInfo.documenter`, `meetingInfo.peoplePresent`
  - NER: Text fields (purpose, decisions, action items)
- **Location**: Nested in `meetingInfo` or extracted from text

### Documents
- **Source**: `meetingInfo.workingDocs[]`
- **Location**: Array in `meetingInfo`
- **Fields**: `title`, `link`

### Decisions
- **Source**: `agendaItems[].decisionItems[]`
- **Location**: Nested in agenda items
- **Fields**: `decision`, `rationale`, `effect`

### Action Items
- **Source**: `agendaItems[].actionItems[]`
- **Location**: Nested in agenda items
- **Fields**: `text`, `assignee`, `due_date`, `status`
```

#### Step 1.2: Identify Relationship Patterns

Map how entities relate to each other:

```markdown
## Relationship Patterns

- Meeting → belongs_to → Workgroup (via `workgroup_id`)
- Meeting → has_many → Documents (via `meetingInfo.workingDocs`)
- Meeting → has_many → AgendaItems (via `agendaItems`)
- AgendaItem → has_many → DecisionItems (via `decisionItems`)
- AgendaItem → has_many → ActionItems (via `actionItems`)
- Person → assigned_to → ActionItem (via `assignee`)
- Person → attended → Meeting (via `meetingInfo.peoplePresent`)
```

### Phase 2: Configure Entity Extraction

#### Step 2.1: Update `MeetingRecord` Model

If your JSON structure differs, update `src/models/meeting_record.py`:

```python
class MeetingRecord(BaseModel):
    # Add your top-level fields
    workgroup_id: Optional[str] = None
    workgroup: Optional[str] = None
    meetingInfo: Optional[MeetingInfo] = None
    agendaItems: Optional[List[AgendaItem]] = None
    # ... your custom fields
```

#### Step 2.2: Update Entity Extraction Logic

Modify `src/services/meeting_to_entity.py` to extract your entities:

```python
def convert_and_save_meeting_record(meeting_record: MeetingRecord) -> Meeting:
    # 1. Extract Workgroup
    if meeting_record.workgroup_id:
        workgroup_id = UUID(meeting_record.workgroup_id)
        # Create or load workgroup entity
        workgroup = extract_workgroup(workgroup_id, meeting_record.workgroup)
    
    # 2. Extract Meeting
    meeting = extract_meeting(meeting_record, workgroup_id)
    
    # 3. Extract People (structured)
    if meeting_record.meetingInfo:
        extract_people_from_meeting_info(meeting.id, meeting_record.meetingInfo)
    
    # 4. Extract Documents
    if meeting_record.meetingInfo and meeting_record.meetingInfo.workingDocs:
        extract_documents(meeting.id, meeting_record.meetingInfo.workingDocs)
    
    # 5. Extract Agenda Items, Decisions, Actions
    if meeting_record.agendaItems:
        extract_agenda_items_and_decisions(meeting.id, meeting_record.agendaItems)
    
    # 6. Extract NER entities from text fields
    extract_ner_entities_from_text(meeting.id, meeting_record)
    
    return meeting
```

#### Step 2.3: Implement Entity Extraction Functions

For each entity type, create an extraction function:

```python
def extract_workgroup(workgroup_id: UUID, workgroup_name: Optional[str]) -> Workgroup:
    """Extract workgroup entity from JSON."""
    existing = load_entity(workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
    if existing:
        return existing
    
    workgroup = Workgroup(
        id=workgroup_id,
        name=workgroup_name or f"Workgroup {workgroup_id}"
    )
    save_workgroup(workgroup)
    return workgroup

def extract_people_from_meeting_info(meeting_id: UUID, meeting_info: MeetingInfo):
    """Extract people entities from meetingInfo."""
    people_to_extract = []
    
    if meeting_info.host:
        people_to_extract.append(meeting_info.host)
    if meeting_info.documenter:
        people_to_extract.append(meeting_info.documenter)
    if meeting_info.peoplePresent:
        # Parse comma-separated list
        people_to_extract.extend([p.strip() for p in meeting_info.peoplePresent.split(",")])
    
    for person_name in people_to_extract:
        if _should_extract_entity(person_name, entity_type="person"):
            extract_person(person_name, meeting_id)

def extract_documents(meeting_id: UUID, working_docs: List[Dict]):
    """Extract document entities from workingDocs array."""
    for doc_data in working_docs:
        title = doc_data.get("title", "")
        link = doc_data.get("link", "")
        
        if _should_extract_entity(title, entity_type="document"):
            document = Document(
                id=generate_document_id(title, link),
                meeting_id=meeting_id,
                title=title,
                link=link
            )
            save_document(document)
```

### Phase 3: Configure NER Extraction

#### Step 3.1: Identify Text Fields for NER

List all text fields that might contain entity mentions:

```python
NER_TEXT_FIELDS = [
    "meetingInfo.purpose",           # Meeting purpose/description
    "agendaItems[].decisionItems[].decision",  # Decision text
    "agendaItems[].decisionItems[].rationale",  # Decision rationale
    "agendaItems[].actionItems[].text",        # Action item text
    # Add your custom text fields
]
```

#### Step 3.2: Configure NER Service

The NER service automatically extracts entities from text fields. Ensure it's called during entity extraction:

```python
def extract_ner_entities_from_text(meeting_id: UUID, meeting_record: MeetingRecord):
    """Extract entities from text fields using NER."""
    ner_service = NERIntegrationService()
    
    # Extract from purpose
    if meeting_record.meetingInfo and meeting_record.meetingInfo.purpose:
        ner_entities = ner_service.extract_from_text(
            text=meeting_record.meetingInfo.purpose,
            meeting_id=meeting_id,
            source_field="meetingInfo.purpose"
        )
        # Merge with structured entities
        merge_ner_entities(ner_entities)
    
    # Extract from decisions
    if meeting_record.agendaItems:
        for agenda_item in meeting_record.agendaItems:
            if agenda_item.decisionItems:
                for decision in agenda_item.decisionItems:
                    if decision.get("decision"):
                        ner_entities = ner_service.extract_from_text(
                            text=decision["decision"],
                            meeting_id=meeting_id,
                            source_field="agendaItems[].decisionItems[].decision"
                        )
                        merge_ner_entities(ner_entities)
```

### Phase 4: Ensure Complete Entity Coverage

#### Checklist: All Entities Identified

- [ ] **Workgroups**: Extracted from `workgroup_id` or `workgroup` field
- [ ] **Meetings**: Extracted from combination of `workgroup_id` + `date`
- [ ] **People**: Extracted from:
  - [ ] Structured fields (`host`, `documenter`, `peoplePresent`)
  - [ ] NER from text fields (`purpose`, `decisions`, `action items`)
- [ ] **Documents**: Extracted from `workingDocs` array
- [ ] **Agenda Items**: Extracted from `agendaItems` array
- [ ] **Decisions**: Extracted from `agendaItems[].decisionItems[]`
- [ ] **Action Items**: Extracted from `agendaItems[].actionItems[]`
- [ ] **Custom Entities**: Any additional entity types in your JSON

#### Checklist: All Relationships Established

- [ ] Meeting → Workgroup (foreign key: `meeting.workgroup_id`)
- [ ] Meeting → Documents (foreign key: `document.meeting_id`)
- [ ] Meeting → AgendaItems (foreign key: `agenda_item.meeting_id`)
- [ ] AgendaItem → DecisionItems (foreign key: `decision_item.agenda_item_id`)
- [ ] AgendaItem → ActionItems (foreign key: `action_item.agenda_item_id`)
- [ ] Person → ActionItems (foreign key: `action_item.assignee_id`)
- [ ] Person → Meetings (via `meetingInfo.peoplePresent` - many-to-many)

---

## How Entity Extraction Controls RAG Prompts

### 1. Query Classification

Entity extraction enables the system to detect entity queries and route them appropriately:

```python
# In QueryService.execute_query()
if is_entity_query(query_text):
    # Use entity query service (faster, structured)
    return entity_query_service.query(query_text)
else:
    # Use semantic RAG (qualitative, LLM-based)
    return rag_query_service.query(query_text)
```

**Entity Query Detection**:
- Contains entity names: "List decisions by Stephen"
- Contains entity types: "Show all workgroups"
- Contains quantitative terms: "How many meetings", "Count decisions"
- Contains list commands: "List meetings in March 2025"

### 2. Context Enhancement for RAG

When semantic RAG is used, entity extraction enhances the context:

```python
# In RAGGenerator.generate()
for chunk in retrieved_chunks:
    meeting_id = chunk.get('meeting_id')
    
    # Load decision items for this meeting (if decision query)
    if is_decision_query(query):
        decision_items = entity_query_service.get_decision_items_by_meeting(meeting_id)
        # Inject actual decision text into context
        chunk['text'] += "\n\nDecisions made:\n" + format_decisions(decision_items)
    
    # Load entity metadata for citation enhancement
    entities = entity_query_service.get_entities_for_meeting(meeting_id)
    chunk['metadata']['entities'] = entities
```

This ensures:
- **Accurate Answers**: LLM receives actual decision text, not just meeting references
- **Complete Context**: Entity relationships are included in the prompt
- **Controlled Output**: LLM is constrained to entities that exist in the data

### 3. Citation Verification

Entity extraction enables citation verification:

```python
def verify_citations_with_entity_extraction(citations: List[Citation]) -> bool:
    """Verify citations reference valid entities."""
    for citation in citations:
        meeting_id = UUID(citation.meeting_id)
        
        # Verify meeting exists
        meeting = entity_query_service.get_by_id(meeting_id, ENTITIES_MEETINGS_DIR, Meeting)
        if not meeting:
            return False
        
        # Verify workgroup exists
        if meeting.workgroup_id:
            workgroup = entity_query_service.get_by_id(
                meeting.workgroup_id, 
                ENTITIES_WORKGROUPS_DIR, 
                Workgroup
            )
            if not workgroup:
                return False
    
    return True
```

---

## Ensuring Auditable Citations

### Citation Format

Every citation follows this format:

```
[meeting_id | date | workgroup_name] (chunk_type) - Entities: Entity1, Entity2 - Relationship1 → Relationship2 → Relationship3
```

**Components**:
1. **Basic Citation**: `[meeting_id | date | workgroup_name]`
   - `meeting_id`: UUID from entity storage (verifiable)
   - `date`: ISO 8601 date from meeting entity
   - `workgroup_name`: Normalized name from workgroup entity

2. **Chunk Type**: `(summary)`, `(decision)`, `(action)`, `(attendance)`, `(resource)`
   - Indicates semantic chunk type for context

3. **Entities**: `Entities: Entity1, Entity2`
   - Normalized entity names mentioned in the chunk
   - Verifiable via entity storage

4. **Relationships**: `Person → attended → Meeting`
   - Relationship triples from entity storage
   - Verifiable via relationship storage

### Audit Trail

Every citation can be traced back to:

1. **Source JSON**: `meeting_id` → `entities/meetings/{meeting_id}.json` → Original JSON record
2. **Entity Storage**: `workgroup_name` → `entities/workgroups/{workgroup_id}.json` → Normalized entity
3. **Relationship Storage**: `entities/_relations/meeting_person.json` → Relationship records
4. **Chunk Metadata**: `retrieved_chunks[].metadata` → Original chunk with score and source

### Example Audit Trail

```
Citation: [99088668-86fe-3b53-225e-619d592088b8 | 2025-03-27 | Governance Workgroup] (decision) - Entities: Budget, Allocation - Stephen → attended → Meeting

Audit Trail:
1. Meeting Entity: entities/meetings/99088668-86fe-3b53-225e-619d592088b8.json
   → Contains: workgroup_id, date, host_id, documenter_id
2. Workgroup Entity: entities/workgroups/{workgroup_id}.json
   → Contains: name = "Governance Workgroup" (normalized)
3. Person Entity: entities/people/{person_id}.json
   → Contains: display_name = "Stephen" (normalized from "Stephen [QADAO]")
4. Relationship: entities/_relations/meeting_person.json
   → Contains: {meeting_id, person_id, relationship_type: "attended"}
5. Chunk Metadata: Retrieved from FAISS index
   → Contains: chunk_type = "decision", entities = ["Budget", "Allocation"]
6. Source JSON: Original meeting record
   → Contains: Full meeting JSON with all original data
```

---

## Best Practices

### 1. Extract All Structured Entities First

Always extract structured entities (from JSON fields) before NER extraction. This ensures:
- Structured entities are canonical (source of truth)
- NER entities can be merged into structured entities
- No duplicate entities

### 2. Normalize Entity Names

Always normalize entity names during extraction:
- Remove suffixes: `"Stephen [QADAO]"` → `"Stephen"`
- Handle variations: `"Governance WG"` → `"Governance Workgroup"`
- Use fuzzy matching: `"Stephen"` ≈ `"Steven"` (if same person)

### 3. Establish Relationships Explicitly

Don't rely on implicit relationships. Explicitly create relationship records:
- Meeting → Workgroup (via `meeting.workgroup_id`)
- Person → Meeting (via `meeting_person` junction table)
- ActionItem → Person (via `action_item.assignee_id`)

### 4. Store Entity Metadata

Store metadata with entities for citation enhancement:
- Source field: `"meetingInfo.host"`
- Source meeting: `meeting_id`
- Normalized name: Canonical entity name
- Variations: All name variations that map to this entity

### 5. Verify Citations After Generation

Always verify citations reference valid entities:
- Check meeting exists in entity storage
- Check workgroup exists
- Check entities mentioned in citations exist
- Log warnings for invalid citations

---

## Testing Your Integration

### Test Entity Extraction

```bash
# Ingest entities from your JSON source
archive-rag ingest-entities path/to/your/meetings.json

# Verify entities were extracted
ls entities/workgroups/     # Should contain workgroup JSON files
ls entities/meetings/        # Should contain meeting JSON files
ls entities/people/          # Should contain person JSON files
ls entities/decision_items/ # Should contain decision JSON files
```

### Test RAG Integration

```bash
# Index your meetings
archive-rag index path/to/meetings/ indexes/meetings.faiss

# Test entity query (should use entity storage)
archive-rag query indexes/meetings.faiss "List all decisions made by Governance workgroup"

# Test semantic query (should use FAISS + LLM)
archive-rag query indexes/meetings.faiss "What decisions were made about budget allocation?"

# Verify citations include entity metadata
# Check that citations show: [meeting_id | date | workgroup_name] (decision) - Entities: ...
```

### Test Citation Auditability

```bash
# Query and get citations
archive-rag query indexes/meetings.faiss "List decisions" --output-format json > query_result.json

# Extract meeting_id from citation
meeting_id=$(jq -r '.citations[0].meeting_id' query_result.json)

# Verify meeting exists in entity storage
cat entities/meetings/${meeting_id}.json

# Verify workgroup exists
workgroup_id=$(jq -r '.workgroup_id' entities/meetings/${meeting_id}.json)
cat entities/workgroups/${workgroup_id}.json
```

---

## Summary

**Key Principles**:

1. **Extract First, Query Later**: Entity extraction happens during indexing, not during queries
2. **Two-Path System**: Use entity queries for structured data, semantic RAG for qualitative questions
3. **Complete Coverage**: Extract all entities (structured + NER) and establish all relationships
4. **Normalize Everything**: Normalize entity names to ensure consistent citations
5. **Verify Citations**: Always verify citations reference valid entities for auditability

**Result**: A RAG system that:
- Provides accurate, evidence-bound answers
- Returns auditable citations with full provenance
- Routes queries efficiently (entity vs. semantic)
- Enhances citations with entity metadata
- Maintains a complete audit trail from citation to source JSON


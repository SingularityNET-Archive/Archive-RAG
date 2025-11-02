# Modifying the Meeting JSON Format

## Overview

The required JSON format is defined in `src/models/meeting_record.py`. To change the format, you need to modify the `MeetingRecord` Pydantic model.

## Main File to Modify

**`src/models/meeting_record.py`** - This is the primary definition of the format.

## Steps to Change the Format

### 1. Modify the MeetingRecord Model

Edit `src/models/meeting_record.py` to add, remove, or change fields:

```python
class MeetingRecord(BaseModel):
    # Required fields use Field(...)
    # Optional fields use Field(default=None) or Optional[type]
    
    # Add new required field:
    new_required_field: str = Field(..., description="Your new field")
    
    # Add new optional field:
    new_optional_field: Optional[str] = Field(None, description="Optional field")
    
    # Make existing field optional (change Field(...) to Field(None)):
    decisions: Optional[List[str]] = Field(None, ...)  # Now optional
    
    # Remove a field:
    # Just delete the line
    
    # Add custom validation:
    @validator("new_field")
    def validate_new_field(cls, v):
        # Your validation logic
        return v
```

### 2. Update Required Fields Check

Edit `src/services/ingestion.py` line 40 to match your new required fields:

```python
# Update this list to match your required fields
required_fields = ["id", "date", "participants", "transcript", "your_new_field"]
```

### 3. Update Field Usage (if needed)

If you change field names that are used elsewhere, update:

- **`src/services/chunking.py`**: Uses `meeting_record.id`, `meeting_record.date`, `meeting_record.participants` in metadata
- **`src/services/citation_extractor.py`**: Extracts citations using `meeting_id`, `date`, `participants`
- **Any other services** that access MeetingRecord fields

### 4. Test Your Changes

```bash
# Test with a sample file
python -c "
from src.models.meeting_record import MeetingRecord
import json

# Test your new format
with open('your-file.json') as f:
    data = json.load(f)
    
try:
    mr = MeetingRecord(**data)
    print('✓ Format valid!')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

## Example: Adding a New Field

### Example 1: Add "location" field (optional)

```python
# In src/models/meeting_record.py
class MeetingRecord(BaseModel):
    # ... existing fields ...
    location: Optional[str] = Field(None, description="Meeting location")
```

**No other changes needed** - optional fields don't need to be in required_fields list.

### Example 2: Add "summary" field (required)

```python
# In src/models/meeting_record.py
class MeetingRecord(BaseModel):
    # ... existing fields ...
    summary: str = Field(..., description="Meeting summary")
```

**Also update** `src/services/ingestion.py`:
```python
required_fields = ["id", "date", "participants", "transcript", "summary"]
```

### Example 3: Rename "transcript" to "content"

```python
# In src/models/meeting_record.py
class MeetingRecord(BaseModel):
    # ... existing fields ...
    content: str = Field(..., description="Meeting content")  # Renamed from transcript
```

**Update all references to `transcript`**:
- `src/services/chunking.py`: Change `meeting_record.transcript` to `meeting_record.content`
- `src/services/ingestion.py`: Update required_fields and validation
- Any other files using `transcript` field

### Example 4: Change "date" to accept multiple formats

```python
# In src/models/meeting_record.py
class MeetingRecord(BaseModel):
    # ... existing fields ...
    
    @validator("date")
    def validate_date_format(cls, v):
        # Accept both ISO 8601 and custom format
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            # Try custom format: "YYYY-MM-DD HH:MM"
            try:
                datetime.strptime(v, "%Y-%m-%d %H:%M")
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")
        return v
```

## Important Considerations

### Fields Used by Other Components

These fields are heavily used and changing them requires updates:

- **`id`**: Used everywhere (indexing, citations, metadata)
- **`date`**: Used in citations `[meeting_id | date | speaker]`
- **`participants`**: Used in citations for speaker names
- **`transcript`**: The main content that gets chunked and embedded

### Backward Compatibility

If you want to support both old and new formats:

```python
class MeetingRecord(BaseModel):
    # Support both old and new field names
    transcript: Optional[str] = Field(None, description="Meeting transcript (legacy)")
    content: Optional[str] = Field(None, description="Meeting content (new)")
    
    @validator("content", "transcript", always=True)
    def ensure_content(cls, v, values):
        # Use content if available, fallback to transcript
        if v:
            return v
        if values.get("transcript"):
            return values["transcript"]
        raise ValueError("Either 'content' or 'transcript' must be provided")
```

## Quick Reference

| Change Type | Files to Modify |
|------------|----------------|
| Add optional field | `src/models/meeting_record.py` only |
| Add required field | `src/models/meeting_record.py` + `src/services/ingestion.py` |
| Rename field | `src/models/meeting_record.py` + all files using that field |
| Change field type | `src/models/meeting_record.py` + validation logic |
| Add validation | `src/models/meeting_record.py` (add `@validator`) |

## Testing Your Changes

After modifying the format:

1. **Validate a sample file**:
   ```bash
   python -c "from src.models.meeting_record import MeetingRecord; import json; data = json.load(open('your-file.json')); mr = MeetingRecord(**data); print('✓ Valid')"
   ```

2. **Test indexing**:
   ```bash
   archive-rag index your-data-dir/ indexes/test.faiss
   ```

3. **Test querying**:
   ```bash
   archive-rag query indexes/test.faiss "Test query"
   ```

If you need help with specific changes, let me know what format you want to use!


# NER Integration Tests (Phase 6)

This document describes the test suite for Phase 6: User Story 4 - Apply Named Entity Recognition to Text Fields.

## Test Files

### Unit Tests: `tests/unit/test_ner_integration.py`

Tests for the `NERIntegrationService` class covering:

1. **Entity Extraction**
   - Extraction from empty/whitespace text
   - Extraction of PERSON, ORG, DATE entities
   - Source field tracking

2. **Entity Filtering (FR-013, FR-014)**
   - Filtering out filler comments ("n/a", "todo", "filler", etc.)
   - Filtering out very short entities
   - Filtering out relative dates ("today", "tomorrow")
   - Extracting meaningful entities (PERSON, ORG, GPE)

3. **Entity Merging**
   - Merging with empty structured entities
   - Exact name matching
   - Fuzzy similarity matching (>95%)
   - Handling entities with different attributes (display_name vs name)

### Integration Tests: `tests/integration/test_ner_entity_extraction.py`

Tests for NER integration with the entity extraction pipeline:

1. **NER Extraction from Text Fields**
   - Extraction from `meetingInfo.purpose` field
   - Extraction from decision text fields
   - Extraction from action item text fields

2. **Entity Filtering in Context**
   - Filtering filler comments during real extraction
   - Verifying meaningful entities are extracted

3. **Entity Merging in Context**
   - Merging NER entities with existing structured entities
   - Verifying matched entities are linked correctly

4. **Summary Tracking**
   - Verifying NER extraction summary is tracked
   - Testing extraction from multiple fields in one meeting

5. **Error Handling**
   - Graceful handling of missing spaCy model
   - Continuing processing even if NER fails

## Prerequisites

### spaCy Model

The tests require a spaCy model to be installed. The default model is specified in `src/lib/config.py` as `NER_MODEL_NAME`.

To install the default English model:
```bash
python -m spacy download en_core_web_sm
```

Or install a larger model for better accuracy:
```bash
python -m spacy download en_core_web_md
```

### Dependencies

All required dependencies should be installed via:
```bash
pip install -r requirements.txt
```

Key dependencies:
- `spacy` - For NER processing
- `rapidfuzz` - For fuzzy entity matching
- `pydantic` - For data models
- `pytest` - For testing framework

## Running the Tests

### Run All NER Tests

```bash
# Run all unit tests for NER
pytest tests/unit/test_ner_integration.py -v

# Run all integration tests for NER
pytest tests/integration/test_ner_entity_extraction.py -v

# Run both test files
pytest tests/unit/test_ner_integration.py tests/integration/test_ner_entity_extraction.py -v
```

### Run Specific Test Classes

```bash
# Test NERIntegrationService
pytest tests/unit/test_ner_integration.py::TestNERIntegrationService -v

# Test entity filtering
pytest tests/unit/test_ner_integration.py::TestNEREntityFiltering -v

# Test integration with entity extraction
pytest tests/integration/test_ner_entity_extraction.py::TestNERIntegrationWithEntityExtraction -v
```

### Run Specific Test Methods

```bash
# Test person entity extraction
pytest tests/unit/test_ner_integration.py::TestNERIntegrationService::test_extract_from_text_person_entity -v

# Test filtering filler comments
pytest tests/unit/test_ner_integration.py::TestNERIntegrationService::test_extract_from_text_filters_filler_comments -v

# Test merging with structured entities
pytest tests/unit/test_ner_integration.py::TestNERIntegrationService::test_merge_with_structured_exact_match -v
```

### Run with Coverage

```bash
# Install coverage tools
pip install pytest-cov

# Run tests with coverage
pytest tests/unit/test_ner_integration.py tests/integration/test_ner_entity_extraction.py --cov=src/services/ner_integration --cov=src/services/meeting_to_entity --cov-report=html
```

## Test Coverage

The tests cover:

✅ **Phase 6 Task T051**: NERIntegrationService integration
✅ **Phase 6 Task T052**: NER extraction from meetingInfo.purpose
✅ **Phase 6 Task T053**: NER extraction from decision text fields
✅ **Phase 6 Task T054**: NER extraction from action item text fields
✅ **Phase 6 Task T055**: NER entity filtering by extraction criteria (FR-013)
✅ **Phase 6 Task T056**: NER entity filtering to remove filler comments (FR-014)
✅ **Phase 6 Task T057**: NER entity merging with structured entities
✅ **Phase 6 Task T058**: NER entity normalization using EntityNormalizationService
✅ **Phase 6 Task T059**: NER entity output tracking and summary

## Expected Behavior

### Successful Test Run

When all tests pass, you should see output like:
```
tests/unit/test_ner_integration.py::TestNERIntegrationService::test_extract_from_text_person_entity PASSED
tests/unit/test_ner_integration.py::TestNERIntegrationService::test_extract_from_text_org_entity PASSED
...
tests/integration/test_ner_entity_extraction.py::TestNERIntegrationWithEntityExtraction::test_ner_extraction_from_purpose_field PASSED
...
```

### Skipped Tests

If the spaCy model is not installed, some tests will be skipped:
```
tests/unit/test_ner_integration.py::TestNERIntegrationService::test_extract_from_text_person_entity SKIPPED [1] spacy model not available
```

To fix this, install the spaCy model as described in Prerequisites.

## Troubleshooting

### spaCy Model Not Found

**Error**: `ValueError: spaCy model 'en_core_web_sm' not found`

**Solution**: Install the spaCy model:
```bash
python -m spacy download en_core_web_sm
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'spacy'`

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Entity Storage Errors

**Error**: Issues with entity storage directories

**Solution**: The tests automatically initialize entity storage directories. If issues persist, check that the `ENTITIES_DIR` path is writable.

## Notes

- Tests use fixtures to create and clean up test entities automatically
- Some tests may be skipped if spaCy model is not available (tests use `pytest.skip()`)
- Integration tests create real entities in the entity storage system
- Tests clean up after themselves, but manual cleanup may be needed if tests are interrupted


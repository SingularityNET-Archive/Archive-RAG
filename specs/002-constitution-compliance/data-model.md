# Data Model: Constitution Compliance Verification

**Feature**: Constitution Compliance  
**Date**: 2025-11-02  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

This document describes the compliance verification model for ensuring the entity data model implementation complies with Archive-RAG Constitution v1.0.0. Unlike typical data models, this feature does not introduce new entities but rather defines verification structures and processes for detecting and preventing constitution violations.

## Compliance Verification Model

### Compliance Check Types

```
ComplianceCheck
  ├─┬─ StaticAnalysisCheck
  │  ├─┬─ ExternalAPIImportCheck
  │  ├─┬─ NonPythonDependencyCheck
  │  └─┬─ HTTPCallCheck
  │
  ├─┬─ RuntimeCheck
  │  ├─┬─ NetworkCallMonitor
  │  ├─┬─ ProcessSpawnMonitor
  │  └─┬─ ModuleLoadMonitor
  │
  └─┬─ TestCheck
     ├─┬─ UnitTestCoverage
     ├─┬─ IntegrationTestCoverage
     └─┬─ ContractTestCoverage
```

### Compliance Check Structure

**StaticAnalysisCheck**:
- Purpose: Detect violations in source code before execution
- Input: Python source files (`.py` files)
- Method: AST parsing, import analysis, pattern matching
- Output: List of violations with file paths and line numbers

**RuntimeCheck**:
- Purpose: Detect violations during execution
- Input: Runtime operations (API calls, process spawns, module loads)
- Method: Monitoring, interception, validation
- Output: Violation events logged and reported

**TestCheck**:
- Purpose: Verify compliance through automated tests
- Input: Test suite execution
- Method: Mock external dependencies, verify local-only operations
- Output: Test results with compliance status

### Violation Structure

**ConstitutionViolation**:
- `violation_type`: Type of violation (ExternalAPI, NonPythonDependency, etc.)
- `principle`: Constitution principle violated (Technology Discipline, etc.)
- `location`: Where violation occurred (file path, line number, function)
- `violation_details`: Specific violation (API call, dependency, etc.)
- `detection_layer`: How it was detected (static_analysis, runtime, test)
- `timestamp`: When violation was detected
- `recommended_action`: How to fix the violation

### Compliance Status

**ComplianceStatus**:
- `entity_operations`: Compliance status for entity operations (save, load, query, delete)
- `embedding_generation`: Compliance status for embedding operations
- `llm_inference`: Compliance status for LLM inference operations
- `faiss_operations`: Compliance status for FAISS index operations
- `python_only`: Compliance status for Python-only requirement
- `cli_support`: Compliance status for CLI command support
- `overall_status`: Overall compliance (PASS/FAIL)
- `violations`: List of detected violations
- `last_check`: Timestamp of last compliance check

## Compliance Verification Rules

### Rule 1: No External API Dependencies

**Constraint**: System MUST operate without external API dependencies for core entity operations

**Verification**:
- Static: Detect imports of `requests`, `openai`, `httpx`, `urllib3` (external API libraries)
- Runtime: Monitor network calls, intercept HTTP requests
- Test: Mock external API calls, verify they fail with violations

**Violation Example**:
```python
# Violation: External API call
import requests
response = requests.post("https://api.openai.com/v1/embeddings", ...)
```

### Rule 2: Local Embeddings Only

**Constraint**: System MUST use local embedding models (no remote embedding API calls)

**Verification**:
- Static: Detect non-local embedding service initialization
- Runtime: Monitor embedding service for external API calls
- Test: Verify embedding service uses local models only

**Violation Example**:
```python
# Violation: Remote embedding service
from src.services.remote_embedding import RemoteEmbeddingService
service = RemoteEmbeddingService(api_url="https://api.openai.com/v1")
```

### Rule 3: Local LLM Inference Only

**Constraint**: System MUST use local LLM models (no remote LLM API calls)

**Verification**:
- Static: Detect non-local LLM service initialization
- Runtime: Monitor LLM service for external API calls
- Test: Verify LLM service uses local models only

**Violation Example**:
```python
# Violation: Remote LLM service
from src.services.remote_llm import RemoteLLMService
service = RemoteLLMService(api_url="https://api.openai.com/v1")
```

### Rule 4: Local FAISS Storage Only

**Constraint**: System MUST store all FAISS indexes locally (no remote vector database)

**Verification**:
- Static: Detect remote vector database connections
- Runtime: Monitor FAISS index operations for remote storage
- Test: Verify FAISS indexes are stored locally only

**Violation Example**:
```python
# Violation: Remote vector database
import pinecone
index = pinecone.Index("meetings-index")
```

### Rule 5: Python-Only Execution

**Constraint**: System MUST use only Python standard library and Python packages (no external binaries)

**Verification**:
- Static: Detect subprocess/exec calls to external binaries
- Runtime: Monitor process spawns, detect external binary execution
- Test: Verify no external binaries are executed

**Violation Example**:
```python
# Violation: External binary execution
import subprocess
subprocess.run(["curl", "https://api.example.com"])
```

### Rule 6: CLI Support

**Constraint**: System MUST provide CLI commands for all entity operations

**Verification**:
- Static: Detect CLI command definitions
- Runtime: Verify CLI commands are accessible
- Test: Verify CLI commands work without external dependencies

**Compliant Example**:
```python
# Compliant: CLI command for entity query
@cli_app.command()
def query_workgroup(workgroup_id: str):
    query_service = EntityQueryService()
    meetings = query_service.get_meetings_by_workgroup(workgroup_id)
    print(meetings)
```

## Compliance Verification Workflow

### Development-Time Checks

1. **Static Analysis** (CI/CD):
   - Run static analysis on all source files
   - Detect external API imports
   - Detect non-Python dependencies
   - Report violations with file/line numbers

2. **Automated Tests** (CI/CD):
   - Run compliance unit tests
   - Run compliance integration tests
   - Run compliance contract tests
   - Report test failures as violations

### Runtime Checks

1. **Operation Monitoring**:
   - Monitor entity operations for API calls
   - Monitor embedding operations for external calls
   - Monitor LLM inference for external calls
   - Log violations with full context

2. **Violation Handling**:
   - Fail-fast with clear error messages
   - Log violation details to audit trail
   - Prevent silent fallbacks to external services

### Manual Verification

1. **Code Review**:
   - Automated compliance reports in PR comments
   - Code review checklist with compliance items
   - Human verification of automated findings

2. **Audit Reports**:
   - Generate compliance audit reports
   - Track compliance status over time
   - Document compliance decisions

## Compliance Verification Examples

### Example 1: Static Analysis Check

```python
# Source file: src/services/entity_storage.py
import requests  # VIOLATION: External API library

def save_entity(entity):
    response = requests.post("https://api.example.com", data=entity)  # VIOLATION: External API call
    return response
```

**Violation Report**:
```
Constitution Violation: External API dependency detected
  Principle: Technology Discipline - "No external API dependency for core functionality"
  Location: src/services/entity_storage.py:1
  Violation: import requests
  Detection Layer: static_analysis
  Recommended Action: Use local storage only (JSON files via standard library)
```

### Example 2: Runtime Check

```python
# Runtime operation
from src.services.embedding import EmbeddingService
service = EmbeddingService()
# If service tries to call external API:
# Runtime check intercepts and raises ConstitutionViolation
```

**Violation Report**:
```
Constitution Violation: External API call detected during runtime
  Principle: Technology Discipline - "Local embeddings + FAISS storage"
  Location: src/services/embedding.py:45 (runtime)
  Violation: HTTP POST to https://api.openai.com/v1/embeddings
  Detection Layer: runtime
  Recommended Action: Use local embedding model (sentence-transformers)
```

### Example 3: Test Check

```python
# Test: Verify compliance
def test_entity_storage_no_external_apis():
    """Verify entity storage doesn't use external APIs."""
    # Mock external API call
    with mock.patch('requests.post') as mock_api:
        # Should fail with constitution violation
        with pytest.raises(ConstitutionViolation):
            save_entity(entity)
```

**Test Result**:
```
✓ test_entity_storage_no_external_apis: PASS
  Compliance: Entity storage uses local-only operations
```

## Summary

The compliance verification model provides comprehensive detection and prevention of constitution violations through multiple layers: static analysis (development-time), runtime monitoring (execution-time), and automated tests (verification-time). All violations are reported with clear details and actionable recommendations, ensuring the entity data model implementation complies with Archive-RAG Constitution v1.0.0.


# Compliance Check Contracts

**Feature**: Constitution Compliance  
**Date**: 2025-11-02  
**Spec**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

## Overview

This document defines the contracts for constitution compliance verification. These contracts specify the expected behavior of compliance checks and the format of compliance reports.

## Compliance Check API Contracts

### Static Analysis Check Contract

**Function**: `check_no_external_apis(file_path: Path) -> List[Violation]`

**Input**:
- `file_path`: Path to Python source file

**Output**:
- `List[Violation]`: List of detected violations

**Violation Structure**:
```python
{
    "violation_type": "ExternalAPIImport",
    "principle": "Technology Discipline",
    "location": {
        "file": "src/services/entity_storage.py",
        "line": 5,
        "column": 1
    },
    "violation_details": "import requests",
    "detection_layer": "static_analysis",
    "recommended_action": "Use local storage only (JSON files via standard library)"
}
```

**Preconditions**:
- File exists and is readable
- File contains valid Python syntax

**Postconditions**:
- All violations are detected and reported
- Violations include file location and details

**Exceptions**:
- `FileNotFoundError`: If file does not exist
- `SyntaxError`: If file contains invalid Python syntax

---

### Runtime Check Contract

**Function**: `monitor_api_calls(operation: Callable) -> Any`

**Input**:
- `operation`: Function to monitor for API calls

**Output**:
- Return value of `operation`

**Behavior**:
- Wraps `operation` to monitor for external API calls
- Raises `ConstitutionViolation` if external API call detected
- Returns result if no violations detected

**Violation Format**:
```python
ConstitutionViolation(
    violation_type="ExternalAPICall",
    principle="Technology Discipline",
    location="src/services/embedding.py:45 (runtime)",
    violation_details="HTTP POST to https://api.openai.com/v1/embeddings",
    detection_layer="runtime",
    recommended_action="Use local embedding model (sentence-transformers)"
)
```

**Preconditions**:
- `operation` is callable
- Network monitoring is enabled

**Postconditions**:
- All external API calls are detected and reported
- Operation result returned if compliant

**Exceptions**:
- `ConstitutionViolation`: If external API call detected
- `RuntimeError`: If monitoring fails

---

### Test Check Contract

**Function**: `test_compliance(operation: Callable, expected_local: bool = True) -> TestResult`

**Input**:
- `operation`: Function to test for compliance
- `expected_local`: Whether operation should be local-only (default: True)

**Output**:
- `TestResult`: Test result with compliance status

**TestResult Structure**:
```python
{
    "test_name": "test_entity_storage_no_external_apis",
    "status": "PASS",
    "compliance": "Entity storage uses local-only operations",
    "violations": []
}
```

**Preconditions**:
- `operation` is testable (can be called in test context)
- External dependencies are mocked

**Postconditions**:
- Compliance status is verified
- Violations are reported if detected

**Exceptions**:
- `AssertionError`: If compliance check fails
- `ConstitutionViolation`: If violation detected during test

---

## Compliance Report Contract

### Report Structure

**Report Format**: JSON + Human-readable Markdown

**Report Structure**:
```json
{
    "report_type": "compliance_audit",
    "timestamp": "2025-11-02T10:00:00Z",
    "overall_status": "PASS",
    "check_layers": {
        "static_analysis": {
            "status": "PASS",
            "violations": [],
            "files_checked": 45,
            "duration_ms": 120
        },
        "runtime": {
            "status": "PASS",
            "violations": [],
            "operations_monitored": 100,
            "duration_ms": 500
        },
        "tests": {
            "status": "PASS",
            "violations": [],
            "tests_run": 25,
            "coverage_percent": 95
        }
    },
    "compliance_by_category": {
        "entity_operations": "PASS",
        "embedding_generation": "PASS",
        "llm_inference": "PASS",
        "faiss_operations": "PASS",
        "python_only": "PASS",
        "cli_support": "PASS"
    },
    "violations": []
}
```

**Preconditions**:
- All check layers have completed execution
- All violations have been collected

**Postconditions**:
- Report accurately reflects compliance status
- All violations are included in report

---

## CLI Contract

### Command: `archive-rag check-compliance`

**Synopsis**:
```bash
archive-rag check-compliance [OPTIONS]
```

**Options**:
- `--static`: Run static analysis checks (default: true)
- `--runtime`: Run runtime checks (default: false)
- `--tests`: Run compliance tests (default: true)
- `--output-format`: Output format (json, text, markdown) (default: text)
- `--report-file`: Write report to file (optional)

**Behavior**:
- Runs specified compliance checks
- Reports compliance status and violations
- Exits with code 0 if compliant, 1 if violations detected

**Output Format (text)**:
```
Constitution Compliance Report
==============================

Overall Status: PASS

Static Analysis: PASS (45 files checked, 0 violations)
Runtime Checks: PASS (100 operations monitored, 0 violations)
Tests: PASS (25 tests run, 95% coverage)

Compliance by Category:
  ✓ Entity Operations: PASS
  ✓ Embedding Generation: PASS
  ✓ LLM Inference: PASS
  ✓ FAISS Operations: PASS
  ✓ Python-Only: PASS
  ✓ CLI Support: PASS
```

**Preconditions**:
- Archive-RAG repository is accessible
- Source files are readable
- Test framework is available (if `--tests` specified)

**Postconditions**:
- Compliance status is reported
- Violations are listed if detected
- Report file is written if `--report-file` specified

**Exit Codes**:
- `0`: Compliance passed
- `1`: Compliance violations detected
- `2`: Error during compliance check

---

## Compliance Verification Contracts

### Entity Operations Compliance

**Contract**: All entity operations (save, load, query, delete) MUST execute without external API calls

**Verification**:
- Static: No external API imports in entity storage/query code
- Runtime: No HTTP requests during entity operations
- Test: Entity operations work without network access

**Violation Detection**:
- Import of `requests`, `openai`, `httpx` in entity code → Violation
- HTTP request during entity operation → Violation
- Entity operation requires network access → Violation

---

### Embedding Generation Compliance

**Contract**: Embedding generation MUST use local models only (no remote API calls)

**Verification**:
- Static: No remote embedding service initialization
- Runtime: No HTTP requests during embedding generation
- Test: Embedding service works without network access

**Violation Detection**:
- Remote embedding service initialized → Violation
- HTTP request during embedding → Violation
- Embedding requires network access → Violation

---

### LLM Inference Compliance

**Contract**: LLM inference MUST use local models only (no remote API calls)

**Verification**:
- Static: No remote LLM service initialization
- Runtime: No HTTP requests during LLM inference
- Test: LLM service works without network access

**Violation Detection**:
- Remote LLM service initialized → Violation
- HTTP request during LLM inference → Violation
- LLM inference requires network access → Violation

---

### FAISS Operations Compliance

**Contract**: FAISS operations MUST use local storage only (no remote vector database)

**Verification**:
- Static: No remote vector database connections
- Runtime: No network requests during FAISS operations
- Test: FAISS operations work without network access

**Violation Detection**:
- Remote vector database connection → Violation
- Network request during FAISS operation → Violation
- FAISS requires network access → Violation

---

### Python-Only Compliance

**Contract**: System MUST use only Python standard library and Python packages (no external binaries)

**Verification**:
- Static: No subprocess/exec calls to external binaries
- Runtime: No external process spawns
- Test: System works without external binaries

**Violation Detection**:
- `subprocess.run()` with external binary → Violation
- External process spawned at runtime → Violation
- System requires external binary → Violation

---

### CLI Support Compliance

**Contract**: All major entity operations MUST be accessible via CLI commands

**Verification**:
- Static: CLI commands defined for all entity operations
- Runtime: CLI commands execute without external dependencies
- Test: CLI commands work without network access

**Violation Detection**:
- Missing CLI command for entity operation → Violation
- CLI command requires external dependency → Violation
- CLI command fails without network → Violation

---

## Summary

These contracts define the expected behavior of compliance checks and the format of compliance reports. All contracts ensure that the entity data model implementation complies with Archive-RAG Constitution v1.0.0 through comprehensive verification across multiple layers.


# Quick Start: Constitution Compliance

**Feature**: Constitution Compliance  
**Date**: 2025-11-02  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data Model**: [data-model.md](data-model.md)

## Overview

This guide provides quick start instructions for verifying constitution compliance in the entity data model implementation. The compliance verification ensures all entity operations comply with Archive-RAG Constitution v1.0.0 requirements.

## Prerequisites

- Python 3.11+ installed
- Archive-RAG repository cloned
- Virtual environment activated
- Dependencies installed (pytest, sentence-transformers, faiss-cpu, transformers)
- Entity data model implementation completed (`specs/001-entity-data-model`)

## Setup

### 1. Verify Implementation Status

```bash
# Ensure entity data model implementation is complete
cd /path/to/Archive-RAG
git branch
# Should be on 002-constitution-compliance or have entity model implemented
```

### 2. Install Compliance Checking Tools

```bash
# No additional dependencies needed - uses Python standard library
# Compliance checks use: ast, inspect, pytest (all existing dependencies)
```

## Basic Usage

### Run Compliance Check

```bash
# Run all compliance checks (static analysis + tests)
archive-rag check-compliance

# Run only static analysis checks
archive-rag check-compliance --static --no-tests

# Run only compliance tests
archive-rag check-compliance --tests --no-static

# Generate JSON report
archive-rag check-compliance --output-format json --report-file compliance-report.json
```

### Example Output

```
Constitution Compliance Report
==============================

Overall Status: PASS

Static Analysis: PASS (45 files checked, 0 violations)
  ✓ No external API imports detected
  ✓ No non-Python dependencies detected
  ✓ No HTTP calls in source code

Runtime Checks: PASS (100 operations monitored, 0 violations)
  ✓ Entity operations use local storage only
  ✓ Embedding generation uses local models only
  ✓ LLM inference uses local models only
  ✓ FAISS operations use local storage only

Tests: PASS (25 tests run, 95% coverage)
  ✓ Entity operations pass compliance tests
  ✓ Embedding operations pass compliance tests
  ✓ LLM operations pass compliance tests

Compliance by Category:
  ✓ Entity Operations: PASS
  ✓ Embedding Generation: PASS
  ✓ LLM Inference: PASS
  ✓ FAISS Operations: PASS
  ✓ Python-Only: PASS
  ✓ CLI Support: PASS

No violations detected. All compliance checks passed.
```

### Handling Violations

If violations are detected:

```
Constitution Compliance Report
==============================

Overall Status: FAIL

Static Analysis: FAIL (45 files checked, 2 violations)

Violations Detected:

1. External API Import
   Principle: Technology Discipline - "No external API dependency for core functionality"
   Location: src/services/embedding.py:5
   Violation: import requests
   Recommended Action: Use local embedding model instead of remote API

2. External API Call
   Principle: Technology Discipline - "Local embeddings + FAISS storage"
   Location: src/services/rag_generator.py:45
   Violation: requests.post("https://api.openai.com/v1/chat/completions", ...)
   Recommended Action: Use local LLM model instead of remote API

Compliance by Category:
  ✗ Embedding Generation: FAIL (1 violation)
  ✗ LLM Inference: FAIL (1 violation)
  ✓ Entity Operations: PASS
  ✓ FAISS Operations: PASS
  ✓ Python-Only: PASS
  ✓ CLI Support: PASS

2 violations detected. Fix violations before proceeding.
```

## Advanced Usage

### Run Static Analysis Only

```bash
# Check specific file
archive-rag check-compliance --static --file src/services/embedding.py

# Check all files in directory
archive-rag check-compliance --static --directory src/services/

# Generate detailed violation report
archive-rag check-compliance --static --verbose --report-file violations.md
```

### Run Compliance Tests

```bash
# Run all compliance tests
pytest tests/unit/test_compliance.py tests/integration/test_compliance_checks.py

# Run specific test category
pytest tests/unit/test_compliance.py::test_entity_operations_no_external_apis

# Run with coverage
pytest tests/unit/test_compliance.py --cov=src/lib/compliance --cov-report=html
```

### Integration with CI/CD

```yaml
# .github/workflows/compliance-check.yml
name: Constitution Compliance Check

on: [push, pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: archive-rag check-compliance --static --tests
```

## Compliance Verification Workflow

### 1. Development-Time Verification

```bash
# Before committing code, run compliance checks
archive-rag check-compliance --static

# If violations detected, fix them before committing
# Example: Remove external API imports, use local models
```

### 2. Pre-commit Hook

```bash
# Install pre-commit hook (optional)
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
archive-rag check-compliance --static
if [ $? -ne 0 ]; then
    echo "Constitution violations detected. Fix before committing."
    exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
```

### 3. CI/CD Integration

```bash
# In CI/CD pipeline
archive-rag check-compliance --static --tests --output-format json > compliance-report.json

# Fail build if violations detected
if [ $? -ne 0 ]; then
    echo "Compliance check failed. Review violations and fix."
    exit 1
fi
```

### 4. Manual Verification

```bash
# Generate compliance audit report
archive-rag check-compliance --static --tests --output-format markdown --report-file compliance-audit.md

# Review report and verify compliance
cat compliance-audit.md
```

## Troubleshooting

### Violation: External API Import

**Problem**: Static analysis detects `import requests` in entity code

**Solution**:
```python
# Remove external API import
# import requests  # REMOVE THIS

# Use local storage instead
import json
from pathlib import Path

def save_entity(entity):
    # Use JSON file storage (local-only)
    file_path = Path(f"entities/{entity.id}.json")
    file_path.write_text(json.dumps(entity.model_dump()))
```

### Violation: Remote Embedding Service

**Problem**: Runtime check detects HTTP request to embedding API

**Solution**:
```python
# Replace remote embedding service
# service = RemoteEmbeddingService(api_url="https://api.openai.com/v1")  # REMOVE

# Use local embedding service
from src.services.embedding import EmbeddingService
service = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
```

### Violation: External Binary Execution

**Problem**: Static analysis detects `subprocess.run()` with external binary

**Solution**:
```python
# Remove external binary execution
# subprocess.run(["curl", "https://api.example.com"])  # REMOVE

# Use Python standard library instead
import urllib.request
with urllib.request.urlopen("https://api.example.com") as response:
    data = response.read()
```

## Next Steps

- Review compliance report and fix any violations
- Add compliance checks to CI/CD pipeline
- Set up pre-commit hooks for development-time verification
- Generate periodic compliance audit reports
- Document any constitution amendments if deviations are needed

## Summary

Constitution compliance verification ensures the entity data model implementation complies with Archive-RAG Constitution v1.0.0 through multiple-layer checks: static analysis (development-time), runtime monitoring (execution-time), and automated tests (verification-time). All violations are detected and reported with clear details and actionable recommendations.


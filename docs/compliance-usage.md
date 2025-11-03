# Constitution Compliance Usage Examples

This document provides practical examples for using the Archive-RAG constitution compliance checking system.

## Table of Contents

- [Basic Compliance Checks](#basic-compliance-checks)
- [Static Analysis Examples](#static-analysis-examples)
- [Runtime Monitoring Examples](#runtime-monitoring-examples)
- [Integration Examples](#integration-examples)
- [Troubleshooting Common Violations](#troubleshooting-common-violations)

## Basic Compliance Checks

### Run All Compliance Checks

```bash
# Run static analysis + runtime checks + tests
archive-rag check-compliance
```

### Run Specific Check Types

```bash
# Only static analysis
archive-rag check-compliance --static --no-tests --no-runtime

# Only runtime checks
archive-rag check-compliance --runtime --no-static --no-tests

# Only compliance tests
archive-rag check-compliance --tests --no-static --no-runtime
```

### Generate Reports

```bash
# JSON report for programmatic processing
archive-rag check-compliance --output-format json --report-file compliance-report.json

# Markdown report for documentation
archive-rag check-compliance --output-format markdown --report-file compliance-report.md

# Text report (default)
archive-rag check-compliance --output-format text
```

## Static Analysis Examples

### Check Specific File

```bash
# Check a single file for violations
archive-rag check-compliance --static --file src/services/embedding.py
```

### Check Directory

```bash
# Check all files in a directory
archive-rag check-compliance --static --directory src/services/
```

### Verbose Output

```bash
# Get detailed violation information
archive-rag check-compliance --static --verbose
```

## Runtime Monitoring Examples

### Enable Runtime Monitoring

```bash
# Run with runtime monitoring enabled
archive-rag check-compliance --runtime

# Run a specific operation with monitoring
archive-rag query indexes/sample-meetings.faiss "test query" --compliance-check
```

### Monitor Entity Operations

```bash
# Entity operations are automatically monitored
archive-rag ingest-entities "https://example.com/meetings.json"
# Compliance checks run automatically during ingestion
```

## Integration Examples

### Pre-commit Hook

Create a pre-commit hook to check compliance before each commit:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run static analysis only (fast)
archive-rag check-compliance --static --no-tests --no-runtime

if [ $? -ne 0 ]; then
    echo "❌ Constitution violations detected. Fix before committing."
    echo "Run 'archive-rag check-compliance --static' for details."
    exit 1
fi

echo "✅ Compliance check passed"
exit 0
```

### CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
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
      - run: archive-rag check-compliance --output-format json --report-file compliance-report.json
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: compliance-report
          path: compliance-report.json
```

### Development Workflow

```bash
# 1. Before committing, run static analysis
archive-rag check-compliance --static

# 2. If violations found, fix them
# ... edit code ...

# 3. Run full compliance check
archive-rag check-compliance

# 4. Commit if all checks pass
git commit -m "Add feature X"
```

## Troubleshooting Common Violations

### Violation: External API Import

**Problem**: Static analysis detects `import requests` or `import openai`

**Solution**:
```python
# ❌ BAD: External API import
import requests
import openai

# ✅ GOOD: Use local alternatives
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer  # Local model
```

### Violation: HTTP Call in Source Code

**Problem**: Static analysis detects `requests.post()` or `httpx.get()`

**Solution**:
```python
# ❌ BAD: HTTP call to external API
response = requests.post("https://api.example.com/v1/endpoint", data=data)

# ✅ GOOD: Use local storage or local models
with open("local_data.json", "w") as f:
    json.dump(data, f)
```

### Violation: External Binary Execution

**Problem**: Static analysis detects `subprocess.run()` with external binary

**Solution**:
```python
# ❌ BAD: External binary execution
subprocess.run(["curl", "https://api.example.com"])

# ✅ GOOD: Use Python standard library
import urllib.request
with urllib.request.urlopen("https://api.example.com") as response:
    data = response.read()
```

### Violation: Remote Embedding Service

**Problem**: Runtime check detects HTTP request to embedding API

**Solution**:
```python
# ❌ BAD: Remote embedding service
from openai import OpenAI
client = OpenAI(api_key="...")
embedding = client.embeddings.create(model="text-embedding-3-small", input=text)

# ✅ GOOD: Local embedding service
from src.services.embedding import EmbeddingService
service = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
embedding = service.embed_text(text)
```

### Violation: Remote LLM Service

**Problem**: Runtime check detects HTTP request to LLM API

**Solution**:
```python
# ❌ BAD: Remote LLM service
from openai import OpenAI
client = OpenAI(api_key="...")
response = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)

# ✅ GOOD: Local LLM service
from transformers import pipeline
generator = pipeline("text-generation", model="gpt2")
response = generator(text)
```

## Best Practices

1. **Run checks before committing**: Use pre-commit hooks to catch violations early
2. **Check in CI/CD**: Automate compliance verification in your pipeline
3. **Fix violations immediately**: Don't accumulate violations over time
4. **Use local alternatives**: Always prefer local models and storage over remote APIs
5. **Monitor runtime**: Enable runtime monitoring for production-like testing

## Additional Resources

- **Quickstart Guide**: [specs/002-constitution-compliance/quickstart.md](../specs/002-constitution-compliance/quickstart.md)
- **Specification**: [specs/002-constitution-compliance/spec.md](../specs/002-constitution-compliance/spec.md)
- **Implementation Plan**: [specs/002-constitution-compliance/plan.md](../specs/002-constitution-compliance/plan.md)


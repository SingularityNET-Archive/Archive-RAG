# HuggingFace Models for Feature Extraction

## Overview

When using HuggingFace Inference API for embeddings, **not all models support feature extraction**. Many sentence-transformers models are configured for **sentence similarity** tasks, not direct feature extraction.

## Models That Support Feature Extraction

The following models have been tested and **work** with HuggingFace Inference API for feature extraction:

### Recommended Models

1. **BAAI/bge-small-en-v1.5** (Recommended)
   - Dimension: **384**
   - Fast and efficient
   - Good balance of quality and speed
   - ✅ Tested and working

2. **BAAI/bge-base-en-v1.5**
   - Dimension: **768**
   - Better quality than small model
   - Moderate speed
   - ✅ Tested and working

3. **BAAI/bge-large-en-v1.5**
   - Dimension: **1024**
   - Best quality
   - Slower than smaller models
   - ✅ Tested and working

## Models That DON'T Work (Similarity Only)

The following models are configured for **sentence similarity** and do NOT support feature extraction:

- ❌ `sentence-transformers/all-MiniLM-L6-v2` - Similarity pipeline
- ❌ `sentence-transformers/all-mpnet-base-v2` - Similarity pipeline
- ❌ `sentence-transformers/paraphrase-MiniLM-L6-v2` - Similarity pipeline
- ❌ `intfloat/e5-small-v2` - Similarity pipeline
- ❌ `intfloat/e5-base-v2` - Similarity pipeline
- ❌ `thenlper/gte-large` - Similarity pipeline
- ❌ `thenlper/gte-base` - Similarity pipeline
- ❌ `thenlper/gte-small` - Similarity pipeline

## Configuration

Update your `.env` file to use a working model:

```bash
ARCHIVE_RAG_PROCESSING_MODE=remote
ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
ARCHIVE_RAG_EMBEDDING_API_URL="https://api-inference.huggingface.co"
ARCHIVE_RAG_EMBEDDING_API_KEY="hf_your_api_key_here"
ARCHIVE_RAG_EMBEDDING_MODEL="BAAI/bge-small-en-v1.5"
```

## Testing

You can test if a model supports feature extraction:

```python
import requests

API_URL = "https://api-inference.huggingface.co/models/BAAI/bge-small-en-v1.5"
headers = {"Authorization": "Bearer YOUR_API_KEY"}

response = requests.post(
    API_URL,
    headers=headers,
    json={"inputs": ["Hello world"]},
    timeout=15
)

if response.status_code == 200:
    result = response.json()
    if isinstance(result, list) and isinstance(result[0], list):
        print(f"✓ Model supports feature extraction!")
        print(f"  Dimension: {len(result[0])}")
    else:
        print(f"✗ Model does not support feature extraction")
else:
    print(f"✗ Error: {response.status_code} - {response.text}")
```

## Alternative: Use Local sentence-transformers

If you prefer to use `sentence-transformers/all-MiniLM-L6-v2` or other similarity models, use the **local** sentence-transformers library instead:

```bash
# Disable remote embeddings to use local processing
ARCHIVE_RAG_PROCESSING_MODE=local
# or simply don't set ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
```

Local processing supports all sentence-transformers models and is the default (constitution-compliant) option.


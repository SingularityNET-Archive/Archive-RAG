# Remote Processing Configuration

**Note**: By default, Archive-RAG uses **local processing only** (constitution-compliant). Remote processing is an **opt-in feature** that can be enabled via environment variables to reduce local memory usage.

## Overview

Remote processing allows you to offload memory-intensive operations (embeddings and LLM inference) to remote API endpoints while keeping FAISS indexing and retrieval local. This reduces local memory usage significantly.

**Default Mode**: Local processing (constitution-compliant)
- ✅ Local embeddings (sentence-transformers)
- ✅ Local FAISS vector search
- ✅ No external API dependencies
- ✅ Offline-capable

**Remote Mode** (opt-in): Memory-efficient processing
- ✅ Remote embeddings (OpenAI, HuggingFace, or custom API)
- ✅ Remote LLM inference (OpenAI, HuggingFace, or custom API)
- ✅ Local FAISS vector search (still local for performance)
- ⚠️ Requires internet connection
- ⚠️ Requires API keys

## Setup

### 1. Enable Remote Processing

Set environment variables to enable remote processing:

```bash
# Enable remote processing mode
export ARCHIVE_RAG_PROCESSING_MODE=remote

# Configure embedding service (choose one)
export ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
export ARCHIVE_RAG_EMBEDDING_API_URL="https://api.openai.com/v1"  # or HuggingFace URL
export ARCHIVE_RAG_EMBEDDING_API_KEY="your-api-key-here"

# Configure LLM service (choose one)
export ARCHIVE_RAG_REMOTE_LLM=true
export ARCHIVE_RAG_LLM_API_URL="https://api.openai.com/v1"  # or HuggingFace URL
export ARCHIVE_RAG_LLM_API_KEY="your-api-key-here"
export ARCHIVE_RAG_LLM_MODEL="gpt-3.5-turbo"  # or "gpt-4", HuggingFace model, etc.
```

### 2. Supported APIs

#### OpenAI API

```bash
export ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
export ARCHIVE_RAG_EMBEDDING_API_URL="https://api.openai.com/v1"
export ARCHIVE_RAG_EMBEDDING_API_KEY="sk-..."
export ARCHIVE_RAG_EMBEDDING_MODEL="text-embedding-3-small"  # or "text-embedding-ada-002"

export ARCHIVE_RAG_REMOTE_LLM=true
export ARCHIVE_RAG_LLM_API_URL="https://api.openai.com/v1"
export ARCHIVE_RAG_LLM_API_KEY="sk-..."
export ARCHIVE_RAG_LLM_MODEL="gpt-3.5-turbo"
```

#### HuggingFace Inference API

**Note**: Many sentence-transformers models are configured for similarity tasks, not feature extraction. Use BAAI/bge models for embeddings:

```bash
export ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
export ARCHIVE_RAG_EMBEDDING_API_URL="https://router.huggingface.co/hf-inference"
export ARCHIVE_RAG_EMBEDDING_API_KEY="hf_..."  # or use HUGGINGFACE_API_KEY
export ARCHIVE_RAG_EMBEDDING_MODEL="BAAI/bge-small-en-v1.5"  # Recommended: supports feature extraction (384-dim)
# Alternative models that work:
# - BAAI/bge-base-en-v1.5 (768-dim)
# - BAAI/bge-large-en-v1.5 (1024-dim)

export ARCHIVE_RAG_REMOTE_LLM=true
export ARCHIVE_RAG_LLM_API_URL="https://router.huggingface.co/hf-inference"
export HUGGINGFACE_API_KEY="hf_..."
export ARCHIVE_RAG_LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.2"
```

#### Custom API Endpoint

```bash
export ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
export ARCHIVE_RAG_EMBEDDING_API_URL="https://your-custom-api.com/embeddings"
export ARCHIVE_RAG_EMBEDDING_API_KEY="your-api-key"

export ARCHIVE_RAG_REMOTE_LLM=true
export ARCHIVE_RAG_LLM_API_URL="https://your-custom-api.com/generate"
export ARCHIVE_RAG_LLM_API_KEY="your-api-key"
```

### 3. Usage

Once configured, use Archive-RAG normally:

```bash
# Remote embeddings will be used automatically if configured
archive-rag index data/meetings/ indexes/meetings.faiss

# Remote LLM will be used automatically if configured
archive-rag query indexes/meetings.faiss "What decisions were made?"
```

## Hybrid Mode

You can enable remote processing for only certain components:

```bash
# Use remote embeddings but local LLM (or template-based)
export ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
export ARCHIVE_RAG_REMOTE_LLM=false  # Keep LLM local
```

## Memory Comparison

### Local Processing (Default)
- **Embeddings**: ~200-500 MB per model (sentence-transformers)
- **LLM**: ~2-8 GB for small models (GPT-2), 20+ GB for larger models
- **FAISS Index**: ~50-200 MB for 10k documents
- **Total**: ~2.5-25 GB depending on models

### Remote Processing (Opt-in)
- **Embeddings**: 0 MB (API calls only)
- **LLM**: 0 MB (API calls only)
- **FAISS Index**: ~50-200 MB (still local for performance)
- **Total**: ~50-200 MB (just FAISS index)

## Constitution Compliance

**Important**: Remote processing is **opt-in** and **disabled by default**. The system:

- ✅ Defaults to local processing (constitution-compliant)
- ✅ Requires explicit environment variable configuration
- ✅ Falls back to local processing if remote services unavailable
- ✅ Maintains audit logging and reproducibility where possible

## Security Considerations

1. **API Keys**: Store API keys securely (use `.env` files, not in code)
2. **Data Privacy**: Remote APIs process your data - ensure compliance with privacy policies
3. **Rate Limiting**: Be aware of API rate limits and costs
4. **Offline Mode**: Keep local processing as fallback for offline scenarios

## Example `.env` File

Create a `.env` file in the project root:

```bash
# Remote Processing Configuration (opt-in)
ARCHIVE_RAG_PROCESSING_MODE=remote

# Embedding Service
ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
ARCHIVE_RAG_EMBEDDING_API_URL=https://api.openai.com/v1
ARCHIVE_RAG_EMBEDDING_API_KEY=sk-your-key-here

# LLM Service
ARCHIVE_RAG_REMOTE_LLM=true
ARCHIVE_RAG_LLM_API_URL=https://api.openai.com/v1
ARCHIVE_RAG_LLM_API_KEY=sk-your-key-here
ARCHIVE_RAG_LLM_MODEL=gpt-3.5-turbo

# HuggingFace (alternative)
# HUGGINGFACE_API_KEY=hf-your-key-here
```

Load with `python-dotenv`:

```bash
pip install python-dotenv
```

Then in your code or CLI wrapper:

```python
from dotenv import load_dotenv
load_dotenv()
```

## Troubleshooting

### Remote service not working

- Check environment variables are set correctly
- Verify API keys are valid
- Check network connectivity
- Review logs for error messages
- System will fall back to local processing automatically

### Memory still high

- Ensure `ARCHIVE_RAG_REMOTE_EMBEDDINGS=true` is set
- Ensure `ARCHIVE_RAG_REMOTE_LLM=true` is set
- Check that API URLs are correct
- Verify API keys are working

### Switching back to local

```bash
unset ARCHIVE_RAG_PROCESSING_MODE
unset ARCHIVE_RAG_REMOTE_EMBEDDINGS
unset ARCHIVE_RAG_REMOTE_LLM
```

Or set explicitly:

```bash
export ARCHIVE_RAG_PROCESSING_MODE=local
```

## Implementation Notes

- Remote services are lazy-loaded only when explicitly enabled
- Automatic fallback to local processing if remote fails
- All existing code continues to work without changes
- Constitution compliance maintained by default (local-first)


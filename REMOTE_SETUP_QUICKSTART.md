# Quick Start: Remote Processing Setup

## The Problem

Local models consume significant memory:
- **Embedding models**: 200-500 MB
- **LLM models**: 2-20+ GB
- **Total local memory**: ~2.5-25 GB

## The Solution

Use remote API endpoints for memory-intensive operations while keeping FAISS indexing local.

## Quick Setup (OpenAI Example)

### 1. Set Environment Variables

```bash
# Enable remote processing
export ARCHIVE_RAG_PROCESSING_MODE=remote

# Embeddings via OpenAI
export ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
export ARCHIVE_RAG_EMBEDDING_API_URL="https://api.openai.com/v1"
export ARCHIVE_RAG_EMBEDDING_API_KEY="sk-your-key-here"
export ARCHIVE_RAG_EMBEDDING_MODEL="text-embedding-3-small"

# LLM via OpenAI
export ARCHIVE_RAG_REMOTE_LLM=true
export ARCHIVE_RAG_LLM_API_URL="https://api.openai.com/v1"
export ARCHIVE_RAG_LLM_API_KEY="sk-your-key-here"
export ARCHIVE_RAG_LLM_MODEL="gpt-3.5-turbo"
```

### 2. Use Archive-RAG Normally

```bash
# Indexing uses remote embeddings (saves ~200-500 MB)
archive-rag index data/meetings/ indexes/meetings.faiss

# Queries use remote LLM (saves ~2-20 GB)
archive-rag query indexes/meetings.faiss "What decisions were made?"
```

## Memory Savings

- **Before**: ~2.5-25 GB local memory
- **After**: ~50-200 MB local memory (just FAISS index)
- **Savings**: ~95-99% reduction in local memory usage

## Supported Providers

### OpenAI
```bash
export ARCHIVE_RAG_EMBEDDING_API_URL="https://api.openai.com/v1"
export ARCHIVE_RAG_LLM_API_URL="https://api.openai.com/v1"
```

### HuggingFace Inference API
```bash
export ARCHIVE_RAG_EMBEDDING_API_URL="https://api-inference.huggingface.co"
export ARCHIVE_RAG_LLM_API_URL="https://api-inference.huggingface.co"
export HUGGINGFACE_API_KEY="hf-your-key-here"
```

### Custom API Endpoint
```bash
export ARCHIVE_RAG_EMBEDDING_API_URL="https://your-api.com/embeddings"
export ARCHIVE_RAG_LLM_API_URL="https://your-api.com/generate"
```

## Disable Remote Processing

To go back to local processing:

```bash
unset ARCHIVE_RAG_PROCESSING_MODE
unset ARCHIVE_RAG_REMOTE_EMBEDDINGS
unset ARCHIVE_RAG_REMOTE_LLM
```

Or set explicitly:

```bash
export ARCHIVE_RAG_PROCESSING_MODE=local
```

## Important Notes

1. **Default is LOCAL**: System defaults to local processing (constitution-compliant)
2. **Opt-in Only**: Remote processing requires explicit configuration
3. **Automatic Fallback**: Falls back to local if remote unavailable
4. **FAISS Stays Local**: Vector search remains local for performance

For detailed documentation, see [REMOTE_PROCESSING.md](REMOTE_PROCESSING.md)


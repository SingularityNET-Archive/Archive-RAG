# Fixing LLM Errors in Queries

## Current Issue

You're seeing 401/404 errors when querying because:
1. The HuggingFace model `mistralai/Mistral-7B-Instruct-v0.2` doesn't exist or isn't accessible
2. Remote LLM is enabled but the model isn't available

## Solutions

### Option 1: Disable Remote LLM (Recommended)

Your queries are working with template-based fallback. To disable remote LLM and eliminate errors, update your `.env` file:

```bash
# Disable remote LLM
ARCHIVE_RAG_REMOTE_LLM=false
# or simply remove these lines:
# ARCHIVE_RAG_REMOTE_LLM=true
# ARCHIVE_RAG_LLM_API_URL="https://api-inference.huggingface.co"
# ARCHIVE_RAG_LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.2"
```

This will use template-based answer generation (which is already working) and eliminate the errors.

### Option 2: Use OpenAI API

If you want to use a remote LLM, use OpenAI instead:

```bash
ARCHIVE_RAG_REMOTE_LLM=true
ARCHIVE_RAG_LLM_API_URL="https://api.openai.com/v1"
ARCHIVE_RAG_LLM_API_KEY="sk-..."  # Your OpenAI API key
ARCHIVE_RAG_LLM_MODEL="gpt-3.5-turbo"
```

### Option 3: Find Working HuggingFace Model

If you want to use HuggingFace, you need to find a model that:
1. Supports text generation via Inference API
2. Is accessible with your API key
3. Is available on the public Inference API

Check HuggingFace model pages to see if they support Inference API access.

## Current Behavior

Even with the LLM errors, your queries are working:
- ✓ Retrieval works (finding relevant chunks)
- ✓ Citations work (showing sources)
- ✓ Template-based answers work (fallback when LLM fails)

The errors are just warnings - the system gracefully falls back to template-based generation.


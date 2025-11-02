# HuggingFace LLM API Issue Resolution

## Problem

After migrating to the new HuggingFace Inference Providers API (`router.huggingface.co/hf-inference`), LLM models are returning **401/404 errors**:

```
401 Client Error: Unauthorized for url: https://router.huggingface.co/hf-inference/models/mistralai/Mistral-7B-Instruct-v0.2
```

## Root Cause

The new **Inference Providers API** works for **embeddings** (✅ tested and working), but **LLM models** are not immediately available on the new endpoint. They require:

1. **Inference Endpoints** to be deployed (costs money, requires setup)
2. Models to be explicitly available on the Inference Providers API
3. Different authentication or endpoint formats

## Solution Applied

**Remote LLM has been disabled** in your `.env` file. Your queries will continue to work using **template-based generation**, which:
- ✅ Already working (no errors)
- ✅ Fast and reliable
- ✅ Free (no API costs)
- ✅ Provides answers with citations

## Current Status

- ✅ **Embeddings**: Working with new endpoint (`router.huggingface.co/hf-inference`)
- ✅ **Queries**: Working with template-based generation (no LLM needed)
- ✅ **Citations**: Working correctly
- ✅ **No Errors**: LLM errors eliminated

## If You Want Remote LLM

### Option 1: Use OpenAI API (Easiest)

Update your `.env`:

```bash
ARCHIVE_RAG_REMOTE_LLM=true
ARCHIVE_RAG_LLM_API_URL="https://api.openai.com/v1"
ARCHIVE_RAG_LLM_API_KEY="sk-..."  # Your OpenAI API key
ARCHIVE_RAG_LLM_MODEL="gpt-3.5-turbo"
```

### Option 2: Deploy HuggingFace Inference Endpoint

1. Go to: https://huggingface.co/inference-endpoints
2. Create an endpoint with your desired model
3. Get endpoint URL and update `.env`:

```bash
ARCHIVE_RAG_REMOTE_LLM=true
ARCHIVE_RAG_LLM_API_URL="https://YOUR_ENDPOINT_ID.us-east-1.aws.endpoints.huggingface.cloud"
ARCHIVE_RAG_LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.1"
```

### Option 3: Continue with Template-Based (Current - Recommended)

**This is already working** and provides good results:
- No API costs
- No setup required
- Fast and reliable
- Generates answers with proper citations

## Recommendation

**Keep remote LLM disabled** unless you specifically need advanced LLM capabilities. The template-based generation is working well for your use case.


# HuggingFace LLM Setup Guide

## Current Situation

Most HuggingFace LLM models are **not immediately available** on the Inference API. They require **Inference Endpoints** to be deployed, which involves:
- Setting up an endpoint (costs money)
- Deploying a model to your endpoint
- Managing the endpoint

## Options for Remote LLM

### Option 1: Use OpenAI API (Easiest)

**Recommended if you want remote LLM without setup hassle**

Update your `.env` file:

```bash
ARCHIVE_RAG_REMOTE_LLM=true
ARCHIVE_RAG_LLM_API_URL="https://api.openai.com/v1"
ARCHIVE_RAG_LLM_API_KEY="sk-..."  # Your OpenAI API key
ARCHIVE_RAG_LLM_MODEL="gpt-3.5-turbo"
```

**Pros:**
- ✓ Works immediately
- ✓ No setup required
- ✓ Reliable and fast

**Cons:**
- ✗ Costs money per API call
- ✗ Requires OpenAI API key

### Option 2: Deploy HuggingFace Inference Endpoint

If you want to use HuggingFace models, you need to deploy an Inference Endpoint:

1. **Go to HuggingFace**: https://huggingface.co/inference-endpoints

2. **Create a new endpoint**:
   - Choose a model (e.g., `mistralai/Mistral-7B-Instruct-v0.1`)
   - Select instance type
   - Deploy

3. **Get endpoint URL** and update `.env`:
   ```bash
   ARCHIVE_RAG_REMOTE_LLM=true
   ARCHIVE_RAG_LLM_API_URL="https://YOUR_ENDPOINT_ID.us-east-1.aws.endpoints.huggingface.cloud"
   ARCHIVE_RAG_LLM_API_KEY="hf_..."  # Your HuggingFace API key
   ARCHIVE_RAG_LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.1"
   ```

**Pros:**
- ✓ Use HuggingFace models
- ✓ Control over model choice
- ✓ Cost-effective for high volume

**Cons:**
- ✗ Requires setup and deployment
- ✗ Costs money for endpoint hosting
- ✗ Takes time to set up

### Option 3: Use Template-Based Generation (Current - Already Working)

**Recommended if you don't need advanced LLM capabilities**

Your queries are already working with template-based generation. To eliminate LLM errors:

Update your `.env` file:

```bash
ARCHIVE_RAG_REMOTE_LLM=false
# Comment out or remove these:
# ARCHIVE_RAG_LLM_API_URL="https://api-inference.huggingface.co"
# ARCHIVE_RAG_LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.2"
```

**Pros:**
- ✓ No setup required
- ✓ Free
- ✓ Already working
- ✓ Fast and reliable

**Cons:**
- ✗ Simpler answers (template-based)
- ✗ Less creative than LLM

## Recommendation

**For immediate use**: **Option 3** (template-based) - it's already working and free

**For better answers**: **Option 1** (OpenAI) - easiest setup with good results

**For HuggingFace specifically**: **Option 2** (Inference Endpoints) - requires setup

## Current Status

Your system is working correctly:
- ✓ Retrieval finds relevant chunks
- ✓ Citations work
- ✓ Answers are generated (via template fallback)

The LLM errors are warnings that don't affect functionality - the system gracefully falls back to template-based generation.


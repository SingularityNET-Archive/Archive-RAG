# HuggingFace API Migration Guide

## Important: API Endpoint Deprecation

**HuggingFace has deprecated the old `api-inference.huggingface.co` endpoint** and it will return 404 errors starting November 1st, 2025.

## Migration Required

You need to update your `.env` file to use the new **Inference Providers API** endpoint:

### Old Endpoint (Deprecated)
```
https://api-inference.huggingface.co
```

### New Endpoint (Required)
```
https://router.huggingface.co/hf-inference
```

## Update Your `.env` File

Change these lines:

**Before:**
```bash
ARCHIVE_RAG_EMBEDDING_API_URL="https://api-inference.huggingface.co"
ARCHIVE_RAG_LLM_API_URL="https://api-inference.huggingface.co"
```

**After:**
```bash
ARCHIVE_RAG_EMBEDDING_API_URL="https://router.huggingface.co/hf-inference"
ARCHIVE_RAG_LLM_API_URL="https://router.huggingface.co/hf-inference"
```

## What Changed?

1. **Code Updated**: The default URL in the code has been updated to the new endpoint
2. **Compatibility**: The new endpoint is compatible with the same API format
3. **Features**: New endpoint provides access to more models through a unified API

## Verification

The new endpoint has been tested and works with:
- ✓ Embeddings: `BAAI/bge-small-en-v1.5` (200 OK)
- ✓ Same API format and authentication

## Additional Information

- **Documentation**: https://huggingface.co/docs/inference-providers
- **Migration**: Simply replace the URL - no other changes needed
- **Deadline**: Old endpoint will stop working November 1st, 2025

## Note

The code has been updated to use the new endpoint by default. If you have the old URL in your `.env` file, please update it.


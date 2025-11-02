# Remote Processing Setup Guide

## Quick Check: Is Remote Processing Enabled?

Run this command to check your current configuration:

```bash
python3 check_remote_status.py
```

## Setting Up Remote Processing

### Step 1: Install python-dotenv (if not already installed)

```bash
pip install python-dotenv
# or
python3 -m pip install python-dotenv
```

### Step 2: Configure .env File

Create or edit `.env` file in the project root with your remote API settings:

```bash
# Remote Embeddings Configuration
ARCHIVE_RAG_PROCESSING_MODE=remote
ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
ARCHIVE_RAG_EMBEDDING_API_URL=https://api.openai.com/v1
ARCHIVE_RAG_EMBEDDING_API_KEY=your-openai-api-key-here

# Remote LLM Configuration (optional)
ARCHIVE_RAG_REMOTE_LLM=true
ARCHIVE_RAG_LLM_API_URL=https://api.openai.com/v1
ARCHIVE_RAG_LLM_API_KEY=your-openai-api-key-here
ARCHIVE_RAG_LLM_MODEL=gpt-3.5-turbo
```

### Step 3: Verify Configuration

```bash
# Check if variables are loaded
python3 check_remote_status.py

# Or check manually
python3 -c "from src.lib.remote_config import get_embedding_remote_config; emb_enabled, emb_url, _ = get_embedding_remote_config(); print(f'Embedding Remote: {emb_enabled}, URL: {emb_url}')"
```

## Environment Variables Reference

### Required Variables for Remote Embeddings

- `ARCHIVE_RAG_PROCESSING_MODE=remote` - Enable remote processing mode
- `ARCHIVE_RAG_REMOTE_EMBEDDINGS=true` - Enable remote embeddings
- `ARCHIVE_RAG_EMBEDDING_API_URL` - API endpoint URL (e.g., `https://api.openai.com/v1`)
- `ARCHIVE_RAG_EMBEDDING_API_KEY` - Your API key

### Optional Variables for Remote LLM

- `ARCHIVE_RAG_REMOTE_LLM=true` - Enable remote LLM
- `ARCHIVE_RAG_LLM_API_URL` - LLM API endpoint URL
- `ARCHIVE_RAG_LLM_API_KEY` - LLM API key
- `ARCHIVE_RAG_LLM_MODEL` - Model name (default: `gpt-3.5-turbo`)

## Troubleshooting

### Issue: .env file not being loaded

**Solution**: Ensure `python-dotenv` is installed:

```bash
pip install python-dotenv
```

### Issue: Variables show as "NOT SET"

**Check**:
1. `.env` file exists in project root
2. Variable names are correct (no typos)
3. No spaces around `=` sign: `KEY=value` (not `KEY = value`)
4. Values are not quoted (unless needed for special characters)

**Verify format**:
```bash
# Correct format:
ARCHIVE_RAG_REMOTE_EMBEDDINGS=true

# Wrong format:
ARCHIVE_RAG_REMOTE_EMBEDDINGS = true  # No spaces!
ARCHIVE_RAG_REMOTE_EMBEDDINGS="true"  # No quotes needed for boolean
```

### Issue: Still showing "Local" after setting .env

**Solution**: Restart your Python process. Environment variables are loaded when the module is imported.

```bash
# Re-run the check
python3 check_remote_status.py
```

## Example .env File

```bash
# Archive-RAG Remote Processing Configuration

# Enable remote processing
ARCHIVE_RAG_PROCESSING_MODE=remote

# Remote Embeddings (OpenAI)
ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
ARCHIVE_RAG_EMBEDDING_API_URL=https://api.openai.com/v1
ARCHIVE_RAG_EMBEDDING_API_KEY=sk-...

# Remote LLM (OpenAI)
ARCHIVE_RAG_REMOTE_LLM=true
ARCHIVE_RAG_LLM_API_URL=https://api.openai.com/v1
ARCHIVE_RAG_LLM_API_KEY=sk-...
ARCHIVE_RAG_LLM_MODEL=gpt-3.5-turbo
```

## Notes

- The `.env` file is loaded automatically when `src.lib.remote_config` is imported
- Environment variables take precedence over `.env` file values
- If remote API is unavailable, the system automatically falls back to local processing
- Remote processing is **opt-in** - default is local (constitution-compliant)


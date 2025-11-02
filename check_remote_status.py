#!/usr/bin/env python3
"""Check if remote processing is enabled and configured."""

import os
from src.lib.remote_config import (
    is_remote_processing_enabled,
    get_embedding_remote_config,
    get_llm_remote_config,
    get_entity_extraction_remote_config,
    REMOTE_PROCESSING_MODE,
    EMBEDDING_REMOTE_ENABLED,
    LLM_REMOTE_ENABLED,
    ENTITY_EXTRACTION_REMOTE_ENABLED
)


def print_remote_status():
    """Print remote processing status."""
    print("=" * 60)
    print("Archive-RAG Remote Processing Status")
    print("=" * 60)
    print()
    
    # Overall status
    print("Overall Status:")
    print(f"  Processing Mode: {REMOTE_PROCESSING_MODE}")
    print(f"  Remote Enabled: {is_remote_processing_enabled()}")
    print()
    
    # Environment variables
    print("Environment Variables:")
    env_vars = [
        "ARCHIVE_RAG_PROCESSING_MODE",
        "ARCHIVE_RAG_REMOTE_EMBEDDINGS",
        "ARCHIVE_RAG_EMBEDDING_API_URL",
        "ARCHIVE_RAG_EMBEDDING_API_KEY",
        "ARCHIVE_RAG_REMOTE_LLM",
        "ARCHIVE_RAG_LLM_API_URL",
        "ARCHIVE_RAG_LLM_API_KEY",
        "ARCHIVE_RAG_LLM_MODEL",
        "HUGGINGFACE_API_KEY"
    ]
    
    for var in env_vars:
        value = os.getenv(var, "NOT SET")
        if "KEY" in var and value != "NOT SET":
            value = "***SET***"  # Don't show actual keys
        print(f"  {var}: {value}")
    print()
    
    # Embedding service
    print("Embedding Service:")
    emb_enabled, emb_url, emb_key = get_embedding_remote_config()
    print(f"  Remote Enabled: {emb_enabled}")
    print(f"  API URL: {emb_url or 'None (using local)'}")
    print(f"  API Key: {'Set' if emb_key else 'Not set'}")
    if not emb_enabled:
        print("  → Using LOCAL sentence-transformers")
    else:
        print(f"  → Using REMOTE API: {emb_url}")
    print()
    
    # LLM service
    print("LLM Service:")
    llm_enabled, llm_url, llm_key, llm_model = get_llm_remote_config()
    print(f"  Remote Enabled: {llm_enabled}")
    print(f"  API URL: {llm_url or 'None (using local)'}")
    print(f"  API Key: {'Set' if llm_key else 'Not set'}")
    print(f"  Model: {llm_model}")
    if not llm_enabled:
        print("  → Using LOCAL transformers model")
    else:
        print(f"  → Using REMOTE API: {llm_url} (model: {llm_model})")
    print()
    
    # Entity extraction service
    print("Entity Extraction Service:")
    ext_enabled, ext_url = get_entity_extraction_remote_config()
    print(f"  Remote Enabled: {ext_enabled}")
    print(f"  API URL: {ext_url or 'None (using local)'}")
    if not ext_enabled:
        print("  → Using LOCAL spaCy/NER model")
    else:
        print(f"  → Using REMOTE API: {ext_url}")
    print()
    
    # Summary
    print("Summary:")
    if is_remote_processing_enabled():
        print("  ⚠️  REMOTE PROCESSING IS ENABLED")
        print("     - Remote API calls will be made for configured services")
        print("     - Falls back to local if remote unavailable")
    else:
        print("  ✓  LOCAL PROCESSING (constitution-compliant default)")
        print("     - All processing happens locally")
        print("     - No external API dependencies")
    print()
    print("=" * 60)


if __name__ == "__main__":
    print_remote_status()


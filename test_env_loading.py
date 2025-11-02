#!/usr/bin/env python3
"""Test if .env file is being loaded correctly."""

from pathlib import Path
import os

# Try to load .env
try:
    from dotenv import load_dotenv
    env_path = Path(".env")
    if env_path.exists():
        print(f"✓ .env file found at: {env_path.absolute()}")
        load_dotenv(dotenv_path=env_path, override=False)
        print("✓ .env file loaded")
    else:
        print(f"✗ .env file not found at: {env_path.absolute()}")
except ImportError:
    print("✗ python-dotenv not installed. Run: pip install python-dotenv")

# Check variables
vars_to_check = [
    "ARCHIVE_RAG_PROCESSING_MODE",
    "ARCHIVE_RAG_REMOTE_EMBEDDINGS",
    "ARCHIVE_RAG_EMBEDDING_API_URL",
    "ARCHIVE_RAG_EMBEDDING_API_KEY",
]

print("\nEnvironment Variables:")
for var in vars_to_check:
    value = os.getenv(var, "NOT SET")
    if "KEY" in var and value != "NOT SET":
        value = "***SET*** (hidden)"
    print(f"  {var}: {value}")

# Check if config module sees them
print("\nConfig Module Status:")
try:
    # Import will trigger .env loading in remote_config
    from src.lib.remote_config import (
        REMOTE_PROCESSING_MODE,
        EMBEDDING_REMOTE_ENABLED,
        EMBEDDING_REMOTE_API_URL
    )
    print(f"  Processing Mode: {REMOTE_PROCESSING_MODE}")
    print(f"  Embedding Remote Enabled: {EMBEDDING_REMOTE_ENABLED}")
    print(f"  Embedding API URL: {EMBEDDING_REMOTE_API_URL or 'None (local)'}")
except Exception as e:
    print(f"  Error loading config: {e}")

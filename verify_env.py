#!/usr/bin/env python3
"""Verify .env file format and show what's needed for remote embeddings."""

from pathlib import Path
import os

def check_env_file():
    """Check .env file format and content."""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ .env file not found!")
        print("\nCreate .env file in project root with:")
        print_required_format()
        return
    
    print(f"✓ .env file found: {env_path.absolute()}")
    
    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=False)
        print("✓ .env file loaded")
    except ImportError:
        print("❌ python-dotenv not installed. Run: pip install python-dotenv")
        return
    
    # Check required variables for remote embeddings
    print("\n" + "="*60)
    print("Remote Embeddings Configuration Check")
    print("="*60)
    
    required_vars = {
        "ARCHIVE_RAG_PROCESSING_MODE": "remote",
        "ARCHIVE_RAG_REMOTE_EMBEDDINGS": "true",
        "ARCHIVE_RAG_EMBEDDING_API_URL": None,  # Must be set, no default
        "ARCHIVE_RAG_EMBEDDING_API_KEY": None,  # Must be set, no default
    }
    
    all_set = True
    for var, expected_value in required_vars.items():
        value = os.getenv(var)
        if value is None:
            print(f"❌ {var}: NOT SET")
            all_set = False
        elif expected_value and value.lower() != expected_value.lower():
            print(f"⚠️  {var}: {value} (expected: {expected_value})")
        elif "KEY" in var:
            print(f"✓  {var}: ***SET*** (hidden)")
        elif "URL" in var:
            print(f"✓  {var}: {value}")
        else:
            print(f"✓  {var}: {value}")
    
    if all_set:
        print("\n✓ All required variables are set!")
        print("\nVerifying configuration...")
        
        # Check if config module sees them
        try:
            from src.lib.remote_config import (
                REMOTE_PROCESSING_MODE,
                EMBEDDING_REMOTE_ENABLED,
                EMBEDDING_REMOTE_API_URL,
                get_embedding_remote_config
            )
            
            emb_enabled, emb_url, emb_key = get_embedding_remote_config()
            
            print(f"\nConfig Module Status:")
            print(f"  Processing Mode: {REMOTE_PROCESSING_MODE}")
            print(f"  Embedding Remote Enabled: {emb_enabled}")
            print(f"  Embedding API URL: {emb_url or 'None'}")
            print(f"  API Key Set: {bool(emb_key)}")
            
            if emb_enabled and emb_url:
                print("\n✅ REMOTE EMBEDDINGS ARE ENABLED!")
                print(f"   Using API: {emb_url}")
            else:
                print("\n⚠️  Remote embeddings not fully enabled")
                print("   Check that all variables are set correctly")
        except Exception as e:
            print(f"\n❌ Error loading config: {e}")
    else:
        print("\n" + "="*60)
        print("Required .env Format:")
        print("="*60)
        print_required_format()


def print_required_format():
    """Print required .env file format."""
    print("""
# .env file format (required variables for remote embeddings):
ARCHIVE_RAG_PROCESSING_MODE=remote
ARCHIVE_RAG_REMOTE_EMBEDDINGS=true
ARCHIVE_RAG_EMBEDDING_API_URL=https://api.openai.com/v1
ARCHIVE_RAG_EMBEDDING_API_KEY=your-api-key-here

# Notes:
# - No spaces around = sign
# - Values are not quoted (unless needed)
# - Boolean values: true/false (lowercase)
# - One variable per line
""")


if __name__ == "__main__":
    check_env_file()


"""Bot configuration management for Discord bot."""

import os
from pathlib import Path
from typing import Optional

from ..lib.config import BASE_DIR, INDEXES_DIR

# Discord bot token (required)
DISCORD_BOT_TOKEN: Optional[str] = os.getenv("DISCORD_BOT_TOKEN")

# Default RAG index path
DEFAULT_INDEX_PATH: str = os.getenv("ARCHIVE_RAG_INDEX_PATH", str(INDEXES_DIR / "meetings.faiss"))

# Rate limiting configuration
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("DISCORD_RATE_LIMIT_PER_MINUTE", "10"))
RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("DISCORD_RATE_LIMIT_WINDOW_SECONDS", "60"))

# Discord message limits
DISCORD_MAX_MESSAGE_LENGTH: int = 2000
DISCORD_MESSAGE_SAFETY_MARGIN: int = 100  # Safety margin for splitting

# Bot configuration validation
def validate_config() -> tuple[bool, Optional[str]]:
    """
    Validate bot configuration.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not DISCORD_BOT_TOKEN:
        return False, "DISCORD_BOT_TOKEN environment variable is required"
    
    if not Path(DEFAULT_INDEX_PATH).exists():
        return False, f"RAG index not found at {DEFAULT_INDEX_PATH}"
    
    return True, None


def get_discord_token() -> str:
    """
    Get Discord bot token from environment.
    
    Returns:
        Discord bot token
        
    Raises:
        ValueError: If token is not configured
    """
    if not DISCORD_BOT_TOKEN:
        raise ValueError(
            "DISCORD_BOT_TOKEN environment variable is required. "
            "Set it in your environment or .env file."
        )
    return DISCORD_BOT_TOKEN


def get_index_path() -> str:
    """
    Get RAG index path from configuration.
    
    Returns:
        Path to FAISS index file
    """
    return DEFAULT_INDEX_PATH



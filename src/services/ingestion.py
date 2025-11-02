"""JSON ingestion service for meeting records."""

from pathlib import Path
from typing import List, Optional
import json

from ..models.meeting_record import MeetingRecord
from ..lib.hashing import compute_file_hash, verify_file_hash
from ..lib.validation import validate_json_file, validate_required_fields
from ..lib.logging import get_logger

logger = get_logger(__name__)


def ingest_meeting_file(
    file_path: Path,
    verify_hash: Optional[str] = None
) -> tuple[MeetingRecord, str]:
    """
    Ingest a meeting JSON file and create MeetingRecord.
    
    Args:
        file_path: Path to meeting JSON file
        verify_hash: Expected SHA-256 hash for verification (optional)
        
    Returns:
        Tuple of (MeetingRecord, file_hash)
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If JSON is invalid or missing required fields
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Meeting file not found: {file_path}")
    
    # Validate JSON
    data = validate_json_file(file_path)
    
    # Validate required fields
    required_fields = ["id", "date", "participants", "transcript"]
    validate_required_fields(data, required_fields)
    
    # Create MeetingRecord
    meeting_record = MeetingRecord(**data)
    
    # Compute SHA-256 hash
    file_hash = compute_file_hash(file_path)
    
    # Verify hash if provided
    if verify_hash:
        if not verify_file_hash(file_path, verify_hash):
            raise ValueError(f"Hash mismatch for file: {file_path}")
    
    logger.info(
        "meeting_ingested",
        meeting_id=meeting_record.id,
        file_path=str(file_path),
        hash=file_hash
    )
    
    return meeting_record, file_hash


def ingest_meeting_directory(
    directory: Path,
    verify_hashes: Optional[dict[str, str]] = None
) -> List[tuple[MeetingRecord, str]]:
    """
    Ingest all meeting JSON files from a directory.
    
    Args:
        directory: Directory containing meeting JSON files
        verify_hashes: Dictionary mapping file paths to expected hashes (optional)
        
    Returns:
        List of tuples (MeetingRecord, file_hash)
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    json_files = list(directory.glob("*.json"))
    if not json_files:
        logger.warning("no_json_files_found", directory=str(directory))
        return []
    
    results = []
    verify_hashes = verify_hashes or {}
    
    for json_file in json_files:
        try:
            verify_hash = verify_hashes.get(str(json_file))
            meeting_record, file_hash = ingest_meeting_file(json_file, verify_hash)
            results.append((meeting_record, file_hash))
        except Exception as e:
            logger.error(
                "ingestion_failed",
                file_path=str(json_file),
                error=str(e)
            )
            # Continue processing other files
            continue
    
    logger.info(
        "directory_ingested",
        directory=str(directory),
        total_files=len(json_files),
        successful=len(results)
    )
    
    return results


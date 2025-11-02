"""JSON ingestion service for meeting records."""

from pathlib import Path
from typing import List, Optional, Union
import json
import hashlib
import urllib.request
import urllib.parse

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
    
    # Validate required fields (support both new and legacy formats)
    # Check if new format (workgroup_id + meetingInfo) or legacy format (id + date + participants + transcript)
    has_new_format = "workgroup_id" in data and "meetingInfo" in data
    has_legacy_format = "id" in data and "date" in data and "participants" in data and "transcript" in data
    
    if not has_new_format and not has_legacy_format:
        # Try to validate with flexible check (let MeetingRecord handle normalization)
        # Don't raise error here - let Pydantic validation handle it
        pass
    
    # Legacy format: explicit check
    if has_legacy_format:
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


def ingest_meeting_url(
    url: str,
    verify_hash: Optional[str] = None
) -> List[tuple[MeetingRecord, str]]:
    """
    Ingest meeting records from a URL (supports JSON array or single object).
    
    Args:
        url: URL to fetch JSON data from
        verify_hash: Expected SHA-256 hash for verification (optional)
        
    Returns:
        List of tuples (MeetingRecord, file_hash) - one per meeting in the array
    """
    try:
        # Fetch JSON from URL
        logger.info("fetching_url", url=url)
        with urllib.request.urlopen(url, timeout=30) as response:
            data_bytes = response.read()
            data_text = data_bytes.decode('utf-8')
    except Exception as e:
        logger.error("url_fetch_failed", url=url, error=str(e))
        raise ValueError(f"Failed to fetch URL {url}: {e}")
    
    # Compute hash of fetched content
    content_hash = hashlib.sha256(data_bytes).hexdigest()
    
    # Verify hash if provided
    if verify_hash:
        if content_hash != verify_hash:
            raise ValueError(f"Hash mismatch for URL: {url}")
    
    # Parse JSON
    try:
        data = json.loads(data_text)
    except json.JSONDecodeError as e:
        logger.error("json_parse_failed", url=url, error=str(e))
        raise ValueError(f"Invalid JSON from URL {url}: {e}")
    
    # Handle array or single object
    if isinstance(data, list):
        # Array of meetings
        meetings_data = data
        logger.info("url_contains_array", url=url, count=len(meetings_data))
    elif isinstance(data, dict):
        # Single meeting object
        meetings_data = [data]
        logger.info("url_contains_single_object", url=url)
    else:
        raise ValueError(f"URL {url} must contain a JSON object or array")
    
    # Process each meeting
    results = []
    for i, meeting_data in enumerate(meetings_data):
        try:
            # Create MeetingRecord from data
            meeting_record = MeetingRecord(**meeting_data)
            
            # Use content hash (same for all from same URL)
            # But add index for uniqueness if needed
            meeting_hash = content_hash if len(meetings_data) == 1 else f"{content_hash}_{i}"
            
            logger.info(
                "meeting_ingested_from_url",
                url=url,
                meeting_id=meeting_record.id,
                index=i,
                hash=meeting_hash
            )
            
            results.append((meeting_record, meeting_hash))
        except Exception as e:
            logger.error(
                "meeting_ingestion_failed_from_url",
                url=url,
                index=i,
                error=str(e)
            )
            # Continue processing other meetings
            continue
    
    logger.info(
        "url_ingested",
        url=url,
        total_meetings=len(meetings_data),
        successful=len(results)
    )
    
    return results


def ingest_meeting_directory(
    directory: Union[Path, str],
    verify_hashes: Optional[dict[str, str]] = None
) -> List[tuple[MeetingRecord, str]]:
    """
    Ingest all meeting JSON files from a directory or URL.
    
    Args:
        directory: Directory path (Path) or URL (str) containing meeting JSON files
        verify_hashes: Dictionary mapping file paths/URLs to expected hashes (optional)
        
    Returns:
        List of tuples (MeetingRecord, file_hash)
    """
    # Convert Path to string for checking
    directory_str = str(directory) if isinstance(directory, Path) else directory
    
    # Handle URL input (check for http://, https://, http:/, https:/ - Path normalizes // to /)
    is_url = (
        directory_str.startswith("http://") or 
        directory_str.startswith("https://") or
        directory_str.startswith("http:/") or 
        directory_str.startswith("https:/")
    )
    
    if is_url:
        # Restore proper URL format if Path normalized it
        if directory_str.startswith("http:/") and not directory_str.startswith("http://"):
            directory_str = directory_str.replace("http:/", "http://", 1)
        elif directory_str.startswith("https:/") and not directory_str.startswith("https://"):
            directory_str = directory_str.replace("https:/", "https://", 1)
        
        verify_hash = verify_hashes.get(directory_str) if verify_hashes else None
        return ingest_meeting_url(directory_str, verify_hash)
    
    # Handle directory path
    directory_path = Path(directory)
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    json_files = list(directory_path.glob("*.json"))
    if not json_files:
        logger.warning("no_json_files_found", directory=str(directory_path))
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
        directory=str(directory_path),
        total_files=len(json_files),
        successful=len(results)
    )
    
    return results


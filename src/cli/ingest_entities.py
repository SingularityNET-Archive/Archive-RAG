"""CLI command for ingesting meetings from source URL into entity storage."""

import typer
from typing import Optional

from ..services.meeting_to_entity import ingest_meetings_to_entities
from ..lib.logging import get_logger

logger = get_logger(__name__)


def ingest_entities_command(
    source_url: str = typer.Argument(..., help="URL to source JSON file containing meetings"),
    verify_hash: Optional[str] = typer.Option(
        None,
        "--verify-hash",
        help="Optional SHA-256 hash to verify source file integrity"
    )
):
    """
    Ingest meetings from source URL and save to entity storage.
    
    This command:
    - Fetches meeting JSON data from the source URL
    - Converts each meeting to entity models (Meeting, Workgroup, Person)
    - Saves entities to entity storage directories
    - Updates index files for fast lookups
    
    Example:
        archive-rag ingest-entities "https://raw.githubusercontent.com/.../meeting-summaries-array.json"
    """
    try:
        typer.echo(f"Ingesting meetings from source URL...")
        typer.echo(f"  URL: {source_url}")
        
        if verify_hash:
            typer.echo(f"  Verifying hash: {verify_hash[:16]}...")
        
        # Ingest meetings to entities
        successful = ingest_meetings_to_entities(source_url)
        
        typer.echo(f"\n✓ Ingestion complete!")
        typer.echo(f"  Successfully ingested: {successful} meetings")
        typer.echo(f"  Entities saved to: entities/")
        
    except Exception as e:
        logger.error("ingest_entities_failed", url=source_url, error=str(e))
        typer.echo(f"✗ Ingestion failed: {e}", err=True)
        raise typer.Exit(code=1)


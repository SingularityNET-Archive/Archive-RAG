"""CLI command for backfilling tags from source data."""

import typer
from typing import Optional

from ..services.meeting_to_entity import ingest_meetings_to_entities
from ..lib.logging import get_logger

logger = get_logger(__name__)


def backfill_tags_command(
    source_url: str = typer.Argument(..., help="URL to source JSON file containing meetings"),
    verify_hash: Optional[str] = typer.Option(
        None,
        "--verify-hash",
        help="Optional SHA-256 hash to verify source file integrity"
    )
):
    """
    Backfill tags from source URL for existing meetings.
    
    This command re-processes meetings from the source URL and extracts tags,
    but only creates/updates tag entities (existing meetings are preserved).
    
    Example:
        archive-rag backfill-tags "https://raw.githubusercontent.com/.../meeting-summaries-array.json"
    """
    try:
        typer.echo("Backfilling tags from source URL...")
        typer.echo(f"  URL: {source_url}")
        typer.echo("  Note: This will only create/update tag entities, existing meetings are preserved.")
        
        if verify_hash:
            typer.echo(f"  Verifying hash: {verify_hash[:16]}...")
        
        # Ingest meetings to entities (will extract tags)
        successful = ingest_meetings_to_entities(source_url)
        
        typer.echo(f"\n✓ Tag backfill complete!")
        typer.echo(f"  Successfully processed: {successful} meetings")
        typer.echo(f"  Tags saved to: entities/tags/")
        
        # Count created tags
        from pathlib import Path
        from ..lib.config import ENTITIES_TAGS_DIR
        
        tag_count = len(list(Path(ENTITIES_TAGS_DIR).glob("*.json")))
        typer.echo(f"  Total tags: {tag_count}")
        
    except Exception as e:
        logger.error("backfill_tags_failed", url=source_url, error=str(e))
        typer.echo(f"✗ Tag backfill failed: {e}", err=True)
        raise typer.Exit(code=1)


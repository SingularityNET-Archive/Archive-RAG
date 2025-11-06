"""CLI command for ingesting meetings from source URL into entity storage."""

import typer
import json
from pathlib import Path
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
    ),
    output_json: Optional[Path] = typer.Option(
        None,
        "--output-json",
        help="Path to JSON file to save structured entity extraction output"
    )
):
    """
    Ingest meetings from source URL and save to entity storage.
    
    This command:
    - Fetches meeting JSON data from the source URL
    - Converts each meeting to entity models (Meeting, Workgroup, Person)
    - Saves entities to entity storage directories
    - Updates index files for fast lookups
    - Optionally generates and saves structured entity extraction output
    
    Example:
        archive-rag ingest-entities "https://raw.githubusercontent.com/.../meeting-summaries-array.json"
        
    With structured output:
        archive-rag ingest-entities "https://..." --output-json output.json
    """
    try:
        typer.echo(f"Ingesting meetings from source URL...")
        typer.echo(f"  URL: {source_url}")
        
        if verify_hash:
            typer.echo(f"  Verifying hash: {verify_hash[:16]}...")
        
        # Ingest meetings to entities and generate output if requested
        if output_json:
            typer.echo(f"\nIngesting meetings and generating structured output...")
            from ..services.meeting_to_entity import ingest_meetings_to_entities_with_output
            all_outputs = ingest_meetings_to_entities_with_output(source_url)
            
            # Save aggregated output
            with open(output_json, 'w') as f:
                json.dump(all_outputs, f, indent=2, default=str)
            
            typer.echo(f"\n✓ Ingestion complete!")
            typer.echo(f"  Successfully ingested: {len(all_outputs)} meetings")
            typer.echo(f"  Entities saved to: entities/")
            typer.echo(f"\n✓ Structured output saved to: {output_json}")
            typer.echo(f"  Total entities: {sum(len(output.get('structured_entity_list', [])) for output in all_outputs.values())}")
            typer.echo(f"  Total relationship triples: {sum(len(output.get('relationship_triples', [])) for output in all_outputs.values())}")
            typer.echo(f"  Total chunks: {sum(len(output.get('chunks_for_embedding', [])) for output in all_outputs.values())}")
        else:
            # Regular ingestion without output generation
            successful = ingest_meetings_to_entities(source_url)
            
            typer.echo(f"\n✓ Ingestion complete!")
            typer.echo(f"  Successfully ingested: {successful} meetings")
            typer.echo(f"  Entities saved to: entities/")
        
    except Exception as e:
        logger.error("ingest_entities_failed", url=source_url, error=str(e))
        typer.echo(f"✗ Ingestion failed: {e}", err=True)
        raise typer.Exit(code=1)


"""Extract-entities CLI command for extracting named entities from meeting archive."""

from pathlib import Path
from typing import Optional, Set
import typer
import json

from ..services.retrieval import load_index
from ..services.entity_extraction import create_entity_extraction_service
from ..lib.config import DEFAULT_SPACY_MODEL, DEFAULT_MIN_ENTITY_FREQUENCY
from ..services.audit_writer import AuditWriter
from ..lib.logging import get_logger

logger = get_logger(__name__)


def extract_entities_command(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    output_dir: str = typer.Argument(..., help="Directory to write entity extraction results"),
    model: str = typer.Option(
        DEFAULT_SPACY_MODEL,
        "--model",
        help="spaCy model name"
    ),
    entity_types: Optional[str] = typer.Option(
        None,
        "--entity-types",
        help="Comma-separated entity types to extract (default: all)"
    ),
    min_frequency: int = typer.Option(
        DEFAULT_MIN_ENTITY_FREQUENCY,
        "--min-frequency",
        help="Minimum frequency for entity inclusion"
    ),
    no_pii: bool = typer.Option(
        False,
        "--no-pii",
        help="Skip PII detection and redaction"
    )
):
    """
    Extract named entities from meeting archive.
    """
    try:
        # Load index
        index, embedding_index = load_index(index_file)
        
        # Extract documents from metadata
        documents = []
        for chunk_metadata in embedding_index.metadata.values():
            text = chunk_metadata.get("text", "")
            if text:
                documents.append(text)
        
        if not documents:
            typer.echo("No documents found in index.", err=True)
            raise typer.Exit(code=1)
        
        # Parse entity types
        entity_types_set = None
        if entity_types:
            entity_types_set = set([et.strip() for et in entity_types.split(",")])
        
        # Create entity extraction service
        entity_service = create_entity_extraction_service(
            model_name=model,
            entity_types=entity_types_set,
            min_frequency=min_frequency,
            no_pii=no_pii
        )
        
        # Extract entities
        results = entity_service.extract_entities(documents)
        
        # Write results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results_file = output_path / "entities.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Create audit log
        audit_writer = AuditWriter()
        audit_writer.write_index_audit_log(
            operation="extract-entities",
            input_dir=index_file,
            output_index=str(results_file),
            metadata={
                "model": model,
                "entity_types": list(entity_types_set) if entity_types_set else None,
                "min_frequency": min_frequency,
                "num_entities": len(results.get("entities", []))
            }
        )
        
        typer.echo(f"Entity extraction complete: {results_file}")
        typer.echo(f"Entities extracted: {results.get('total_filtered', 0)}")
        typer.echo(f"Documents processed: {len(documents)}")
        
    except Exception as e:
        logger.error("entity_extraction_failed", error=str(e))
        typer.echo(f"Entity extraction failed: {e}", err=True)
        raise typer.Exit(code=1)


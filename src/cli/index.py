"""Index CLI command for ingesting meeting JSON files and creating FAISS index."""

from pathlib import Path
from typing import Optional
import typer

from ..services.ingestion import ingest_meeting_directory
from ..services.chunking import chunk_transcript
from ..services.embedding import create_embedding_service
from ..services.index_builder import build_faiss_index, save_index
from ..services.audit_writer import AuditWriter
from ..lib.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_SEED
)
from ..lib.pii_detection import create_pii_detector
from ..lib.logging import get_logger

logger = get_logger(__name__)


def index_command(
    input_dir: Path = typer.Argument(..., help="Directory containing meeting JSON files"),
    output_index: str = typer.Argument(..., help="Path to output FAISS index file"),
    embedding_model: str = typer.Option(
        DEFAULT_EMBEDDING_MODEL,
        "--embedding-model",
        help="Embedding model name"
    ),
    chunk_size: int = typer.Option(
        DEFAULT_CHUNK_SIZE,
        "--chunk-size",
        help="Chunk size for document splitting"
    ),
    chunk_overlap: int = typer.Option(
        DEFAULT_CHUNK_OVERLAP,
        "--chunk-overlap",
        help="Overlap between chunks"
    ),
    seed: int = typer.Option(
        DEFAULT_SEED,
        "--seed",
        help="Random seed for reproducibility"
    ),
    hash_only: bool = typer.Option(
        False,
        "--hash-only",
        help="Only compute SHA-256 hashes, do not index"
    ),
    verify_hash: Optional[str] = typer.Option(
        None,
        "--verify-hash",
        help="Verify SHA-256 hash of input files"
    ),
    redact_pii: bool = typer.Option(
        True,
        "--redact-pii/--no-redact-pii",
        help="Enable PII detection and redaction"
    )
):
    """
    Ingest meeting JSON files and create FAISS vector index.
    """
    try:
        # Initialize embedding service
        typer.echo("Initializing embedding service...")
        embedding_service = create_embedding_service(model_name=embedding_model)
        typer.echo(f"✓ Embedding service initialized: {embedding_model}")
        
        # Initialize PII detector if needed
        pii_detector = None
        if redact_pii:
            typer.echo("Initializing PII detector...")
            pii_detector = create_pii_detector()
            typer.echo("✓ PII detector initialized")
        
        # Ingest meeting files
        typer.echo(f"Ingesting meeting files from {input_dir}...")
        meeting_records = ingest_meeting_directory(input_dir)
        typer.echo(f"✓ Ingested {len(meeting_records)} meeting files")
        
        if hash_only:
            # Only compute hashes
            typer.echo("Hash computation complete. Use --verify-hash to verify.")
            return
        
        # Chunk transcripts
        typer.echo("Chunking transcripts...", nl=False)
        typer.echo(" ", nl=True)  # Force flush
        all_chunks = []
        for i, (meeting_record, file_hash) in enumerate(meeting_records, 1):
            chunks = chunk_transcript(
                meeting_record,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            all_chunks.extend(chunks)
            typer.echo(f"  ✓ Meeting {i}/{len(meeting_records)}: {meeting_record.id} -> {len(chunks)} chunks", err=False)
        
        typer.echo(f"✓ Created {len(all_chunks)} total chunks from {len(meeting_records)} meetings")
        
        if not all_chunks:
            typer.echo("No chunks created. Check input files.", err=True)
            raise typer.Exit(code=1)
        
        # Build FAISS index
        typer.echo("Generating embeddings (this may take a moment)...")
        index, embedding_index = build_faiss_index(
            all_chunks,
            embedding_service,
            index_type="IndexFlatIP",
            index_name=output_index
        )
        typer.echo("✓ Embeddings generated and index built")
        
        # Save index
        typer.echo(f"Saving index to {output_index}...")
        save_index(index, embedding_index, output_index)
        typer.echo("✓ Index saved")
        
        # Create audit log for indexing operation
        audit_writer = AuditWriter()
        audit_writer.write_index_audit_log(
            operation="index",
            input_dir=str(input_dir),
            output_index=output_index,
            metadata={
                "embedding_model": embedding_model,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "total_meetings": len(meeting_records),
                "total_chunks": len(all_chunks),
                "embedding_dimension": embedding_index.embedding_dimension
            }
        )
        
        typer.echo(f"Index created successfully: {output_index}")
        typer.echo(f"Total meetings indexed: {len(meeting_records)}")
        typer.echo(f"Total chunks: {len(all_chunks)}")
        
    except Exception as e:
        logger.error("indexing_failed", error=str(e))
        typer.echo(f"Indexing failed: {e}", err=True)
        raise typer.Exit(code=1)


"""Main CLI entry point for Archive-RAG."""

import typer
from pathlib import Path
from typing import Optional

from .index import index_command
from .query import query_command

app = typer.Typer(
    name="archive-rag",
    help="Archive Meeting Retrieval & Grounded Interpretation RAG"
)


@app.command()
def index(
    input_dir: Path = typer.Argument(..., help="Directory containing meeting JSON files"),
    output_index: str = typer.Argument(..., help="Path to output FAISS index file"),
    embedding_model: str = typer.Option(
        "sentence-transformers/all-MiniLM-L6-v2",
        "--embedding-model",
        help="Embedding model name"
    ),
    chunk_size: int = typer.Option(512, "--chunk-size", help="Chunk size for document splitting"),
    chunk_overlap: int = typer.Option(50, "--chunk-overlap", help="Overlap between chunks"),
    seed: int = typer.Option(42, "--seed", help="Random seed for reproducibility"),
    hash_only: bool = typer.Option(False, "--hash-only", help="Only compute SHA-256 hashes, do not index"),
    verify_hash: Optional[str] = typer.Option(None, "--verify-hash", help="Verify SHA-256 hash of input files"),
    redact_pii: bool = typer.Option(True, "--redact-pii/--no-redact-pii", help="Enable PII detection and redaction")
):
    """Ingest meeting JSON files and create FAISS vector index."""
    index_command(
        input_dir=input_dir,
        output_index=output_index,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        seed=seed,
        hash_only=hash_only,
        verify_hash=verify_hash,
        redact_pii=redact_pii
    )


@app.command()
def query(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    query_text: str = typer.Argument(..., help="User question string"),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model name"),
    model_version: Optional[str] = typer.Option(None, "--model-version", help="LLM model version"),
    top_k: int = typer.Option(5, "--top-k", help="Number of chunks to retrieve"),
    seed: int = typer.Option(42, "--seed", help="Random seed for deterministic inference"),
    output_format: str = typer.Option("text", "--output-format", help="Output format: text or json"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="SSO user ID")
):
    """Query the RAG system and get evidence-bound answers with citations."""
    query_command(
        index_file=index_file,
        query_text=query_text,
        model=model,
        model_version=model_version,
        top_k=top_k,
        seed=seed,
        output_format=output_format,
        user_id=user_id
    )


@app.command()
def version():
    """Show version information."""
    from .. import __version__
    typer.echo(f"Archive-RAG version {__version__}")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()


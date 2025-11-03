"""Main CLI entry point for Archive-RAG."""

import typer
from pathlib import Path
from typing import Optional

from .index import index_command
from .query import query_command, query_workgroup_command, query_person_command
from .audit_view import audit_view_command
from .topic_model import topic_model_command
from .extract_entities import extract_entities_command
from .evaluate import evaluate_command
from .compliance import check_compliance_command

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
def topic_model(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    output_dir: str = typer.Argument(..., help="Directory to write topic modeling results"),
    num_topics: int = typer.Option(10, "--num-topics", help="Number of topics to discover"),
    method: str = typer.Option("lda", "--method", help="Topic modeling method: lda or bertopic"),
    seed: int = typer.Option(42, "--seed", help="Random seed for reproducibility"),
    no_pii: bool = typer.Option(False, "--no-pii", help="Skip PII detection and redaction")
):
    """Run topic modeling on meeting archive to discover high-level topics."""
    topic_model_command(
        index_file=index_file,
        output_dir=output_dir,
        num_topics=num_topics,
        method=method,
        seed=seed,
        no_pii=no_pii
    )


@app.command()
def extract_entities(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    output_dir: str = typer.Argument(..., help="Directory to write entity extraction results"),
    model: str = typer.Option("en_core_web_sm", "--model", help="spaCy model name"),
    entity_types: Optional[str] = typer.Option(None, "--entity-types", help="Comma-separated entity types to extract"),
    min_frequency: int = typer.Option(2, "--min-frequency", help="Minimum frequency for entity inclusion"),
    no_pii: bool = typer.Option(False, "--no-pii", help="Skip PII detection and redaction")
):
    """Extract named entities from meeting archive."""
    extract_entities_command(
        index_file=index_file,
        output_dir=output_dir,
        model=model,
        entity_types=entity_types,
        min_frequency=min_frequency,
        no_pii=no_pii
    )


@app.command()
def evaluate(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    benchmark_file: str = typer.Argument(..., help="Path to evaluation benchmark JSON file"),
    output_dir: str = typer.Argument(..., help="Directory to write evaluation results"),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model name"),
    model_version: Optional[str] = typer.Option(None, "--model-version", help="LLM model version"),
    seed: int = typer.Option(42, "--seed", help="Random seed for reproducibility"),
    output_format: str = typer.Option("report", "--output-format", help="Results format: json or report")
):
    """Run evaluation suite to measure factuality and citation compliance."""
    evaluate_command(
        index_file=index_file,
        benchmark_file=benchmark_file,
        output_dir=output_dir,
        model=model,
        model_version=model_version,
        seed=seed,
        output_format=output_format
    )


@app.command()
def query_workgroup(
    workgroup_id: str = typer.Argument(..., help="Workgroup ID (UUID)"),
    output_format: str = typer.Option("text", "--output-format", help="Output format: text or json")
):
    """Query all meetings for a specific workgroup using entity-based data model."""
    query_workgroup_command(workgroup_id=workgroup_id, output_format=output_format)


@app.command()
def query_person(
    person_id: str = typer.Argument(..., help="Person ID (UUID)"),
    action_items: bool = typer.Option(False, "--action-items", help="Query action items assigned to this person"),
    output_format: str = typer.Option("text", "--output-format", help="Output format: text or json")
):
    """Query information for a specific person, optionally including action items."""
    query_person_command(person_id=person_id, action_items=action_items, output_format=output_format)


@app.command()
def audit_view(
    log_file: Optional[Path] = typer.Argument(None, help="Path to specific audit log file"),
    query_id: Optional[str] = typer.Option(None, "--query-id", help="Filter by query ID"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="Filter by user ID"),
    date_from: Optional[str] = typer.Option(None, "--date-from", help="Filter logs from date (ISO 8601)"),
    date_to: Optional[str] = typer.Option(None, "--date-to", help="Filter logs to date (ISO 8601)"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    export: Optional[Path] = typer.Option(None, "--export", help="Export filtered logs to file")
):
    """View and analyze audit logs."""
    audit_view_command(
        log_file=log_file,
        query_id=query_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        output_format=output_format,
        export=export
    )


@app.command()
def check_compliance(
    static: bool = typer.Option(True, "--static/--no-static", help="Run static analysis checks"),
    runtime: bool = typer.Option(False, "--runtime/--no-runtime", help="Run runtime checks"),
    tests: bool = typer.Option(True, "--tests/--no-tests", help="Run compliance tests"),
    output_format: str = typer.Option("text", "--output-format", help="Output format: json, text, or markdown"),
    report_file: Optional[Path] = typer.Option(None, "--report-file", help="Write report to file")
):
    """Check constitution compliance for entity data model implementation."""
    check_compliance_command(
        static=static,
        runtime=runtime,
        tests=tests,
        output_format=output_format,
        report_file=report_file
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


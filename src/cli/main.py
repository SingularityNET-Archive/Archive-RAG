"""Main CLI entry point for Archive-RAG."""

import typer
from pathlib import Path
from typing import Optional

from .index import index_command
from .query import query_command, query_workgroup_command, query_person_command, query_meeting_command, query_decisions_command
from .audit_view import audit_view_command
from .topic_model import topic_model_command
from .extract_entities import extract_entities_command
from .evaluate import evaluate_command
from .compliance import check_compliance_command
from .ingest_entities import ingest_entities_command
from .backfill_tags import backfill_tags_command
from .bot import bot_command
from .test_entity_extraction import test_entity_extraction_command
from .test_semantic_chunking import test_semantic_chunking_command
from .test_discord_bot_enhancements import app as test_discord_bot_app
from .web import web_command

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
    redact_pii: bool = typer.Option(True, "--redact-pii/--no-redact-pii", help="Enable PII detection and redaction"),
    semantic: bool = typer.Option(False, "--semantic/--no-semantic", help="Use semantic chunking (includes chunk_type, entities, relationships)")
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
        redact_pii=redact_pii,
        semantic=semantic
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
def query_meeting(
    meeting_id: str = typer.Argument(..., help="Meeting ID (UUID)"),
    documents: bool = typer.Option(False, "--documents", help="Query documents linked to this meeting"),
    decisions: bool = typer.Option(False, "--decisions", help="Query decisions made in this meeting"),
    output_format: str = typer.Option("text", "--output-format", help="Output format: text or json")
):
    """Query information for a specific meeting, optionally including linked documents and decisions."""
    query_meeting_command(meeting_id=meeting_id, documents=documents, decisions=decisions, output_format=output_format)


@app.command()
def query_person(
    person_id: str = typer.Argument(..., help="Person ID (UUID)"),
    action_items: bool = typer.Option(False, "--action-items", help="Query action items assigned to this person"),
    output_format: str = typer.Option("text", "--output-format", help="Output format: text or json")
):
    """Query information for a specific person, optionally including action items."""
    query_person_command(person_id=person_id, action_items=action_items, output_format=output_format)


@app.command()
def query_decisions(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    query_text: str = typer.Argument(..., help="Free text query for decisions"),
    top_k: int = typer.Option(5, "--top-k", help="Number of decisions to retrieve"),
    min_score: float = typer.Option(0.0, "--min-score", help="Minimum relevance score threshold (0.0 to 1.0)"),
    output_format: str = typer.Option("text", "--output-format", help="Output format: text or json"),
    include_rationale: bool = typer.Option(True, "--include-rationale/--no-rationale", help="Include decision rationale in output"),
    include_effect: bool = typer.Option(True, "--include-effect/--no-effect", help="Include decision effect scope in output"),
    include_score: bool = typer.Option(False, "--include-score/--no-score", help="Include relevance score in output")
):
    """Query meeting decisions using free text search via RAG index."""
    query_decisions_command(
        index_file=index_file,
        query_text=query_text,
        top_k=top_k,
        min_score=min_score,
        output_format=output_format,
        include_rationale=include_rationale,
        include_effect=include_effect,
        include_score=include_score
    )


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
def ingest_entities(
    source_url: str = typer.Argument(..., help="URL to source JSON file containing meetings"),
    verify_hash: Optional[str] = typer.Option(None, "--verify-hash", help="Optional SHA-256 hash to verify source file integrity"),
    output_json: Optional[Path] = typer.Option(None, "--output-json", help="Path to JSON file to save structured entity extraction output")
):
    """Ingest meetings from source URL and save to entity storage."""
    ingest_entities_command(source_url=source_url, verify_hash=verify_hash, output_json=output_json)


@app.command()
def backfill_tags(
    source_url: str = typer.Argument(..., help="URL to source JSON file containing meetings"),
    verify_hash: Optional[str] = typer.Option(None, "--verify-hash", help="Optional SHA-256 hash to verify source file integrity")
):
    """Backfill tags from source URL for existing meetings."""
    backfill_tags_command(source_url=source_url, verify_hash=verify_hash)


@app.command()
def bot(
    token: Optional[str] = typer.Option(
        None,
        "--token",
        help="Discord bot token (overrides DISCORD_BOT_TOKEN env var)"
    ),
    index_name: Optional[str] = typer.Option(
        None,
        "--index-name",
        help="RAG index name (overrides INDEX_NAME env var)"
    )
):
    """Start the Discord bot for Archive-RAG."""
    bot_command(token=token, index_name=index_name)


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development")
):
    """Start the web server for Archive-RAG."""
    web_command(host=host, port=port, reload=reload)


@app.command()
def test_entity_extraction(
    source_url: str = typer.Argument(..., help="URL to source JSON file containing meetings"),
    phases: Optional[str] = typer.Option(
        None,
        "--phases",
        help="Comma-separated list of phases to test (e.g., 'US1,US2,US3' or 'all')"
    ),
    meeting_index: Optional[int] = typer.Option(
        None,
        "--meeting-index",
        help="Index of single meeting to test (0-based). Mutually exclusive with --random and --index-range"
    ),
    random: Optional[int] = typer.Option(
        None,
        "--random",
        help="Test N random meetings. Mutually exclusive with --meeting-index and --index-range"
    ),
    index_range: Optional[str] = typer.Option(
        None,
        "--index-range",
        help="Test meetings in index range (e.g., '0:5' or '10:20'). Mutually exclusive with --meeting-index and --random"
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Path to JSON file to save test results"
    ),
    verify_hash: Optional[str] = typer.Option(
        None,
        "--verify-hash",
        help="Optional SHA-256 hash to verify source file integrity"
    )
):
    """Test entity extraction implementation phases."""
    test_entity_extraction_command(
        source_url=source_url,
        phases=phases,
        meeting_index=meeting_index,
        random=random,
        index_range=index_range,
        output_file=output_file,
        verify_hash=verify_hash
    )


@app.command()
def version():
    """Show version information."""
    from .. import __version__
    typer.echo(f"Archive-RAG version {__version__}")


app.add_typer(test_discord_bot_app, name="test-discord-bot", help="Test Discord bot enhancements")


@app.command()
def test_semantic_chunking(
    source_url: str = typer.Argument(..., help="URL to source JSON file containing meetings"),
    queries: Optional[str] = typer.Option(
        None,
        "--queries",
        help="Comma-separated list of queries to test (default: built-in test queries)"
    ),
    top_k: int = typer.Option(
        5,
        "--top-k",
        help="Number of chunks to retrieve per query"
    ),
    embedding_model: str = typer.Option(
        "sentence-transformers/all-MiniLM-L6-v2",
        "--embedding-model",
        help="Embedding model name"
    ),
    chunk_size: int = typer.Option(
        512,
        "--chunk-size",
        help="Chunk size for token-based chunking"
    ),
    chunk_overlap: int = typer.Option(
        50,
        "--chunk-overlap",
        help="Overlap for token-based chunking"
    ),
    meeting_limit: Optional[int] = typer.Option(
        None,
        "--meeting-limit",
        help="Limit number of meetings to process (for faster testing)"
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Directory to save index files (default: ./test_indices)"
    )
):
    """Test semantic chunking vs token-based chunking on queries."""
    test_semantic_chunking_command(
        source_url=source_url,
        queries=queries,
        top_k=top_k,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        meeting_limit=meeting_limit,
        output_dir=output_dir
    )


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()


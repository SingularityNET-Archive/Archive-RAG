"""Topic-model CLI command for discovering topics in meeting archive."""

from pathlib import Path
from typing import Optional
import typer
import json

from ..services.retrieval import load_index
from ..services.topic_modeling import create_topic_modeling_service
from ..services.topic_modeling_bertopic import create_bertopic_modeling_service
from ..lib.config import DEFAULT_NUM_TOPICS, DEFAULT_TOPIC_METHOD, DEFAULT_SEED
from ..services.audit_writer import AuditWriter
from ..lib.logging import get_logger

logger = get_logger(__name__)


def topic_model_command(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    output_dir: str = typer.Argument(..., help="Directory to write topic modeling results"),
    num_topics: int = typer.Option(
        DEFAULT_NUM_TOPICS,
        "--num-topics",
        help="Number of topics to discover"
    ),
    method: str = typer.Option(
        DEFAULT_TOPIC_METHOD,
        "--method",
        help="Topic modeling method: lda or bertopic"
    ),
    seed: int = typer.Option(
        DEFAULT_SEED,
        "--seed",
        help="Random seed for reproducibility"
    ),
    no_pii: bool = typer.Option(
        False,
        "--no-pii",
        help="Skip PII detection and redaction"
    )
):
    """
    Run topic modeling on meeting archive to discover high-level topics.
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
        
        # Create topic modeling service
        if method == "bertopic":
            topic_service = create_bertopic_modeling_service(
                num_topics=num_topics,
                seed=seed,
                no_pii=no_pii
            )
        else:
            topic_service = create_topic_modeling_service(
                num_topics=num_topics,
                method=method,
                seed=seed,
                no_pii=no_pii
            )
        
        # Extract topics
        results = topic_service.extract_topics(documents)
        
        # Write results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results_file = output_path / "topics.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Create audit log
        audit_writer = AuditWriter()
        audit_writer.write_index_audit_log(
            operation="topic-model",
            input_dir=index_file,
            output_index=str(results_file),
            metadata={
                "num_topics": num_topics,
                "method": method,
                "num_documents": len(documents)
            }
        )
        
        typer.echo(f"Topic modeling complete: {results_file}")
        typer.echo(f"Topics discovered: {num_topics}")
        typer.echo(f"Documents processed: {len(documents)}")
        
    except Exception as e:
        logger.error("topic_modeling_failed", error=str(e))
        typer.echo(f"Topic modeling failed: {e}", err=True)
        raise typer.Exit(code=1)


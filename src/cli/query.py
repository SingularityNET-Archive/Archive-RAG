"""Query CLI command for querying the RAG system."""

from pathlib import Path
from typing import Optional
import typer
import uuid
from datetime import datetime

from ..services.query_service import create_query_service
from ..services.citation_extractor import format_citations_as_text
from ..lib.config import DEFAULT_TOP_K, DEFAULT_SEED
from ..lib.auth import get_user_id
from ..lib.logging import get_logger

logger = get_logger(__name__)


def query_command(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    query_text: str = typer.Argument(..., help="User question string"),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="LLM model name"
    ),
    model_version: Optional[str] = typer.Option(
        None,
        "--model-version",
        help="LLM model version"
    ),
    top_k: int = typer.Option(
        DEFAULT_TOP_K,
        "--top-k",
        help="Number of chunks to retrieve"
    ),
    seed: int = typer.Option(
        DEFAULT_SEED,
        "--seed",
        help="Random seed for deterministic inference"
    ),
    output_format: str = typer.Option(
        "text",
        "--output-format",
        help="Output format: text or json"
    ),
    user_id: Optional[str] = typer.Option(
        None,
        "--user-id",
        help="SSO user ID"
    )
):
    """
    Query the RAG system and get evidence-bound answers with citations.
    """
    try:
        # Get user ID (from CLI flag or SSO context)
        resolved_user_id = get_user_id(user_id)
        
        # Create query service
        query_service = create_query_service(model_name=model, seed=seed)
        
        # Execute query (automatically creates audit log)
        rag_query = query_service.execute_query(
            index_name=index_file,
            query_text=query_text,
            top_k=top_k,
            user_id=resolved_user_id,
            model_version=model_version
        )
        
        # Format output
        if output_format == "json":
            import json
            typer.echo(json.dumps(rag_query.to_dict(), indent=2))
        else:
            # Text format
            typer.echo(f"Answer: {answer}")
            typer.echo("\nCitations:")
            citation_text = format_citations_as_text(citations)
            typer.echo(citation_text)
            if not evidence_found:
                typer.echo("\nNote: No credible evidence found in meeting records.")
        
    except Exception as e:
        logger.error("query_failed", error=str(e))
        typer.echo(f"Query failed: {e}", err=True)
        raise typer.Exit(code=1)


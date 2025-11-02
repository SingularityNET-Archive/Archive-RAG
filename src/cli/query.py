"""Query CLI command for querying the RAG system."""

from pathlib import Path
from typing import Optional
import typer
import uuid
from datetime import datetime

from ..services.retrieval import query_index, load_index
from ..services.embedding import create_embedding_service
from ..services.rag_generator import create_rag_generator
from ..services.citation_extractor import extract_citations, format_citations_as_text
from ..services.evidence_checker import check_evidence, get_no_evidence_message
from ..models.rag_query import RAGQuery, RetrievedChunk, Citation
from ..lib.config import DEFAULT_TOP_K, DEFAULT_SEED
from ..lib.audit import write_audit_log
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
        # Generate query ID
        query_id = str(uuid.uuid4())
        
        # Load index
        index, embedding_index = load_index(index_file)
        
        # Create embedding service
        embedding_service = create_embedding_service(
            model_name=embedding_index.embedding_model
        )
        
        # Query index
        retrieved_chunks = query_index(
            query_text,
            embedding_service,
            index_file,
            top_k=top_k
        )
        
        # Check evidence
        evidence_found = check_evidence(retrieved_chunks)
        
        # Generate answer
        rag_generator = create_rag_generator(
            model_name=model,
            seed=seed
        )
        
        if evidence_found:
            answer = rag_generator.generate(query_text, retrieved_chunks)
        else:
            answer = get_no_evidence_message()
        
        # Extract citations
        citations = extract_citations(retrieved_chunks)
        
        # Create RAGQuery model
        rag_query = RAGQuery(
            query_id=query_id,
            user_input=query_text,
            timestamp=datetime.utcnow().isoformat() + "Z",
            retrieved_chunks=[
                RetrievedChunk(**chunk) for chunk in retrieved_chunks
            ],
            output=answer,
            citations=citations,
            model_version=model_version or rag_generator.model_name,
            embedding_version=embedding_index.embedding_model,
            user_id=user_id,
            evidence_found=evidence_found,
            audit_log_path=f"audit_logs/query-{query_id}.json"
        )
        
        # Create audit log
        audit_data = rag_query.to_dict()
        audit_log_path = write_audit_log(query_id, audit_data)
        
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


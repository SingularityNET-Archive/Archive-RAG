"""CLI command to test semantic chunking vs token-based chunking on queries."""

from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID
import json
import typer
from datetime import datetime

from ..services.ingestion import ingest_meeting_directory
from ..services.chunking import chunk_transcript, chunk_by_semantic_unit
from ..services.meeting_to_entity import convert_and_save_meeting_record
from ..services.embedding import create_embedding_service
from ..services.index_builder import build_faiss_index, save_index
from ..services.retrieval import query_index
from ..models.meeting_record import MeetingRecord
from ..models.chunk_metadata import ChunkMetadata
from ..services.chunking import DocumentChunk
from ..lib.logging import get_logger

logger = get_logger(__name__)


def _convert_chunk_metadata_to_document_chunk(chunk: ChunkMetadata, meeting_id: str) -> DocumentChunk:
    """Convert ChunkMetadata to DocumentChunk for indexing."""
    # Extract metadata from ChunkMetadata
    metadata = {
        "meeting_id": meeting_id,
        "chunk_type": chunk.metadata.chunk_type,
        "source_field": chunk.metadata.source_field,
        "entities": [
            {
                "entity_id": str(e.entity_id),
                "entity_type": e.entity_type,
                "normalized_name": e.normalized_name,
                "mentions": e.mentions
            }
            for e in chunk.entities
        ],
        "relationships": [
            {
                "subject": r.subject,
                "relationship": r.relationship,
                "object": r.object
            }
            for r in chunk.metadata.relationships
        ],
        "chunk_index": chunk.metadata.chunk_index or 0,
        "total_chunks": chunk.metadata.total_chunks or 1,
    }
    
    return DocumentChunk(
        text=chunk.text,
        chunk_index=chunk.metadata.chunk_index or 0,
        meeting_id=meeting_id,
        start_idx=0,
        end_idx=len(chunk.text),
        metadata=metadata
    )


def _index_with_semantic_chunking(
    meeting_records: List[tuple[MeetingRecord, str]],
    embedding_service,
    output_index: str
) -> tuple[Any, Any]:
    """Index meetings using semantic chunking."""
    typer.echo("Indexing with semantic chunking...")
    all_chunks = []
    
    for i, (meeting_record, file_hash) in enumerate(meeting_records, 1):
        # Extract and save entities first
        meeting_entity = convert_and_save_meeting_record(meeting_record)
        meeting_id = str(meeting_entity.id)
        
        # Create semantic chunks
        semantic_chunks = chunk_by_semantic_unit(
            meeting_record=meeting_record,
            meeting_id=meeting_entity.id,
        )
        
        # Convert ChunkMetadata to DocumentChunk for indexing
        for chunk in semantic_chunks:
            doc_chunk = _convert_chunk_metadata_to_document_chunk(chunk, meeting_id)
            all_chunks.append(doc_chunk)
        
        typer.echo(f"  ✓ Meeting {i}/{len(meeting_records)}: {len(semantic_chunks)} semantic chunks")
    
    typer.echo(f"✓ Created {len(all_chunks)} semantic chunks total")
    
    # Build index
    index, embedding_index = build_faiss_index(
        all_chunks,
        embedding_service,
        index_type="IndexFlatIP",
        index_name=output_index
    )
    
    # Save index
    save_index(index, embedding_index, output_index)
    
    return index, embedding_index


def _index_with_token_chunking(
    meeting_records: List[tuple[MeetingRecord, str]],
    embedding_service,
    output_index: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> tuple[Any, Any]:
    """Index meetings using token-based chunking."""
    typer.echo("Indexing with token-based chunking...")
    all_chunks = []
    
    for i, (meeting_record, file_hash) in enumerate(meeting_records, 1):
        chunks = chunk_transcript(
            meeting_record,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        all_chunks.extend(chunks)
        typer.echo(f"  ✓ Meeting {i}/{len(meeting_records)}: {len(chunks)} token chunks")
    
    typer.echo(f"✓ Created {len(all_chunks)} token chunks total")
    
    # Build index
    index, embedding_index = build_faiss_index(
        all_chunks,
        embedding_service,
        index_type="IndexFlatIP",
        index_name=output_index
    )
    
    # Save index
    save_index(index, embedding_index, output_index)
    
    return index, embedding_index


def _query_and_display(
    query_text: str,
    index_name: str,
    embedding_service,
    top_k: int = 5,
    chunk_type_label: str = "chunks"
) -> List[Dict[str, Any]]:
    """Query index and display results."""
    typer.echo(f"\n  Query: '{query_text}'")
    typer.echo(f"  Retrieving top {top_k} {chunk_type_label}...")
    
    retrieved_chunks = query_index(
        query_text=query_text,
        embedding_service=embedding_service,
        index_name=index_name,
        top_k=top_k
    )
    
    typer.echo(f"  Retrieved {len(retrieved_chunks)} chunks:")
    
    for i, chunk in enumerate(retrieved_chunks, 1):
        score = chunk.get("score", 0.0)
        text = chunk.get("text", "")[:100] + "..." if len(chunk.get("text", "")) > 100 else chunk.get("text", "")
        metadata = chunk.get("metadata", {})
        
        typer.echo(f"\n    [{i}] Score: {score:.4f}")
        typer.echo(f"        Text: {text}")
        typer.echo(f"        Meeting ID: {chunk.get('meeting_id', 'unknown')}")
        
        # Display semantic chunk metadata if available
        if "chunk_type" in metadata:
            typer.echo(f"        Chunk Type: {metadata['chunk_type']}")
            typer.echo(f"        Source Field: {metadata.get('source_field', 'unknown')}")
        
        if "entities" in metadata and metadata["entities"]:
            entity_count = len(metadata["entities"])
            typer.echo(f"        Entities: {entity_count} entity(ies) mentioned")
            # Show first few entities
            for entity in metadata["entities"][:3]:
                typer.echo(f"          - {entity.get('normalized_name', 'unknown')} ({entity.get('entity_type', 'unknown')})")
            if entity_count > 3:
                typer.echo(f"          ... and {entity_count - 3} more")
        
        if "relationships" in metadata and metadata["relationships"]:
            rel_count = len(metadata["relationships"])
            typer.echo(f"        Relationships: {rel_count} relationship(s)")
            for rel in metadata["relationships"][:2]:
                typer.echo(f"          - {rel.get('subject', '?')} -> {rel.get('relationship', '?')} -> {rel.get('object', '?')}")
            if rel_count > 2:
                typer.echo(f"          ... and {rel_count - 2} more")
    
    return retrieved_chunks


def test_semantic_chunking_command(
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
    """
    Test semantic chunking vs token-based chunking on queries.
    
    This command:
    1. Indexes meetings using both semantic and token-based chunking
    2. Runs test queries on both indices
    3. Compares results showing entity metadata and relationships
    """
    typer.echo("=" * 70)
    typer.echo("Semantic Chunking Query Test")
    typer.echo("=" * 70)
    
    # Default test queries
    default_queries = [
        "What decisions were made?",
        "Who attended the meetings?",
        "What action items were assigned?",
        "What workgroups are involved?",
        "What documents were discussed?",
    ]
    
    # Parse queries
    if queries:
        test_queries = [q.strip() for q in queries.split(",")]
    else:
        test_queries = default_queries
    
    # Set output directory
    if output_dir is None:
        output_dir = Path("./test_indices")
    output_dir.mkdir(exist_ok=True)
    
    semantic_index_path = str(output_dir / "semantic_index")
    token_index_path = str(output_dir / "token_index")
    
    # Initialize embedding service
    typer.echo("\nInitializing embedding service...")
    embedding_service = create_embedding_service(model_name=embedding_model)
    typer.echo(f"✓ Embedding service initialized: {embedding_model}")
    
    # Validate source URL/path
    if not source_url or source_url.strip() == "":
        typer.echo("Error: source_url cannot be empty", err=True)
        raise typer.Exit(code=1)
    
    # Check for placeholder URLs
    placeholder_urls = ["https://example.com", "http://example.com", "example.com"]
    if any(placeholder in source_url.lower() for placeholder in placeholder_urls):
        typer.echo("Error: Please provide a valid URL or path to your meetings JSON file.", err=True)
        typer.echo(f"  The URL '{source_url}' appears to be a placeholder.", err=True)
        typer.echo("  Example: archive-rag test-semantic-chunking <your-actual-url>", err=True)
        raise typer.Exit(code=1)
    
    # Ingest meetings
    typer.echo(f"\nIngesting meetings from {source_url}...")
    try:
        meeting_records = ingest_meeting_directory(source_url)
    except ValueError as e:
        typer.echo(f"Error: Failed to ingest meetings from {source_url}", err=True)
        typer.echo(f"  {str(e)}", err=True)
        typer.echo("\nPlease ensure:", err=True)
        typer.echo("  - The URL is accessible and returns valid JSON", err=True)
        typer.echo("  - The URL points to a JSON file containing meeting records", err=True)
        typer.echo("  - For local files, use the full path (e.g., /path/to/meetings.json)", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: Unexpected error while ingesting meetings", err=True)
        typer.echo(f"  {str(e)}", err=True)
        raise typer.Exit(code=1)
    
    if meeting_limit:
        meeting_records = meeting_records[:meeting_limit]
        typer.echo(f"  Limited to {meeting_limit} meetings for testing")
    
    typer.echo(f"✓ Ingested {len(meeting_records)} meeting records")
    
    if not meeting_records:
        typer.echo("No meetings found. Exiting.", err=True)
        typer.echo("  Please check that the source contains valid meeting records.", err=True)
        raise typer.Exit(code=1)
    
    # Index with semantic chunking
    typer.echo("\n" + "=" * 70)
    typer.echo("Step 1: Indexing with Semantic Chunking")
    typer.echo("=" * 70)
    semantic_index, semantic_embedding_index = _index_with_semantic_chunking(
        meeting_records,
        embedding_service,
        semantic_index_path
    )
    typer.echo(f"✓ Semantic index saved to {semantic_index_path}")
    
    # Index with token-based chunking
    typer.echo("\n" + "=" * 70)
    typer.echo("Step 2: Indexing with Token-Based Chunking")
    typer.echo("=" * 70)
    token_index, token_embedding_index = _index_with_token_chunking(
        meeting_records,
        embedding_service,
        token_index_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    typer.echo(f"✓ Token-based index saved to {token_index_path}")
    
    # Run queries and compare
    typer.echo("\n" + "=" * 70)
    typer.echo("Step 3: Running Test Queries")
    typer.echo("=" * 70)
    
    all_results = {
        "semantic": {},
        "token": {},
        "comparison": {}
    }
    
    for query_text in test_queries:
        typer.echo("\n" + "-" * 70)
        typer.echo(f"Query: {query_text}")
        typer.echo("-" * 70)
        
        # Query semantic index
        typer.echo("\n[Semantic Chunking Results]")
        semantic_results = _query_and_display(
            query_text,
            semantic_index_path,
            embedding_service,
            top_k=top_k,
            chunk_type_label="semantic chunks"
        )
        all_results["semantic"][query_text] = semantic_results
        
        # Query token index
        typer.echo("\n[Token-Based Chunking Results]")
        token_results = _query_and_display(
            query_text,
            token_index_path,
            embedding_service,
            top_k=top_k,
            chunk_type_label="token chunks"
        )
        all_results["token"][query_text] = token_results
        
        # Compare results
        typer.echo("\n[Comparison]")
        semantic_scores = [r.get("score", 0.0) for r in semantic_results]
        token_scores = [r.get("score", 0.0) for r in token_results]
        
        avg_semantic = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0
        avg_token = sum(token_scores) / len(token_scores) if token_scores else 0
        
        typer.echo(f"  Average semantic chunk score: {avg_semantic:.4f}")
        typer.echo(f"  Average token chunk score: {avg_token:.4f}")
        typer.echo(f"  Difference: {avg_semantic - avg_token:+.4f}")
        
        # Check for entity metadata in semantic chunks
        semantic_with_entities = sum(
            1 for r in semantic_results 
            if r.get("metadata", {}).get("entities")
        )
        typer.echo(f"  Semantic chunks with entities: {semantic_with_entities}/{len(semantic_results)}")
    
    # Summary
    typer.echo("\n" + "=" * 70)
    typer.echo("Summary")
    typer.echo("=" * 70)
    typer.echo(f"Total meetings indexed: {len(meeting_records)}")
    typer.echo(f"Semantic chunks: {semantic_embedding_index.total_documents}")
    typer.echo(f"Token chunks: {token_embedding_index.total_documents}")
    typer.echo(f"Queries tested: {len(test_queries)}")
    typer.echo(f"\nIndex files:")
    typer.echo(f"  Semantic: {semantic_index_path}.faiss")
    typer.echo(f"  Token: {token_index_path}.faiss")
    
    typer.echo("\n✓ Test complete!")


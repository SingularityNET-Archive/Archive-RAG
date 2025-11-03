"""Query CLI command for querying the RAG system."""

from pathlib import Path
from typing import Optional
import typer
import uuid
from datetime import datetime
from uuid import UUID

from ..services.query_service import create_query_service
from ..services.citation_extractor import format_citations_as_text
from ..services.entity_query import EntityQueryService
from ..services.decision_query import query_decisions_by_text, format_decision_results
from ..lib.config import DEFAULT_TOP_K, DEFAULT_SEED, ENTITIES_TAGS_DIR
from ..lib.auth import get_user_id
from ..lib.logging import get_logger
from ..services.compliance_checker import ComplianceChecker

logger = get_logger(__name__)

def _get_cli_compliance_checker():
    """Get singleton compliance checker instance for CLI operations (T055 - US4)."""
    from ..services.compliance_checker import get_compliance_checker
    checker = get_compliance_checker()
    # Ensure monitoring is enabled for CLI operations
    if not checker.enabled:
        checker.enable_monitoring()
    return checker


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
        # Check compliance for CLI command execution (T055 - US4)
        checker = _get_cli_compliance_checker()
        violations = checker.check_entity_operations()
        violations.extend(checker.check_faiss_operations())
        if violations:
            logger.error("cli_command_compliance_violation", violations=[str(v) for v in violations])
            typer.echo(f"Compliance violation detected: {violations[0]}", err=True)
            raise typer.Exit(code=1)
        
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
            typer.echo(f"Answer: {rag_query.output}")
            typer.echo("\nCitations:")
            citation_text = format_citations_as_text(rag_query.citations)
            typer.echo(citation_text)
            if not rag_query.evidence_found:
                typer.echo("\nNote: No credible evidence found in meeting records.")
        
    except Exception as e:
        logger.error("query_failed", error=str(e))
        typer.echo(f"Query failed: {e}", err=True)
        raise typer.Exit(code=1)


def query_workgroup_command(
    workgroup_id: str = typer.Argument(..., help="Workgroup ID (UUID)"),
    output_format: str = typer.Option(
        "text",
        "--output-format",
        help="Output format: text or json"
    )
):
    """
    Query all meetings for a specific workgroup.
    
    Uses the entity-based data model to retrieve all meetings associated
    with the specified workgroup using the meetings_by_workgroup index.
    """
    try:
        # Parse workgroup_id as UUID
        try:
            workgroup_uuid = UUID(workgroup_id)
        except ValueError:
            typer.echo(f"Invalid workgroup ID format: {workgroup_id}. Expected UUID.", err=True)
            raise typer.Exit(code=1)
        
        # Create query service
        query_service = EntityQueryService()
        
        # Get meetings by workgroup
        meetings = query_service.get_meetings_by_workgroup(workgroup_uuid)
        
        # Format output
        if output_format == "json":
            import json
            meetings_data = [meeting.model_dump(mode="json") for meeting in meetings]
            typer.echo(json.dumps({"workgroup_id": str(workgroup_uuid), "meetings": meetings_data, "count": len(meetings)}, indent=2))
        else:
            # Text format
            typer.echo(f"Workgroup ID: {workgroup_id}")
            typer.echo(f"Found {len(meetings)} meeting(s)")
            typer.echo("\nMeetings:")
            for meeting in meetings:
                typer.echo(f"  - Meeting {meeting.id}")
                typer.echo(f"    Date: {meeting.date}")
                typer.echo(f"    Type: {meeting.meeting_type or 'N/A'}")
                typer.echo(f"    Purpose: {meeting.purpose or 'N/A'}")
        
        logger.info("query_workgroup_success", workgroup_id=str(workgroup_uuid), meeting_count=len(meetings))
        
    except Exception as e:
        logger.error("query_workgroup_failed", error=str(e), workgroup_id=workgroup_id)
        typer.echo(f"Query workgroup failed: {e}", err=True)
        raise typer.Exit(code=1)


def query_meeting_command(
        meeting_id: str = typer.Argument(..., help="Meeting ID (UUID)"),
        documents: bool = typer.Option(
            False,
            "--documents",
            help="Query documents linked to this meeting"
        ),
        decisions: bool = typer.Option(
            False,
            "--decisions",
            help="Query decisions made in this meeting"
        ),
        tags: bool = typer.Option(
            False,
            "--tags",
            help="Query tags for this meeting"
        ),
        output_format: str = typer.Option(
            "text",
            "--output-format",
            help="Output format: text or json"
        )
    ):
        """
        Query information for a specific meeting.
        
        Uses the entity-based data model to retrieve meeting information,
        optionally linked documents, and decisions made in the meeting.
        """
        try:
            # Parse meeting_id as UUID
            try:
                meeting_uuid = UUID(meeting_id)
            except ValueError:
                typer.echo(f"Invalid meeting ID format: {meeting_id}. Expected UUID.", err=True)
                raise typer.Exit(code=1)
            
            # Create query service
            query_service = EntityQueryService()
            
            if documents:
                # Query documents for meeting (with link validation on access)
                documents_list = query_service.get_documents_by_meeting_with_validation(meeting_uuid)
                
                if output_format == "json":
                    import json
                    documents_data = [doc.model_dump(mode="json") for doc in documents_list]
                    typer.echo(json.dumps({"meeting_id": str(meeting_uuid), "documents": documents_data, "count": len(documents_list)}, indent=2))
                else:
                    # Text format
                    typer.echo(f"Meeting ID: {meeting_id}")
                    typer.echo(f"Found {len(documents_list)} document(s)")
                    typer.echo("\nDocuments:")
                    for document in documents_list:
                        typer.echo(f"  - {document.title}")
                        typer.echo(f"    Link: {document.link}")
                        typer.echo(f"    ID: {document.id}")
                        typer.echo(f"    Created: {document.created_at}")
                
                logger.info("query_meeting_documents_success", meeting_id=str(meeting_uuid), document_count=len(documents_list))
            elif decisions:
                # Query decisions for meeting
                decisions_list = query_service.get_decision_items_by_meeting(meeting_uuid)
                
                if output_format == "json":
                    import json
                    decisions_data = [decision.model_dump(mode="json") for decision in decisions_list]
                    typer.echo(json.dumps({"meeting_id": str(meeting_uuid), "decisions": decisions_data, "count": len(decisions_list)}, indent=2))
                else:
                    # Text format
                    typer.echo(f"Meeting ID: {meeting_id}")
                    typer.echo(f"Found {len(decisions_list)} decision(s)")
                    typer.echo("\nDecisions:")
                    for decision in decisions_list:
                        typer.echo(f"  - {decision.decision}")
                        if decision.rationale:
                            typer.echo(f"    Rationale: {decision.rationale}")
                        if decision.effect:
                            typer.echo(f"    Effect: {decision.effect.value}")
                        typer.echo(f"    Created: {decision.created_at}")
                
                logger.info("query_meeting_decisions_success", meeting_id=str(meeting_uuid), decision_count=len(decisions_list))
            elif tags:
                # Query tags for meeting
                # First, get all tags for this meeting
                tags_list = []
                for tag_file in ENTITIES_TAGS_DIR.glob("*.json"):
                    try:
                        tag_id = UUID(tag_file.stem)
                        from src.services.entity_storage import load_entity
                        from src.models.tag import Tag
                        tag = load_entity(tag_id, ENTITIES_TAGS_DIR, Tag)
                        if tag and tag.meeting_id == meeting_uuid:
                            tags_list.append(tag)
                    except (ValueError, AttributeError):
                        continue
                
                if output_format == "json":
                    import json
                    tags_data = [tag.model_dump(mode="json") for tag in tags_list]
                    typer.echo(json.dumps({"meeting_id": str(meeting_uuid), "tags": tags_data, "count": len(tags_list)}, indent=2))
                else:
                    # Text format
                    typer.echo(f"Meeting ID: {meeting_id}")
                    typer.echo(f"Found {len(tags_list)} tag(s)")
                    typer.echo("\nTags:")
                    for tag in tags_list:
                        if tag.topics_covered:
                            topics = tag.topics_covered if isinstance(tag.topics_covered, list) else [tag.topics_covered]
                            typer.echo(f"  Topics: {', '.join(str(t) for t in topics)}")
                        if tag.emotions:
                            emotions = tag.emotions if isinstance(tag.emotions, list) else [tag.emotions]
                            typer.echo(f"  Emotions: {', '.join(str(e) for e in emotions)}")
                        typer.echo(f"  Created: {tag.created_at}")
                
                logger.info("query_meeting_tags_success", meeting_id=str(meeting_uuid), tag_count=len(tags_list))
            else:
                # Just display meeting info (no options requested)
                typer.echo(f"Meeting ID: {meeting_id}")
                typer.echo("Use --documents to query documents for this meeting.")
                typer.echo("Use --decisions to query decisions made in this meeting.")
                typer.echo("Use --tags to query tags for this meeting.")
            
        except Exception as e:
            logger.error("query_meeting_failed", error=str(e), meeting_id=meeting_id)
            typer.echo(f"Query meeting failed: {e}", err=True)
            raise typer.Exit(code=1)


def query_person_command(
    person_id: str = typer.Argument(..., help="Person ID (UUID)"),
    action_items: bool = typer.Option(
        False,
        "--action-items",
        help="Query action items assigned to this person"
    ),
    output_format: str = typer.Option(
        "text",
        "--output-format",
        help="Output format: text or json"
    )
):
    """
    Query information for a specific person.
    
    With --action-items flag, retrieves all action items assigned to
    the specified person using the entity-based data model.
    """
    try:
        # Parse person_id as UUID
        try:
            person_uuid = UUID(person_id)
        except ValueError:
            typer.echo(f"Invalid person ID format: {person_id}. Expected UUID.", err=True)
            raise typer.Exit(code=1)
        
        # Create query service
        query_service = EntityQueryService()
        
        # Query action items if requested
        if action_items:
            action_items_list = query_service.get_action_items_by_person(person_uuid)
            
            # Format output
            if output_format == "json":
                import json
                action_items_data = [item.model_dump(mode="json") for item in action_items_list]
                typer.echo(json.dumps({"person_id": str(person_uuid), "action_items": action_items_data, "count": len(action_items_list)}, indent=2))
            else:
                # Text format
                typer.echo(f"Person ID: {person_id}")
                typer.echo(f"Found {len(action_items_list)} action item(s)")
                typer.echo("\nAction Items:")
                for item in action_items_list:
                    typer.echo(f"  - {item.text}")
                    typer.echo(f"    Status: {item.status or 'N/A'}")
                    typer.echo(f"    Due Date: {item.due_date or 'N/A'}")
                    typer.echo(f"    Created: {item.created_at}")
            
            logger.info("query_person_action_items_success", person_id=str(person_uuid), action_item_count=len(action_items_list))
        else:
            typer.echo(f"Person ID: {person_id}")
            typer.echo("Use --action-items to query action items for this person.")
        
    except Exception as e:
        logger.error("query_person_failed", error=str(e), person_id=person_id)
        typer.echo(f"Query person failed: {e}", err=True)
        raise typer.Exit(code=1)


def query_decisions_command(
    index_file: str = typer.Argument(..., help="Path to FAISS index file"),
    query_text: str = typer.Argument(..., help="Free text query for decisions"),
    top_k: int = typer.Option(
        DEFAULT_TOP_K,
        "--top-k",
        help="Number of decisions to retrieve"
    ),
    min_score: float = typer.Option(
        0.0,
        "--min-score",
        help="Minimum relevance score threshold (0.0 to 1.0)"
    ),
    output_format: str = typer.Option(
        "text",
        "--output-format",
        help="Output format: text or json"
    ),
    include_rationale: bool = typer.Option(
        True,
        "--include-rationale/--no-rationale",
        help="Include decision rationale in output"
    ),
    include_effect: bool = typer.Option(
        True,
        "--include-effect/--no-effect",
        help="Include decision effect scope in output"
    ),
    include_score: bool = typer.Option(
        False,
        "--include-score/--no-score",
        help="Include relevance score in output"
    )
):
    """
    Query meeting decisions using free text search.
    
    Uses the RAG index to find meetings relevant to your query, then returns
    the actual DecisionItem entities from those meetings. This allows you to
    search for decisions using natural language queries.
    
    Examples:
      archive-rag query-decisions indexes/meetings.faiss "budget decisions"
      archive-rag query-decisions indexes/meetings.faiss "what were the decisions about funding?"
      archive-rag query-decisions indexes/meetings.faiss "decisions that affect other people"
    """
    try:
        # Query decisions using free text
        results = query_decisions_by_text(
            query_text=query_text,
            index_name=index_file,
            top_k=top_k,
            min_score=min_score
        )
        
        # Format output
        if output_format == "json":
            import json
            # Convert DecisionItem objects to dictionaries
            results_data = []
            for result in results:
                decision_dict = result["decision"].model_dump(mode="json")
                results_data.append({
                    "decision": decision_dict,
                    "meeting_id": str(result["meeting_id"]),
                    "relevance_score": result["relevance_score"],
                    "chunk_text": result.get("chunk_text", "")
                })
            typer.echo(json.dumps({
                "query": query_text,
                "results": results_data,
                "count": len(results_data)
            }, indent=2))
        else:
            # Text format
            formatted_output = format_decision_results(
                results,
                include_rationale=include_rationale,
                include_effect=include_effect,
                include_score=include_score
            )
            typer.echo(formatted_output)
        
        logger.info("query_decisions_success", query_text=query_text[:50], result_count=len(results))
        
    except Exception as e:
        logger.error("query_decisions_failed", error=str(e), query_text=query_text[:50] if query_text else "")
        typer.echo(f"Query decisions failed: {e}", err=True)
        raise typer.Exit(code=1)


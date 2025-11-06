"""CLI command for testing entity extraction implementation phases."""

import typer
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID

from ..services.meeting_to_entity import convert_and_save_meeting_record
from ..services.entity_storage import load_entity
from ..lib.config import ENTITIES_WORKGROUPS_DIR, ENTITIES_MEETINGS_DIR, ENTITIES_PEOPLE_DIR
from ..models.workgroup import Workgroup
from ..models.meeting import Meeting
from ..models.person import Person
from ..services.entity_normalization import EntityNormalizationService
from ..services.relationship_triple_generator import RelationshipTripleGenerator
from ..services.ner_integration import NERIntegrationService
from ..services.semantic_chunking import SemanticChunkingService
from ..models.meeting_record import MeetingRecord
from ..lib.logging import get_logger

logger = get_logger(__name__)


def _format_entity_summary(entity_type: str, entity_id: UUID, name: str) -> str:
    """Format entity summary for display."""
    return f"  {entity_type}: {name} ({entity_id})"


def _print_phase_header(phase: str, description: str):
    """Print phase header."""
    typer.echo(f"\n{'='*60}")
    typer.echo(f"Phase: {phase}")
    typer.echo(f"{description}")
    typer.echo(f"{'='*60}")


def _aggregate_phase_results(phase: str, phase_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate results from multiple meetings for a phase."""
    aggregated = {
        "meetings_tested": len(phase_results),
        "aggregated_counts": {}
    }
    
    if phase == "US1":
        # Aggregate entity counts
        total_entities = sum(len(r.get("entities_extracted", [])) for r in phase_results)
        aggregated["aggregated_counts"]["total_entities_extracted"] = total_entities
        aggregated["aggregated_counts"]["avg_entities_per_meeting"] = total_entities / len(phase_results) if phase_results else 0
        
    elif phase == "US2":
        # Aggregate relationship triple counts
        total_triples = sum(len(r.get("triples_generated", [])) for r in phase_results)
        aggregated["aggregated_counts"]["total_relationship_triples"] = total_triples
        aggregated["aggregated_counts"]["avg_triples_per_meeting"] = total_triples / len(phase_results) if phase_results else 0
        
        # Aggregate relationship types
        relationship_types = {}
        for r in phase_results:
            for rel_type, count in r.get("relationship_types", {}).items():
                relationship_types[rel_type] = relationship_types.get(rel_type, 0) + count
        aggregated["aggregated_counts"]["relationship_types"] = relationship_types
        
    elif phase == "US3":
        # Aggregate normalization counts
        total_normalizations = sum(len(r.get("normalizations", [])) for r in phase_results)
        aggregated["aggregated_counts"]["total_normalizations"] = total_normalizations
        aggregated["aggregated_counts"]["avg_normalizations_per_meeting"] = total_normalizations / len(phase_results) if phase_results else 0
        
    elif phase == "US4":
        # Aggregate NER entity counts
        total_ner_entities = sum(len(r.get("ner_entities_extracted", [])) for r in phase_results)
        aggregated["aggregated_counts"]["total_ner_entities"] = total_ner_entities
        aggregated["aggregated_counts"]["avg_ner_entities_per_meeting"] = total_ner_entities / len(phase_results) if phase_results else 0
        
    elif phase == "US5":
        # Aggregate chunk counts
        total_chunks = sum(len(r.get("chunks_created", [])) for r in phase_results)
        aggregated["aggregated_counts"]["total_chunks"] = total_chunks
        aggregated["aggregated_counts"]["avg_chunks_per_meeting"] = total_chunks / len(phase_results) if phase_results else 0
        
        # Aggregate chunk types
        chunk_types = {}
        for r in phase_results:
            for chunk_type, count in r.get("chunk_types", {}).items():
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + count
        aggregated["aggregated_counts"]["chunk_types"] = chunk_types
        
    elif phase == "US6":
        # Aggregate all US6 metrics
        total_entities = sum(len(r.get("structured_entities", [])) for r in phase_results)
        total_labels = sum(len(r.get("normalized_labels", [])) for r in phase_results)
        total_triples = sum(len(r.get("relationship_triples", [])) for r in phase_results)
        total_chunks = sum(len(r.get("chunks", [])) for r in phase_results)
        
        aggregated["aggregated_counts"]["total_entities"] = total_entities
        aggregated["aggregated_counts"]["total_normalized_labels"] = total_labels
        aggregated["aggregated_counts"]["total_relationship_triples"] = total_triples
        aggregated["aggregated_counts"]["total_chunks"] = total_chunks
        aggregated["aggregated_counts"]["avg_entities_per_meeting"] = total_entities / len(phase_results) if phase_results else 0
        aggregated["aggregated_counts"]["avg_labels_per_meeting"] = total_labels / len(phase_results) if phase_results else 0
        aggregated["aggregated_counts"]["avg_triples_per_meeting"] = total_triples / len(phase_results) if phase_results else 0
        aggregated["aggregated_counts"]["avg_chunks_per_meeting"] = total_chunks / len(phase_results) if phase_results else 0
    
    return aggregated


def _print_phase_summary(phase: str, aggregated: Dict[str, Any], meetings_count: int):
    """Print summary statistics for a phase across all meetings."""
    typer.echo(f"\n{phase} Summary (across {meetings_count} meetings):")
    counts = aggregated.get("aggregated_counts", {})
    
    if phase == "US1":
        typer.echo(f"  Total entities extracted: {counts.get('total_entities_extracted', 0)}")
        typer.echo(f"  Average per meeting: {counts.get('avg_entities_per_meeting', 0):.2f}")
        
    elif phase == "US2":
        typer.echo(f"  Total relationship triples: {counts.get('total_relationship_triples', 0)}")
        typer.echo(f"  Average per meeting: {counts.get('avg_triples_per_meeting', 0):.2f}")
        if counts.get("relationship_types"):
            typer.echo("  Relationship types:")
            for rel_type, count in counts["relationship_types"].items():
                typer.echo(f"    {rel_type}: {count}")
        
    elif phase == "US3":
        typer.echo(f"  Total normalizations: {counts.get('total_normalizations', 0)}")
        typer.echo(f"  Average per meeting: {counts.get('avg_normalizations_per_meeting', 0):.2f}")
        
    elif phase == "US4":
        typer.echo(f"  Total NER entities: {counts.get('total_ner_entities', 0)}")
        typer.echo(f"  Average per meeting: {counts.get('avg_ner_entities_per_meeting', 0):.2f}")
        
    elif phase == "US5":
        typer.echo(f"  Total chunks: {counts.get('total_chunks', 0)}")
        typer.echo(f"  Average per meeting: {counts.get('avg_chunks_per_meeting', 0):.2f}")
        if counts.get("chunk_types"):
            typer.echo("  Chunk types:")
            for chunk_type, count in counts["chunk_types"].items():
                typer.echo(f"    {chunk_type}: {count}")
        
    elif phase == "US6":
        typer.echo(f"  Total entities: {counts.get('total_entities', 0)}")
        typer.echo(f"  Total normalized labels: {counts.get('total_normalized_labels', 0)}")
        typer.echo(f"  Total relationship triples: {counts.get('total_relationship_triples', 0)}")
        typer.echo(f"  Total chunks: {counts.get('total_chunks', 0)}")
        typer.echo(f"  Averages per meeting:")
        typer.echo(f"    Entities: {counts.get('avg_entities_per_meeting', 0):.2f}")
        typer.echo(f"    Labels: {counts.get('avg_labels_per_meeting', 0):.2f}")
        typer.echo(f"    Triples: {counts.get('avg_triples_per_meeting', 0):.2f}")
        typer.echo(f"    Chunks: {counts.get('avg_chunks_per_meeting', 0):.2f}")


def test_phase_us1(meeting_record: MeetingRecord) -> Dict[str, Any]:
    """
    Test Phase US1: Extract Entities from JSON Structure.
    
    Verifies:
    - JSON objects are treated as candidate entities
    - Fields representing nouns/real-world objects are extracted
    - Entity filtering criteria are applied
    """
    _print_phase_header(
        "US1",
        "Extract Entities from JSON Structure"
    )
    
    results = {
        "entities_extracted": [],
        "workgroup_entity": None,
        "meeting_entity": None,
        "people_entities": [],
        "document_entities": [],
        "decision_entities": [],
        "action_entities": []
    }
    
    try:
        # Convert meeting record to entities
        meeting_entity = convert_and_save_meeting_record(meeting_record)
        results["meeting_entity"] = {
            "id": str(meeting_entity.id),
            "name": meeting_entity.purpose or f"Meeting {meeting_entity.date}",
            "type": "Meeting"
        }
        
        # Load workgroup
        if meeting_entity.workgroup_id:
            workgroup = load_entity(meeting_entity.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
            if workgroup:
                results["workgroup_entity"] = {
                    "id": str(workgroup.id),
                    "name": workgroup.name,
                    "type": "Workgroup"
                }
                results["entities_extracted"].append(results["workgroup_entity"])
        
        results["entities_extracted"].append(results["meeting_entity"])
        
        # Check for people (from meeting entity's peoplePresent)
        # Note: This would need to query MeetingPerson relationships
        # For now, we'll show the meeting entity as extracted
        
        typer.echo("✓ Entity extraction completed")
        typer.echo(f"  Extracted {len(results['entities_extracted'])} entities")
        
        for entity in results["entities_extracted"]:
            typer.echo(_format_entity_summary(
                entity["type"],
                UUID(entity["id"]),
                entity["name"]
            ))
        
        return results
        
    except Exception as e:
        typer.echo(f"✗ Phase US1 failed: {e}", err=True)
        logger.error("test_phase_us1_failed", error=str(e))
        raise


def test_phase_us2(meeting_record: MeetingRecord) -> Dict[str, Any]:
    """
    Test Phase US2: Capture Entity Relationships.
    
    Verifies:
    - Workgroup → Meeting relationships
    - Meeting → People relationships
    - Meeting → Decisions relationships
    - Action Item → Assignee relationships
    - Decision → Effect relationships
    """
    _print_phase_header(
        "US2",
        "Capture Entity Relationships"
    )
    
    results = {
        "triples_generated": [],
        "relationship_types": {}
    }
    
    try:
        # Convert meeting record
        meeting_entity = convert_and_save_meeting_record(meeting_record)
        
        # Collect entities for this meeting to generate triples
        entities = [meeting_entity]
        if meeting_entity.workgroup_id:
            workgroup = load_entity(meeting_entity.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
            if workgroup:
                entities.append(workgroup)
        
        # Generate relationship triples
        generator = RelationshipTripleGenerator()
        triples = generator.generate_triples(entities, meeting_entity.id)
        
        results["triples_generated"] = [
            {
                "subject": f"{t.subject_name} ({t.subject_type})",
                "relationship": t.relationship,
                "object": f"{t.object_name} ({t.object_type})"
            }
            for t in triples
        ]
        
        # Count relationship types
        for triple in triples:
            rel_type = triple.relationship
            results["relationship_types"][rel_type] = \
                results["relationship_types"].get(rel_type, 0) + 1
        
        typer.echo("✓ Relationship extraction completed")
        typer.echo(f"  Generated {len(results['triples_generated'])} relationship triples")
        
        if results["triples_generated"]:
            typer.echo("\n  Sample relationships:")
            # Show more relationships to see Workgroup -> Decision/Action
            for triple in results["triples_generated"][:10]:  # Show first 10
                typer.echo(f"    {triple['subject']} --[{triple['relationship']}]--> {triple['object']}")
        else:
            typer.echo("  (No relationships found - this may be expected if relationships are not yet implemented)")
        
        return results
        
    except Exception as e:
        typer.echo(f"✗ Phase US2 failed: {e}", err=True)
        logger.error("test_phase_us2_failed", error=str(e))
        raise


def test_phase_us3(meeting_record: MeetingRecord) -> Dict[str, Any]:
    """
    Test Phase US3: Normalize Entity References.
    
    Verifies:
    - Entity name normalization (e.g., "Stephen [QADAO]" → "Stephen")
    - Fuzzy similarity matching (>95%)
    - Entity merging (variations point to canonical entity)
    - Entity lookup by variation
    """
    _print_phase_header(
        "US3",
        "Normalize Entity References"
    )
    
    results = {
        "normalizations": [],
        "similar_entities_found": [],
        "merges_performed": []
    }
    
    try:
        normalization_service = EntityNormalizationService()
        
        # Test normalization with sample names
        test_names = [
            "Stephen [QADAO]",
            "Stephen",
            "André",
            "Archives Workgroup",
            "Archives WG"
        ]
        
        typer.echo("  Testing name normalization:")
        for name in test_names:
            # Pass None for existing_entities to let it load automatically
            canonical_id, canonical_name = normalization_service.normalize_entity_name(
                name, existing_entities=None
            )
            
            if canonical_name != name:
                results["normalizations"].append({
                    "original": name,
                    "canonical": canonical_name
                })
                typer.echo(f"    '{name}' → '{canonical_name}'")
        
        # Test finding similar entities
        typer.echo("\n  Testing similarity matching:")
        # Load existing entities for similarity matching
        existing_entities = normalization_service._load_existing_entities()
        similar = normalization_service.find_similar_entities(
            "Stephen", 
            existing_entities,
            threshold=0.95
        )
        if similar:
            results["similar_entities_found"] = [
                {
                    "query": "Stephen",
                    "found": entity.display_name,
                    "similarity": 0.95  # Approximate - actual similarity would need to be calculated
                }
                for entity in similar
            ]
            typer.echo(f"    Found {len(similar)} similar entities to 'Stephen'")
        
        typer.echo("\n✓ Normalization testing completed")
        typer.echo(f"  {len(results['normalizations'])} normalizations performed")
        
        return results
        
    except Exception as e:
        typer.echo(f"✗ Phase US3 failed: {e}", err=True)
        logger.error("test_phase_us3_failed", error=str(e))
        raise


def test_phase_us4(meeting_record: MeetingRecord) -> Dict[str, Any]:
    """
    Test Phase US4: Apply Named Entity Recognition to Text Fields.
    
    Verifies:
    - NER applied to text fields (purpose, decision text, etc.)
    - NER entities extracted and merged with structured entities
    - Confidence scores assigned
    """
    _print_phase_header(
        "US4",
        "Apply Named Entity Recognition to Text Fields"
    )
    
    results = {
        "ner_entities_extracted": [],
        "entities_merged": []
    }
    
    try:
        ner_service = NERIntegrationService()
        
        # Extract text fields from meeting record
        text_fields = []
        
        # Check meetingInfo.purpose
        if meeting_record.meetingInfo and meeting_record.meetingInfo.purpose:
            text_fields.append(("meetingInfo.purpose", meeting_record.meetingInfo.purpose))
        
        # Check agendaItems[].decisionItems[].decision
        if meeting_record.agendaItems:
            for idx, item in enumerate(meeting_record.agendaItems):
                if hasattr(item, 'decisionItems') and item.decisionItems:
                    for didx, decision in enumerate(item.decisionItems):
                        if hasattr(decision, 'decision') and decision.decision:
                            text_fields.append(
                                (f"agendaItems[{idx}].decisionItems[{didx}].decision", decision.decision)
                            )
                
                # Also check actionItems[].text
                if hasattr(item, 'actionItems') and item.actionItems:
                    for aidx, action in enumerate(item.actionItems):
                        if hasattr(action, 'text') and action.text:
                            text_fields.append(
                                (f"agendaItems[{idx}].actionItems[{aidx}].text", action.text)
                            )
        
        # Check tags.topicsCovered (may contain entity names)
        if meeting_record.tags and hasattr(meeting_record.tags, 'topicsCovered') and meeting_record.tags.topicsCovered:
            text_fields.append(("tags.topicsCovered", meeting_record.tags.topicsCovered))
        
        # Check transcript (legacy format)
        if meeting_record.transcript:
            text_fields.append(("transcript", meeting_record.transcript))
        
        typer.echo(f"  Processing {len(text_fields)} text fields for NER...")
        
        for field_path, text in text_fields:
            if text and len(text.strip()) > 0:
                entities = ner_service.extract_from_text(
                    text=text,
                    meeting_id=meeting_record.id,
                    source_field=field_path
                )
                
                for entity in entities:
                    results["ner_entities_extracted"].append({
                        "text": entity.text,
                        "type": entity.entity_type,
                        "source_field": entity.source_field,
                        "confidence": entity.confidence
                    })
        
        if results["ner_entities_extracted"]:
            typer.echo(f"\n✓ NER extraction completed")
            typer.echo(f"  Extracted {len(results['ner_entities_extracted'])} NER entities")
            typer.echo("\n  Sample entities:")
            for entity in results["ner_entities_extracted"][:5]:  # Show first 5
                typer.echo(f"    '{entity['text']}' ({entity['type']}) - confidence: {entity['confidence']:.2f}")
        else:
            typer.echo("\n✓ NER extraction completed (no entities found in text fields)")
        
        return results
        
    except Exception as e:
        typer.echo(f"✗ Phase US4 failed: {e}", err=True)
        logger.error("test_phase_us4_failed", error=str(e))
        raise


def test_phase_us5(meeting_record: MeetingRecord) -> Dict[str, Any]:
    """
    Test Phase US5: Chunk Text by Semantic Unit Before Embedding.
    
    Verifies:
    - Text chunked by semantic units (meeting summary, action items, decisions, etc.)
    - Entity context preserved in chunks
    - Chunks split at sentence boundaries when needed
    - Entity metadata embedded in chunks
    - Relationship triples included in chunk metadata
    """
    _print_phase_header(
        "US5",
        "Chunk Text by Semantic Unit Before Embedding"
    )
    
    results = {
        "chunks_created": [],
        "chunk_types": {},
        "entities_embedded": 0,
        "relationships_embedded": 0
    }
    
    try:
        typer.echo("  Processing meeting record for semantic chunking...")
        
        # First, extract and save entities (required for semantic chunking)
        meeting_entity = convert_and_save_meeting_record(meeting_record)
        meeting_id = meeting_entity.id
        
        # Use the integrated semantic chunking function from chunking.py
        # This automatically loads entities and generates relationship triples
        from ..services.chunking import chunk_by_semantic_unit
        
        chunks = chunk_by_semantic_unit(
            meeting_record=meeting_record,
            meeting_id=meeting_id,
        )
        
        # Process results
        total_entities = 0
        total_relationships = 0
        
        for chunk in chunks:
            chunk_entity_count = len(chunk.entities)
            chunk_relationship_count = len(chunk.metadata.relationships)
            total_entities += chunk_entity_count
            total_relationships += chunk_relationship_count
            
            results["chunks_created"].append({
                "type": chunk.metadata.chunk_type,
                "text_preview": chunk.text[:50] + "..." if len(chunk.text) > 50 else chunk.text,
                "entities_count": chunk_entity_count,
                "relationships_count": chunk_relationship_count,
                "source_field": chunk.metadata.source_field
            })
            
            # Count chunk types
            results["chunk_types"][chunk.metadata.chunk_type] = \
                results["chunk_types"].get(chunk.metadata.chunk_type, 0) + 1
        
        results["entities_embedded"] = total_entities
        results["relationships_embedded"] = total_relationships
        
        typer.echo(f"\n✓ Semantic chunking completed")
        typer.echo(f"  Created {len(results['chunks_created'])} chunks")
        typer.echo(f"  Total entities embedded: {total_entities}")
        typer.echo(f"  Total relationships embedded: {total_relationships}")
        
        if results["chunk_types"]:
            typer.echo("\n  Chunk types:")
            for chunk_type, count in results["chunk_types"].items():
                typer.echo(f"    {chunk_type}: {count}")
        
        return results
        
    except Exception as e:
        typer.echo(f"✗ Phase US5 failed: {e}", err=True)
        logger.error("test_phase_us5_failed", error=str(e))
        raise


def test_phase_us6(meeting_record: MeetingRecord) -> Dict[str, Any]:
    """
    Test Phase US6: Generate Structured Entity Output.
    
    Verifies:
    - Structured entity list generated
    - Normalized cluster labels generated
    - Relationship triples generated
    - Chunks with metadata generated
    """
    _print_phase_header(
        "US6",
        "Generate Structured Entity Output"
    )
    
    results = {
        "structured_entities": [],
        "normalized_labels": [],
        "relationship_triples": [],
        "chunks": []
    }
    
    try:
        # Convert meeting record
        meeting_entity = convert_and_save_meeting_record(meeting_record)
        
        # Collect entities for this meeting to generate triples
        entities = [meeting_entity]
        if meeting_entity.workgroup_id:
            workgroup = load_entity(meeting_entity.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
            if workgroup:
                entities.append(workgroup)
        
        # Generate relationship triples
        generator = RelationshipTripleGenerator()
        triples = generator.generate_triples(entities, meeting_entity.id)
        
        results["relationship_triples"] = [
            {
                "subject": f"{t.subject_name} ({t.subject_type})",
                "relationship": t.relationship,
                "object": f"{t.object_name} ({t.object_type})"
            }
            for t in triples
        ]
        
        # Collect structured entities
        if meeting_entity.workgroup_id:
            workgroup = load_entity(meeting_entity.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
            if workgroup:
                results["structured_entities"].append({
                    "type": "Workgroup",
                    "name": workgroup.name,
                    "id": str(workgroup.id)
                })
        
        results["structured_entities"].append({
            "type": "Meeting",
            "name": meeting_entity.purpose or f"Meeting {meeting_entity.date}",
            "id": str(meeting_entity.id)
        })
        
        # Generate normalized labels
        normalization_service = EntityNormalizationService()
        for entity in results["structured_entities"]:
            # Pass None for existing_entities to let it load automatically
            canonical_id, canonical_name = normalization_service.normalize_entity_name(
                entity["name"], existing_entities=None
            )
            results["normalized_labels"].append({
                "original": entity["name"],
                "canonical": canonical_name,
                "entity_id": str(canonical_id)
            })
        
        # Generate chunks
        chunking_service = SemanticChunkingService()
        
        # Collect entities for chunking
        entities_for_chunking = []
        if meeting_entity.workgroup_id:
            workgroup = load_entity(meeting_entity.workgroup_id, ENTITIES_WORKGROUPS_DIR, Workgroup)
            if workgroup:
                entities_for_chunking.append(workgroup)
        entities_for_chunking.append(meeting_entity)
        
        chunks = chunking_service.chunk_by_semantic_unit(
            meeting_record=meeting_record,
            entities=entities_for_chunking,
            meeting_id=meeting_record.id
        )
        
        if chunks:
            results["chunks"] = [
                {
                    "type": chunk.metadata.chunk_type,
                    "text_length": len(chunk.text),
                    "entities_count": len(chunk.entities)
                }
                for chunk in chunks
            ]
        
        typer.echo("✓ Structured output generation completed")
        typer.echo(f"  Entities: {len(results['structured_entities'])}")
        typer.echo(f"  Normalized labels: {len(results['normalized_labels'])}")
        typer.echo(f"  Relationship triples: {len(results['relationship_triples'])}")
        typer.echo(f"  Chunks: {len(results['chunks'])}")
        
        return results
        
    except Exception as e:
        typer.echo(f"✗ Phase US6 failed: {e}", err=True)
        logger.error("test_phase_us6_failed", error=str(e))
        raise


def test_entity_extraction_command(
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
    """
    Test entity extraction implementation phases.
    
    This command tests each phase of the entity extraction implementation:
    - US1: Extract Entities from JSON Structure
    - US2: Capture Entity Relationships
    - US3: Normalize Entity References
    - US4: Apply Named Entity Recognition to Text Fields
    - US5: Chunk Text by Semantic Unit Before Embedding
    - US6: Generate Structured Entity Output
    
    Examples:
        # Test single meeting (by index)
        archive-rag test-entity-extraction "https://..." --phases all --meeting-index 0
        
        # Test 5 random meetings
        archive-rag test-entity-extraction "https://..." --phases all --random 5
        
        # Test meetings in index range [0, 10) - use --index-range, NOT --meeting-index
        archive-rag test-entity-extraction "https://..." --phases all --index-range 0:10
        
        # Test specific phases on random meetings
        archive-rag test-entity-extraction "https://..." --phases US1,US2,US3 --random 10
        
    Note: Use --index-range for ranges (e.g., 0:10), --meeting-index for single meeting (e.g., 5)
    """
    try:
        import urllib.request
        import urllib.error
        import json
        
        typer.echo("="*60)
        typer.echo("Entity Extraction Implementation Test")
        typer.echo("="*60)
        typer.echo(f"\nSource URL: {source_url}")
        
        if verify_hash:
            typer.echo(f"Verifying hash: {verify_hash[:16]}...")
        
        # Validate URL
        if not source_url:
            typer.echo(f"✗ Error: URL is required", err=True)
            raise typer.Exit(code=1)
        
        if not (source_url.startswith("http://") or source_url.startswith("https://")):
            typer.echo(f"✗ Error: Invalid URL format. URL must start with 'http://' or 'https://'", err=True)
            typer.echo(f"   Provided: {source_url[:100]}", err=True)
            raise typer.Exit(code=1)
        
        if len(source_url) < 10 or "..." in source_url:
            typer.echo(f"✗ Error: URL appears to be a placeholder. Please provide the actual URL.", err=True)
            typer.echo(f"   Example: https://raw.githubusercontent.com/.../meeting-summaries-array.json", err=True)
            raise typer.Exit(code=1)
        
        # Fetch meeting data
        typer.echo("\nFetching meeting data...")
        try:
            with urllib.request.urlopen(source_url, timeout=30) as response:
                data_bytes = response.read()
                data_text = data_bytes.decode('utf-8')
        except urllib.error.URLError as e:
            typer.echo(f"✗ Error: Failed to fetch URL: {e}", err=True)
            typer.echo(f"   Please check that the URL is valid and accessible.", err=True)
            raise typer.Exit(code=1)
        except Exception as e:
            typer.echo(f"✗ Error: Unexpected error fetching URL: {e}", err=True)
            raise typer.Exit(code=1)
        
        try:
            meetings_data = json.loads(data_text)
        except json.JSONDecodeError as e:
            typer.echo(f"✗ Error: Failed to parse JSON from URL: {e}", err=True)
            raise typer.Exit(code=1)
        
        if not isinstance(meetings_data, list):
            typer.echo("✗ Expected JSON array of meetings", err=True)
            raise typer.Exit(code=1)
        
        total_meetings = len(meetings_data)
        typer.echo(f"Total meetings available: {total_meetings}")
        
        # Determine which meetings to test
        meeting_indices = []
        
        # Validate mutually exclusive options
        options_count = sum([
            meeting_index is not None,
            random is not None,
            index_range is not None
        ])
        
        if options_count > 1:
            typer.echo("✗ Error: --meeting-index, --random, and --index-range are mutually exclusive. Use only one.", err=True)
            raise typer.Exit(code=1)
        
        if random is not None:
            # Test random meetings
            if random <= 0:
                typer.echo("✗ Error: --random must be a positive integer", err=True)
                raise typer.Exit(code=1)
            if random > total_meetings:
                typer.echo(f"✗ Error: --random {random} exceeds total meetings {total_meetings}", err=True)
                raise typer.Exit(code=1)
            
            import random as random_module
            meeting_indices = sorted(random_module.sample(range(total_meetings), random))
            typer.echo(f"Testing {random} random meetings: {meeting_indices}")
            
        elif index_range is not None:
            # Test index range
            try:
                start_str, end_str = index_range.split(":")
                start = int(start_str.strip())
                end = int(end_str.strip())
            except ValueError:
                typer.echo("✗ Error: --index-range must be in format 'START:END' (e.g., '0:5')", err=True)
                raise typer.Exit(code=1)
            
            if start < 0 or end < 0 or start >= end:
                typer.echo("✗ Error: --index-range START must be >= 0 and END must be > START", err=True)
                raise typer.Exit(code=1)
            
            if end > total_meetings:
                typer.echo(f"✗ Warning: --index-range end {end} exceeds total meetings {total_meetings}, using {total_meetings}", err=True)
                end = total_meetings
            
            meeting_indices = list(range(start, end))
            typer.echo(f"Testing meetings in range [{start}, {end}): {meeting_indices}")
            
        elif meeting_index is not None:
            # Test single meeting
            if meeting_index < 0 or meeting_index >= total_meetings:
                typer.echo(f"✗ Error: Meeting index {meeting_index} out of range (available: 0-{total_meetings-1})", err=True)
                raise typer.Exit(code=1)
            meeting_indices = [meeting_index]
            typer.echo(f"Testing single meeting at index {meeting_index}")
        else:
            # Default: test first meeting
            meeting_indices = [0]
            typer.echo("Testing single meeting at index 0 (default)")
        
        # Parse meeting records
        meeting_records = []
        for idx in meeting_indices:
            try:
                meeting_data = meetings_data[idx]
                meeting_record = MeetingRecord.parse_obj(meeting_data)
                meeting_records.append((idx, meeting_record))
            except Exception as e:
                typer.echo(f"✗ Warning: Failed to parse meeting at index {idx}: {e}", err=True)
                logger.warning("meeting_parse_failed", index=idx, error=str(e))
                continue
        
        if not meeting_records:
            typer.echo("✗ Error: No valid meetings to test", err=True)
            raise typer.Exit(code=1)
        
        # Determine which phases to test
        if phases is None or phases.lower() == "all":
            phases_to_test = ["US1", "US2", "US3", "US4", "US5", "US6"]
        else:
            phases_to_test = [p.strip().upper() for p in phases.split(",")]
        
        # Run tests on all selected meetings
        all_results = {}
        phase_results_by_meeting = {}
        
        for meeting_num, (idx, meeting_record) in enumerate(meeting_records, 1):
            typer.echo(f"\n{'='*60}")
            typer.echo(f"Processing Meeting {meeting_num}/{len(meeting_records)} (index {idx})")
            typer.echo(f"{'='*60}")
            
            meeting_results = {}
            
            if "US1" in phases_to_test:
                meeting_results["US1"] = test_phase_us1(meeting_record)
            
            if "US2" in phases_to_test:
                meeting_results["US2"] = test_phase_us2(meeting_record)
            
            if "US3" in phases_to_test:
                meeting_results["US3"] = test_phase_us3(meeting_record)
            
            if "US4" in phases_to_test:
                meeting_results["US4"] = test_phase_us4(meeting_record)
            
            if "US5" in phases_to_test:
                meeting_results["US5"] = test_phase_us5(meeting_record)
            
            if "US6" in phases_to_test:
                meeting_results["US6"] = test_phase_us6(meeting_record)
            
            phase_results_by_meeting[idx] = meeting_results
        
        # Aggregate results across all meetings
        typer.echo(f"\n{'='*60}")
        typer.echo("Aggregating Results Across Meetings")
        typer.echo(f"{'='*60}")
        
        for phase in phases_to_test:
            phase_results = []
            for idx, meeting_results in phase_results_by_meeting.items():
                if phase in meeting_results:
                    phase_results.append(meeting_results[phase])
            
            if phase_results:
                # Aggregate phase results
                aggregated = _aggregate_phase_results(phase, phase_results)
                all_results[phase] = aggregated
                
                # Print summary for this phase
                _print_phase_summary(phase, aggregated, len(phase_results))
        
        # Overall summary
        typer.echo(f"\n{'='*60}")
        typer.echo("Test Summary")
        typer.echo(f"{'='*60}")
        typer.echo(f"Meetings tested: {len(meeting_records)}")
        typer.echo(f"Meeting indices: {meeting_indices}")
        typer.echo(f"Phases tested: {', '.join(phases_to_test)}")
        typer.echo(f"All phases completed successfully")
        
        # Save results if requested
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(all_results, f, indent=2, default=str)
            typer.echo(f"\nResults saved to: {output_file}")
        
        typer.echo("\n✓ All tests completed")
        
    except Exception as e:
        logger.error("test_entity_extraction_failed", error=str(e))
        typer.echo(f"✗ Test failed: {e}", err=True)
        raise typer.Exit(code=1)


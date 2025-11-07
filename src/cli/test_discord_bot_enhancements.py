"""CLI command to test Discord bot enhancements."""

import typer
from pathlib import Path
from typing import Optional

from src.bot.services.enhanced_citation_formatter import EnhancedCitationFormatter, create_enhanced_citation_formatter
from src.bot.services.issue_reporting_service import IssueReportingService, create_issue_reporting_service
from src.bot.services.relationship_query_service import RelationshipQueryService, create_relationship_query_service
from src.bot.services.issue_storage import IssueStorage, create_issue_storage
from src.bot.services.message_formatter import MessageFormatter, create_message_formatter
from src.models.rag_query import Citation
from src.lib.logging import get_logger

logger = get_logger(__name__)

app = typer.Typer(help="Test Discord bot enhancements")


@app.command("enhanced-citations")
def test_enhanced_citations(
    meeting_id: Optional[str] = typer.Option(None, "--meeting-id", help="Meeting ID to test"),
    workgroup_name: Optional[str] = typer.Option("Test WG", "--workgroup", help="Workgroup name"),
):
    """Test enhanced citation formatter."""
    typer.echo("Testing Enhanced Citation Formatter...")
    typer.echo("")
    
    # Create formatter
    formatter = create_enhanced_citation_formatter()
    
    # Create sample citation
    from uuid import uuid4
    citation = Citation(
        meeting_id=meeting_id or str(uuid4()),
        date="2024-01-15",
        workgroup_name=workgroup_name,
        excerpt="Test meeting excerpt about decisions and actions."
    )
    
    # Test basic formatting
    typer.echo("1. Basic Citation Format:")
    basic_format = formatter.format_citation(citation)
    typer.echo(f"   {basic_format}")
    typer.echo("")
    
    # Test enhanced citation
    typer.echo("2. Enhanced Citation Model:")
    enhanced = formatter.format_enhanced_citation(citation)
    typer.echo(f"   Meeting ID: {enhanced.meeting_id}")
    typer.echo(f"   Date: {enhanced.date}")
    typer.echo(f"   Workgroup: {enhanced.workgroup_name}")
    typer.echo(f"   Normalized Entities: {len(enhanced.normalized_entities)}")
    typer.echo(f"   Relationship Triples: {len(enhanced.relationship_triples)}")
    typer.echo(f"   Chunk Type: {enhanced.chunk_type}")
    typer.echo(f"   Chunk Entities: {len(enhanced.chunk_entities)}")
    typer.echo("")
    
    typer.echo("✅ Enhanced citation formatter test completed!")


@app.command("issue-reporting")
def test_issue_reporting(
    storage_dir: Optional[str] = typer.Option(None, "--storage-dir", help="Storage directory for issue reports"),
):
    """Test issue reporting service."""
    typer.echo("Testing Issue Reporting Service...")
    typer.echo("")
    
    # Create storage
    storage = create_issue_storage()
    if storage_dir:
        storage.storage_dir = Path(storage_dir)
        storage.storage_dir.mkdir(parents=True, exist_ok=True)
    
    # Create service
    service = create_issue_reporting_service()
    service.issue_storage = storage
    
    # Test spam detection
    typer.echo("1. Testing Spam Detection:")
    from src.bot.models.discord_user import DiscordUser
    from src.bot.models.issue_report import IssueReport
    from datetime import datetime
    from uuid import uuid4
    
    user = DiscordUser(user_id="123", username="testuser", roles=[])
    
    # Normal report
    normal_report = IssueReport(
        id=uuid4(),
        query_text="Normal query",
        response_text="Normal response",
        citations=[],
        user_description="Normal issue",
        user_id=user.user_id,
        username=user.username,
        timestamp=datetime.utcnow()
    )
    
    is_spam, reason = service._detect_spam(normal_report, user)
    typer.echo(f"   Normal report - Spam: {is_spam}, Reason: {reason}")
    
    # Test storage
    typer.echo("")
    typer.echo("2. Testing Issue Storage:")
    storage.save_issue_report(normal_report)
    typer.echo(f"   Saved issue report: {normal_report.id}")
    
    loaded = storage.load_issue_report(normal_report.id)
    if loaded:
        typer.echo(f"   Loaded issue report: {loaded.id}")
        typer.echo(f"   Query: {loaded.query_text}")
        typer.echo(f"   User: {loaded.username}")
    
    typer.echo("")
    typer.echo("✅ Issue reporting service test completed!")


@app.command("relationship-queries")
def test_relationship_queries(
    entity_name: str = typer.Option("Stephen", "--entity", help="Entity name to query"),
    entity_type: str = typer.Option("person", "--type", help="Entity type: person, workgroup, meeting"),
):
    """Test relationship query service."""
    typer.echo("Testing Relationship Query Service...")
    typer.echo("")
    
    service = create_relationship_query_service()
    
    if entity_type == "person":
        typer.echo(f"Querying relationships for person: {entity_name}")
        triples, canonical_name, error_msg = service.get_relationships_for_person(entity_name)
        
        if error_msg:
            typer.echo(f"   Error: {error_msg}")
        else:
            typer.echo(f"   Canonical Name: {canonical_name}")
            typer.echo(f"   Relationships Found: {len(triples)}")
            for i, triple in enumerate(triples[:5], 1):
                typer.echo(f"   {i}. {triple.subject_type} ({triple.subject_name}) → {triple.relationship} → {triple.object_type} ({triple.object_name})")
    
    elif entity_type == "workgroup":
        typer.echo(f"Querying relationships for workgroup: {entity_name}")
        triples, canonical_name, error_msg = service.get_relationships_for_workgroup(entity_name)
        
        if error_msg:
            typer.echo(f"   Error: {error_msg}")
        else:
            typer.echo(f"   Canonical Name: {canonical_name}")
            typer.echo(f"   Relationships Found: {len(triples)}")
            for i, triple in enumerate(triples[:5], 1):
                typer.echo(f"   {i}. {triple.subject_type} ({triple.subject_name}) → {triple.relationship} → {triple.object_type} ({triple.object_name})")
    
    typer.echo("")
    typer.echo("✅ Relationship query service test completed!")


@app.command("people-normalization")
def test_people_normalization(
    person_name: str = typer.Option("Stephen", "--person", help="Person name to test normalization"),
):
    """Test people command normalization."""
    typer.echo("Testing People Command Normalization...")
    typer.echo("")
    
    from src.services.entity_query import EntityQueryService
    from src.services.entity_normalization import EntityNormalizationService
    from src.lib.config import ENTITIES_PEOPLE_DIR
    from src.models.person import Person
    
    entity_service = EntityQueryService()
    normalization_service = EntityNormalizationService()
    
    # Load all people
    typer.echo(f"1. Loading all people from {ENTITIES_PEOPLE_DIR}...")
    all_people = entity_service.find_all(ENTITIES_PEOPLE_DIR, Person)
    typer.echo(f"   Found {len(all_people)} people")
    typer.echo("")
    
    # Test normalization
    typer.echo(f"2. Testing normalization for: '{person_name}'")
    try:
        normalized_id, canonical_name = normalization_service.normalize_entity_name(
            person_name,
            all_people,
            {}
        )
        
        if normalized_id.int != 0:
            typer.echo(f"   ✅ Normalized to: '{canonical_name}' (ID: {normalized_id})")
            
            # Find person entity
            person = entity_service.get_by_id(normalized_id, ENTITIES_PEOPLE_DIR, Person)
            if person:
                typer.echo(f"   Person found: {person.display_name}")
                if person.alias:
                    typer.echo(f"   Alias: {person.alias}")
        else:
            typer.echo(f"   ⚠️  No existing entity found, canonical name: '{canonical_name}'")
    except Exception as e:
        typer.echo(f"   ❌ Normalization failed: {e}")
    
    typer.echo("")
    
    # Test finding similar entities
    typer.echo(f"3. Finding similar entities to: '{person_name}'")
    similar = normalization_service.find_similar_entities(person_name, all_people)
    typer.echo(f"   Found {len(similar)} similar entities:")
    for i, person in enumerate(similar[:5], 1):
        typer.echo(f"   {i}. {person.display_name} (ID: {person.id})")
        if person.alias:
            typer.echo(f"      Alias: {person.alias}")
    
    typer.echo("")
    typer.echo("✅ People normalization test completed!")


@app.command("topics-normalization")
def test_topics_normalization(
    topic_name: str = typer.Option("budget", "--topic", help="Topic name to test normalization"),
):
    """Test topics command normalization."""
    typer.echo("Testing Topics Command Normalization...")
    typer.echo("")
    
    from src.services.entity_query import EntityQueryService
    from src.services.entity_normalization import EntityNormalizationService
    
    entity_service = EntityQueryService()
    normalization_service = EntityNormalizationService()
    
    # Get all topics
    typer.echo("1. Loading all topics...")
    all_topics = entity_service.get_all_topics()
    typer.echo(f"   Found {len(all_topics)} unique topics")
    if all_topics:
        typer.echo(f"   Sample topics: {', '.join(all_topics[:5])}")
    typer.echo("")
    
    if not all_topics:
        typer.echo("   ⚠️  No topics found in database")
        typer.echo("")
        typer.echo("✅ Topics normalization test completed (no data to test)")
        return
    
    # Create entity-like structure for normalization
    class TopicEntity:
        def __init__(self, name):
            self.name = name
            self.display_name = name
            self.id = None
    
    topic_entities = [TopicEntity(t) for t in all_topics]
    
    # Test normalization
    typer.echo(f"2. Testing normalization for: '{topic_name}'")
    try:
        similar_topics = normalization_service.find_similar_entities(
            topic_name,
            topic_entities
        )
        
        if similar_topics:
            typer.echo(f"   ✅ Found {len(similar_topics)} similar topics:")
            for i, topic_entity in enumerate(similar_topics[:5], 1):
                typer.echo(f"   {i}. {topic_entity.display_name}")
        else:
            typer.echo(f"   ⚠️  No similar topics found")
    except Exception as e:
        typer.echo(f"   ❌ Normalization failed: {e}")
    
    typer.echo("")
    
    # Test topic search
    typer.echo(f"3. Testing topic search for: '{topic_name}'")
    try:
        meetings = entity_service.get_meetings_by_tag(topic_name, "topics")
        typer.echo(f"   Found {len(meetings)} meetings with this topic")
        if meetings:
            for i, meeting in enumerate(meetings[:3], 1):
                typer.echo(f"   {i}. {meeting.date} - {meeting.workgroup_name or 'Unknown'}")
    except Exception as e:
        typer.echo(f"   ❌ Search failed: {e}")
    
    typer.echo("")
    typer.echo("✅ Topics normalization test completed!")


@app.command("all")
def test_all():
    """Run all tests."""
    typer.echo("Running all Discord bot enhancement tests...")
    typer.echo("")
    
    # Test enhanced citations
    typer.echo("=== Testing Enhanced Citations ===")
    test_enhanced_citations()
    typer.echo("")
    
    # Test issue reporting
    typer.echo("=== Testing Issue Reporting ===")
    test_issue_reporting()
    typer.echo("")
    
    # Test relationship queries
    typer.echo("=== Testing Relationship Queries ===")
    typer.echo("Note: Relationship queries require existing entities in the database.")
    typer.echo("")
    
    # Test people normalization
    typer.echo("=== Testing People Normalization ===")
    test_people_normalization()
    typer.echo("")
    
    # Test topics normalization
    typer.echo("=== Testing Topics Normalization ===")
    test_topics_normalization()
    typer.echo("")
    
    typer.echo("✅ All tests completed!")


if __name__ == "__main__":
    app()


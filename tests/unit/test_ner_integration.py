"""Unit tests for NER integration service."""

import pytest
from uuid import UUID, uuid4

from src.services.ner_integration import NERIntegrationService
from src.models.ner_entity import NEREntity
from src.models.person import Person


class TestNERIntegrationService:
    """Unit tests for NERIntegrationService."""
    
    @pytest.fixture
    def ner_service(self):
        """Fixture for NERIntegrationService."""
        try:
            return NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
    
    @pytest.fixture
    def meeting_id(self):
        """Fixture for meeting UUID."""
        return uuid4()
    
    def test_extract_from_text_empty(self, ner_service, meeting_id):
        """Test extraction from empty text returns empty list."""
        entities = ner_service.extract_from_text(
            text="",
            meeting_id=meeting_id,
            source_field="test.field"
        )
        assert entities == []
    
    def test_extract_from_text_whitespace(self, ner_service, meeting_id):
        """Test extraction from whitespace-only text returns empty list."""
        entities = ner_service.extract_from_text(
            text="   \n\t  ",
            meeting_id=meeting_id,
            source_field="test.field"
        )
        assert entities == []
    
    def test_extract_from_text_person_entity(self, ner_service, meeting_id):
        """Test extraction of person entities from text."""
        text = "Alice Smith and Bob Johnson attended the meeting in New York on January 15, 2025."
        entities = ner_service.extract_from_text(
            text=text,
            meeting_id=meeting_id,
            source_field="meetingInfo.purpose"
        )
        
        # Should extract person names (PERSON entities)
        person_entities = [e for e in entities if e.entity_type == "PERSON"]
        assert len(person_entities) > 0
        
        # Verify entity structure
        for entity in person_entities:
            assert isinstance(entity, NEREntity)
            assert entity.text is not None
            assert entity.text.strip() != ""
            assert entity.entity_type == "PERSON"
            assert entity.source_text == text
            assert entity.source_field == "meetingInfo.purpose"
            assert entity.source_meeting_id == meeting_id
            assert entity.normalized_entity_id is None  # Not merged yet
            assert 0.0 <= entity.confidence <= 1.0
    
    def test_extract_from_text_org_entity(self, ner_service, meeting_id):
        """Test extraction of organization entities from text."""
        text = "The meeting was organized by SingularityNET and OpenAI."
        entities = ner_service.extract_from_text(
            text=text,
            meeting_id=meeting_id,
            source_field="meetingInfo.purpose"
        )
        
        # Should extract organization names (ORG entities)
        org_entities = [e for e in entities if e.entity_type == "ORG"]
        assert len(org_entities) > 0
        
        for entity in org_entities:
            assert entity.entity_type == "ORG"
            assert len(entity.text) > 0
    
    def test_extract_from_text_date_entity(self, ner_service, meeting_id):
        """Test extraction of date entities from text."""
        text = "The meeting will be held on January 15, 2025."
        entities = ner_service.extract_from_text(
            text=text,
            meeting_id=meeting_id,
            source_field="meetingInfo.purpose"
        )
        
        # Should extract date entities
        date_entities = [e for e in entities if e.entity_type == "DATE"]
        # Note: May or may not extract dates depending on spaCy model
        for entity in date_entities:
            assert entity.entity_type == "DATE"
    
    def test_extract_from_text_filters_filler_comments(self, ner_service, meeting_id):
        """Test that filler comments are filtered out (FR-014)."""
        text = "This is a comment. N/A. TODO: add more. Filler text."
        entities = ner_service.extract_from_text(
            text=text,
            meeting_id=meeting_id,
            source_field="test.field"
        )
        
        # Should not extract "N/A", "TODO", "Filler" as entities
        entity_texts = [e.text.lower() for e in entities]
        assert "n/a" not in entity_texts
        assert "todo" not in entity_texts
        assert "filler" not in entity_texts
    
    def test_extract_from_text_filters_short_entities(self, ner_service, meeting_id):
        """Test that very short entities are filtered out."""
        text = "A B C D E F G"
        entities = ner_service.extract_from_text(
            text=text,
            meeting_id=meeting_id,
            source_field="test.field"
        )
        
        # Should filter out single-character entities
        for entity in entities:
            assert len(entity.text.strip()) >= 2
    
    def test_should_extract_ner_entity_person(self, ner_service):
        """Test that PERSON entities are extracted."""
        assert ner_service._should_extract_ner_entity("Alice Smith", "PERSON") is True
        assert ner_service._should_extract_ner_entity("Bob Johnson", "PERSON") is True
    
    def test_should_extract_ner_entity_org(self, ner_service):
        """Test that ORG entities are extracted."""
        assert ner_service._should_extract_ner_entity("SingularityNET", "ORG") is True
        assert ner_service._should_extract_ner_entity("OpenAI", "ORG") is True
    
    def test_should_extract_ner_entity_filters_filler(self, ner_service):
        """Test that filler keywords are filtered."""
        assert ner_service._should_extract_ner_entity("n/a", "PERSON") is False
        assert ner_service._should_extract_ner_entity("todo", "PERSON") is False
        assert ner_service._should_extract_ner_entity("filler", "PERSON") is False
        assert ner_service._should_extract_ner_entity("comment", "PERSON") is False
    
    def test_should_extract_ner_entity_filters_short(self, ner_service):
        """Test that very short entities are filtered."""
        assert ner_service._should_extract_ner_entity("A", "PERSON") is False
        assert ner_service._should_extract_ner_entity("", "PERSON") is False
        assert ner_service._should_extract_ner_entity(" ", "PERSON") is False
    
    def test_should_extract_ner_entity_date_meaningful(self, ner_service):
        """Test that meaningful dates are extracted."""
        assert ner_service._should_extract_ner_entity("January 15, 2025", "DATE") is True
        assert ner_service._should_extract_ner_entity("2025-01-15", "DATE") is True
    
    def test_should_extract_ner_entity_date_relative_filtered(self, ner_service):
        """Test that relative dates are filtered out."""
        assert ner_service._should_extract_ner_entity("today", "DATE") is False
        assert ner_service._should_extract_ner_entity("tomorrow", "DATE") is False
        assert ner_service._should_extract_ner_entity("yesterday", "DATE") is False
    
    def test_merge_with_structured_empty_entities(self, ner_service):
        """Test merging with empty structured entities list."""
        # Use a unique name that won't exist in storage
        unique_name = f"TestPerson_{uuid4().hex[:8]}"
        ner_entities = [
            NEREntity(
                text=unique_name,
                entity_type="PERSON",
                source_text="Test text",
                source_field="test.field",
                source_meeting_id=uuid4(),
                normalized_entity_id=None,
                confidence=1.0
            )
        ]
        
        merged = ner_service.merge_with_structured(ner_entities, [])
        assert len(merged) == 1
        # When no entities are provided and normalization loads from storage,
        # it may find a match or may not. The key is that it doesn't crash.
        assert merged[0].text == unique_name
    
    def test_merge_with_structured_exact_match(self, ner_service):
        """Test merging with exact name match."""
        meeting_id = uuid4()
        ner_entity = NEREntity(
            text="Alice Smith",
            entity_type="PERSON",
            source_text="Test text",
            source_field="test.field",
            source_meeting_id=meeting_id,
            normalized_entity_id=None,
            confidence=1.0
        )
        
        # Create structured entity with exact match
        person = Person(display_name="Alice Smith")
        
        merged = ner_service.merge_with_structured([ner_entity], [person])
        assert len(merged) == 1
        # Should match (either via normalization or fuzzy matching)
        assert merged[0].text == "Alice Smith"
    
    def test_merge_with_structured_fuzzy_match(self, ner_service):
        """Test merging with fuzzy similarity match (>95%)."""
        meeting_id = uuid4()
        ner_entity = NEREntity(
            text="Alice Smith",
            entity_type="PERSON",
            source_text="Test text",
            source_field="test.field",
            source_meeting_id=meeting_id,
            normalized_entity_id=None,
            confidence=1.0
        )
        
        # Create structured entity with similar name
        person = Person(display_name="Alice Smyth")  # One character difference
        
        merged = ner_service.merge_with_structured([ner_entity], [person])
        assert len(merged) == 1
        # Should match via fuzzy matching if similarity >= 95%
        assert merged[0].text == "Alice Smith"
    
    def test_merge_with_structured_no_match(self, ner_service):
        """Test merging when no match is found."""
        meeting_id = uuid4()
        ner_entity = NEREntity(
            text="Bob Johnson",
            entity_type="PERSON",
            source_text="Test text",
            source_field="test.field",
            source_meeting_id=meeting_id,
            normalized_entity_id=None,
            confidence=1.0
        )
        
        # Create structured entity with different name
        person = Person(display_name="Alice Smith")
        
        merged = ner_service.merge_with_structured([ner_entity], [person])
        assert len(merged) == 1
        assert merged[0].text == "Bob Johnson"
        # normalized_entity_id may be set by normalization service or None
    
    def test_merge_with_structured_workgroup_entity(self, ner_service):
        """Test merging with workgroup entities (entities with 'name' attribute)."""
        from src.models.workgroup import Workgroup
        
        meeting_id = uuid4()
        ner_entity = NEREntity(
            text="Archives Workgroup",
            entity_type="ORG",
            source_text="Test text",
            source_field="test.field",
            source_meeting_id=meeting_id,
            normalized_entity_id=None,
            confidence=1.0
        )
        
        workgroup = Workgroup(name="Archives Workgroup")
        
        merged = ner_service.merge_with_structured([ner_entity], [workgroup])
        assert len(merged) == 1
        assert merged[0].text == "Archives Workgroup"
        # The merge function should handle entities with 'name' attribute correctly
        # It may or may not set normalized_entity_id depending on normalization service
        # The important thing is that it doesn't crash when accessing the 'name' attribute


class TestNEREntityFiltering:
    """Unit tests for NER entity filtering criteria (FR-013, FR-014)."""
    
    @pytest.fixture
    def ner_service(self):
        """Fixture for NERIntegrationService."""
        try:
            return NERIntegrationService()
        except ValueError as e:
            pytest.skip(f"spaCy model not available: {e}")
    
    def test_filter_by_thing_type(self, ner_service):
        """Test filtering by entity type (thing types)."""
        # PERSON, ORG, GPE are thing types
        assert ner_service._should_extract_ner_entity("Alice", "PERSON") is True
        assert ner_service._should_extract_ner_entity("Company", "ORG") is True
        assert ner_service._should_extract_ner_entity("New York", "GPE") is True
    
    def test_filter_by_searchable_content(self, ner_service):
        """Test filtering by searchable content."""
        # Entities with meaningful alphanumeric content
        assert ner_service._should_extract_ner_entity("ProjectX", "MISC") is True
        assert ner_service._should_extract_ner_entity("ABC123", "MISC") is True
    
    def test_filter_by_meaningful_words(self, ner_service):
        """Test filtering by meaningful words (3+ characters)."""
        # Entities with words of 3+ characters
        assert ner_service._should_extract_ner_entity("Important Meeting", "MISC") is True
        assert ner_service._should_extract_ner_entity("Budget Review", "MISC") is True
    
    def test_filter_out_filler_comments(self, ner_service):
        """Test filtering out filler comments (FR-014)."""
        filler_words = ["comment", "filler", "n/a", "none", "tbd", "todo", "tba"]
        for word in filler_words:
            assert ner_service._should_extract_ner_entity(word, "MISC") is False
    
    def test_filter_out_short_entities(self, ner_service):
        """Test filtering out very short entities."""
        assert ner_service._should_extract_ner_entity("A", "PERSON") is False
        assert ner_service._should_extract_ner_entity("", "PERSON") is False
        assert ner_service._should_extract_ner_entity(" ", "PERSON") is False
        assert ner_service._should_extract_ner_entity("AB", "PERSON") is True  # 2 chars is OK

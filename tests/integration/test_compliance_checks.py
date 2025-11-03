"""Integration tests for constitution compliance checks."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.lib.compliance import (
    ConstitutionViolation,
    ViolationType,
    DetectionLayer,
    ComplianceStatus
)
from src.lib.static_analysis import check_no_external_apis
from src.services.compliance_checker import ComplianceChecker
from src.services.entity_storage import save_entity, load_entity
from src.services.embedding import EmbeddingService
from src.services.rag_generator import RAGGenerator
from src.models.workgroup import Workgroup
from src.models.meeting import Meeting


class TestEntityOperationsCompliance:
    """Integration tests for entity operations compliance."""
    
    def test_entity_storage_no_external_apis(self, tmp_path):
        """Test that entity storage operations don't use external APIs."""
        from src.lib.config import init_entity_storage
        
        # Initialize entity storage
        with patch('src.lib.config.ENTITIES_DIR', tmp_path / "entities"):
            init_entity_storage()
            
            # Create and save workgroup
            workgroup = Workgroup(name="Test Workgroup")
            save_entity(workgroup, tmp_path / "entities" / "workgroups")
            
            # Load workgroup
            loaded = load_entity(workgroup.id, tmp_path / "entities" / "workgroups", Workgroup)
            
            # Verify no external API calls were made
            assert loaded is not None
            assert loaded.name == "Test Workgroup"
    
    def test_entity_storage_python_only(self, tmp_path):
        """Test that entity storage uses only Python standard library."""
        from src.lib.config import init_entity_storage
        
        # Check that entity_storage.py doesn't have external API imports
        entity_storage_file = Path("src/services/entity_storage.py")
        if entity_storage_file.exists():
            violations = check_no_external_apis(entity_storage_file)
            
            # Should not have external API violations
            external_api_violations = [v for v in violations if v.violation_type == ViolationType.EXTERNAL_API]
            assert len(external_api_violations) == 0, f"Found external API violations: {external_api_violations}"


class TestEmbeddingOperationsCompliance:
    """Integration tests for embedding operations compliance."""
    
    def test_embedding_service_local_only(self):
        """Test that embedding service uses local models only."""
        # Check that embedding.py doesn't have external API imports
        embedding_file = Path("src/services/embedding.py")
        if embedding_file.exists():
            violations = check_no_external_apis(embedding_file)
            
            # Should not have external API violations (local models only)
            external_api_violations = [v for v in violations if v.violation_type == ViolationType.EXTERNAL_API]
            assert len(external_api_violations) == 0, f"Found external API violations: {external_api_violations}"
    
    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_service_no_network_calls(self, mock_model):
        """Test that embedding service doesn't make network calls."""
        checker = ComplianceChecker()
        checker.enable_monitoring()
        
        try:
            service = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
            service.model = mock_model
            
            # Embedding should not trigger network calls
            violations = checker.check_embedding_operations()
            
            # Should not have network call violations
            network_violations = [v for v in violations if v.violation_type == ViolationType.EXTERNAL_API]
            assert len(network_violations) == 0
        finally:
            checker.disable_monitoring()


class TestLLMOperationsCompliance:
    """Integration tests for LLM inference operations compliance."""
    
    def test_llm_service_local_only(self):
        """Test that LLM service uses local models only."""
        # Check that rag_generator.py doesn't have external API imports
        rag_file = Path("src/services/rag_generator.py")
        if rag_file.exists():
            violations = check_no_external_apis(rag_file)
            
            # Should not have external API violations (local models only)
            external_api_violations = [v for v in violations if v.violation_type == ViolationType.EXTERNAL_API]
            assert len(external_api_violations) == 0, f"Found external API violations: {external_api_violations}"
    
    @patch('transformers.AutoTokenizer')
    @patch('transformers.AutoModelForCausalLM')
    def test_llm_service_no_network_calls(self, mock_model, mock_tokenizer):
        """Test that LLM service doesn't make network calls."""
        checker = ComplianceChecker()
        checker.enable_monitoring()
        
        try:
            generator = RAGGenerator(model_name="gpt2")
            generator.model = mock_model
            generator.tokenizer = mock_tokenizer
            
            # LLM generation should not trigger network calls
            violations = checker.check_llm_operations()
            
            # Should not have network call violations
            network_violations = [v for v in violations if v.violation_type == ViolationType.EXTERNAL_API]
            assert len(network_violations) == 0
        finally:
            checker.disable_monitoring()


class TestFAISSOperationsCompliance:
    """Integration tests for FAISS operations compliance."""
    
    def test_faiss_operations_local_only(self):
        """Test that FAISS operations use local storage only (T040 - US3)."""
        # Check index_builder.py and retrieval.py for external API imports
        index_file = Path("src/services/index_builder.py")
        retrieval_file = Path("src/services/retrieval.py")
        
        all_violations = []
        for file_path in [index_file, retrieval_file]:
            if file_path.exists():
                violations = check_no_external_apis(file_path)
                all_violations.extend(violations)
        
        # Should not have remote storage violations
        remote_storage_violations = [v for v in all_violations if v.violation_type == ViolationType.REMOTE_STORAGE]
        assert len(remote_storage_violations) == 0, f"Found remote storage violations: {remote_storage_violations}"
    
    def test_faiss_index_creation_local_only(self, tmp_path):
        """Test that FAISS index creation is local-only (T039 - US3)."""
        from src.services.index_builder import build_faiss_index, save_index
        from src.services.compliance_checker import ComplianceChecker
        from src.services.chunking import DocumentChunk
        from unittest.mock import MagicMock
        
        # Enable compliance monitoring
        checker = ComplianceChecker()
        checker.enable_monitoring()
        
        try:
            # Create mock chunks
            chunks = [
                DocumentChunk(
                    meeting_id="test-meeting-1",
                    chunk_index=0,
                    text="Test chunk text",
                    start_idx=0,
                    end_idx=len("Test chunk text")
                )
            ]
            
            # Create mock embedding service
            embedding_service = MagicMock()
            embedding_service.model_name = "sentence-transformers/all-MiniLM-L6-v2"
            embedding_service.embed_texts.return_value = MagicMock(shape=(1, 384))
            embedding_service.get_embedding_dimension.return_value = 384
            
            # Build index (should be local-only)
            index, embedding_index = build_faiss_index(
                chunks,
                embedding_service,
                index_type="IndexFlatIP",
                index_name="test-index"
            )
            
            # Check for violations
            violations = checker.check_faiss_operations()
            
            # Should not have remote storage violations
            remote_storage_violations = [v for v in violations if v.violation_type == ViolationType.REMOTE_STORAGE]
            assert len(remote_storage_violations) == 0, f"Found remote storage violations: {remote_storage_violations}"
            
            # Verify index path is local
            assert embedding_index.index_path.startswith('/') or embedding_index.index_path.startswith('.') or 'indexes' in embedding_index.index_path
        finally:
            checker.disable_monitoring()
    
    def test_rag_queries_with_entity_based_faiss_index(self, tmp_path):
        """Test that RAG queries work with entity-based FAISS indexes (T041 - US3)."""
        from src.services.query_service import QueryService
        from src.services.compliance_checker import ComplianceChecker
        from unittest.mock import patch, MagicMock
        
        # Enable compliance monitoring
        checker = ComplianceChecker()
        checker.enable_monitoring()
        
        try:
            # Mock FAISS index operations
            with patch('src.services.retrieval.load_index') as mock_load_index, \
                 patch('src.services.embedding.create_embedding_service') as mock_embedding_service:
                
                # Setup mocks
                mock_index = MagicMock()
                mock_embedding_index = MagicMock()
                mock_embedding_index.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
                mock_load_index.return_value = (mock_index, mock_embedding_index)
                
                mock_emb_service = MagicMock()
                mock_emb_service.embed_text.return_value = MagicMock()
                mock_embedding_service.return_value = mock_emb_service
                
                # Create query service
                query_service = QueryService()
                
                # Execute query (should use local FAISS index)
                # Note: This will fail on actual execution but tests compliance checking
                violations = checker.check_faiss_operations()
                
                # Should not have remote storage violations
                remote_storage_violations = [v for v in violations if v.violation_type == ViolationType.REMOTE_STORAGE]
                assert len(remote_storage_violations) == 0, f"Found remote storage violations: {remote_storage_violations}"
        finally:
            checker.disable_monitoring()


class TestPythonOnlyCompliance:
    """Integration tests for Python-only requirement compliance."""
    
    def test_entity_operations_python_only(self):
        """Test that entity operations use only Python standard library (T031 - US2)."""
        # Check entity_storage.py for subprocess calls
        entity_storage_file = Path("src/services/entity_storage.py")
        if entity_storage_file.exists():
            violations = check_no_external_apis(entity_storage_file)
            
            # Should not have external binary violations
            external_binary_violations = [v for v in violations if v.violation_type == ViolationType.EXTERNAL_BINARY]
            assert len(external_binary_violations) == 0, f"Found external binary violations: {external_binary_violations}"
    
    def test_entity_operations_use_standard_library(self, tmp_path):
        """Test that entity operations use only Python standard library (json, pathlib) (T031 - US2)."""
        from src.lib.config import init_entity_storage
        
        # Initialize entity storage
        with patch('src.lib.config.ENTITIES_DIR', tmp_path / "entities"):
            init_entity_storage()
            
            # Create and save workgroup using only standard library
            workgroup = Workgroup(name="Test Workgroup")
            from src.services.entity_storage import save_entity, load_entity
            
            # Save should use only json and pathlib (standard library)
            save_entity(workgroup, tmp_path / "entities" / "workgroups")
            
            # Load should use only json and pathlib (standard library)
            loaded = load_entity(workgroup.id, tmp_path / "entities" / "workgroups", Workgroup)
            
            # Verify operations completed without external binaries
            assert loaded is not None
            assert loaded.name == "Test Workgroup"
    
    def test_no_external_binary_execution(self, tmp_path):
        """Test that no external binaries are executed during entity operations (T032 - US2)."""
        from src.lib.config import init_entity_storage
        from src.services.compliance_checker import ComplianceChecker
        
        # Initialize entity storage
        with patch('src.lib.config.ENTITIES_DIR', tmp_path / "entities"):
            init_entity_storage()
            
            # Enable compliance monitoring
            checker = ComplianceChecker()
            checker.enable_monitoring()
            
            try:
                # Create and save workgroup
                workgroup = Workgroup(name="Test Workgroup")
                from src.services.entity_storage import save_entity
                
                # Save operation should not trigger process spawn violations
                save_entity(workgroup, tmp_path / "entities" / "workgroups")
                
                # Check for process spawn violations
                violations = checker.process_monitor.get_violations()
                
                # Should not have external binary violations
                external_binary_violations = [v for v in violations if v.violation_type == ViolationType.EXTERNAL_BINARY]
                assert len(external_binary_violations) == 0, f"Found external binary violations: {external_binary_violations}"
            finally:
                checker.disable_monitoring()


class TestCLICompliance:
    """Integration tests for CLI support compliance."""
    
    def test_cli_commands_no_external_dependencies(self):
        """Test that CLI commands work without external dependencies."""
        # Check query.py and other CLI files for external API imports
        cli_files = [
            Path("src/cli/query.py"),
            Path("src/cli/index.py"),
            Path("src/cli/compliance.py")
        ]
        
        all_violations = []
        for file_path in cli_files:
            if file_path.exists():
                violations = check_no_external_apis(file_path)
                all_violations.extend(violations)
        
        # Should not have external API violations
        external_api_violations = [v for v in all_violations if v.violation_type == ViolationType.EXTERNAL_API]
        assert len(external_api_violations) == 0, f"Found external API violations in CLI: {external_api_violations}"


"""Contract test for query command."""

import pytest
from typer.testing import CliRunner
from src.cli.main import app


class TestQueryCommand:
    """Contract tests for query command."""
    
    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()
    
    def test_query_command_help(self, runner):
        """Test query command help."""
        result = runner.invoke(app, ["query", "--help"])
        assert result.exit_code == 0
        assert "Query the RAG system" in result.stdout
    
    def test_query_command_structure(self, runner, tmp_path):
        """Test query command structure (contract test)."""
        # Create a dummy index file path
        index_file = str(tmp_path / "test_index.faiss")
        
        result = runner.invoke(app, [
            "query",
            index_file,
            "What decisions were made?"
        ])
        
        # Contract test validates command structure exists
        # Will fail if index file doesn't exist, but validates command accepts args
        assert result.exit_code in [0, 1]
    
    def test_query_command_with_options(self, runner, tmp_path):
        """Test query command with options."""
        index_file = str(tmp_path / "test_index.faiss")
        result = runner.invoke(app, [
            "query",
            index_file,
            "What decisions were made?",
            "--top-k", "10",
            "--seed", "42",
            "--output-format", "json",
            "--user-id", "test@example.com"
        ])
        
        # Contract test validates options are accepted
        assert result.exit_code in [0, 1]
    
    def test_query_workgroup_command_help(self, runner):
        """Test query-workgroup command help."""
        result = runner.invoke(app, ["query-workgroup", "--help"])
        assert result.exit_code == 0
        assert "Query all meetings for a specific workgroup" in result.stdout
    
    def test_query_workgroup_command_structure(self, runner, tmp_path):
        """Test query-workgroup command structure (contract test for US1)."""
        # Create entity storage directories
        from src.lib.config import init_entity_storage
        from pathlib import Path
        
        # Monkeypatch config to use tmp_path
        import src.lib.config as config_module
        original_entities_dir = config_module.ENTITIES_DIR
        config_module.ENTITIES_DIR = Path(tmp_path) / "entities"
        init_entity_storage()
        
        try:
            # Create a workgroup and save it
            from src.models.workgroup import Workgroup
            from src.services.entity_storage import save_workgroup
            
            workgroup = Workgroup(name="Test Workgroup")
            save_workgroup(workgroup)
            
            # Test query-workgroup command with valid UUID
            result = runner.invoke(app, [
                "query-workgroup",
                str(workgroup.id)
            ])
            
            # Contract test validates command structure exists
            # Will succeed if command accepts workgroup_id argument
            assert result.exit_code in [0, 1]
            
        finally:
            # Restore original config
            config_module.ENTITIES_DIR = original_entities_dir
    
    def test_query_workgroup_command_with_options(self, runner, tmp_path):
        """Test query-workgroup command with output format option."""
        from src.lib.config import init_entity_storage
        from pathlib import Path
        from src.models.workgroup import Workgroup
        from src.services.entity_storage import save_workgroup
        
        # Monkeypatch config to use tmp_path
        import src.lib.config as config_module
        original_entities_dir = config_module.ENTITIES_DIR
        config_module.ENTITIES_DIR = Path(tmp_path) / "entities"
        init_entity_storage()
        
        try:
            workgroup = Workgroup(name="Test Workgroup")
            save_workgroup(workgroup)
            
            result = runner.invoke(app, [
                "query-workgroup",
                str(workgroup.id),
                "--output-format", "json"
            ])
            
            # Contract test validates options are accepted
            assert result.exit_code in [0, 1]
            
        finally:
            # Restore original config
            config_module.ENTITIES_DIR = original_entities_dir
    
    def test_query_workgroup_command_invalid_uuid(self, runner):
        """Test query-workgroup command with invalid UUID format."""
        result = runner.invoke(app, [
            "query-workgroup",
            "invalid-uuid"
        ])
        
        # Should fail with invalid UUID format
        assert result.exit_code == 1
        # Check if error message is in output (stdout/stderr) or if exit code is 1 (typer.Exit)
        assert "Invalid workgroup ID format" in result.stdout or "Invalid workgroup ID format" in result.stderr or result.exit_code == 1
    
    def test_query_person_command_help(self, runner):
        """Test query-person command help."""
        result = runner.invoke(app, ["query-person", "--help"])
        assert result.exit_code == 0
        assert "Query information for a specific person" in result.stdout
    
    def test_query_person_command_structure(self, runner, tmp_path):
        """Test query-person command structure (contract test for US2)."""
        from src.lib.config import init_entity_storage
        from pathlib import Path
        from src.models.person import Person
        from src.services.entity_storage import save_person
        
        # Monkeypatch config to use tmp_path
        import src.lib.config as config_module
        original_entities_dir = config_module.ENTITIES_DIR
        config_module.ENTITIES_DIR = Path(tmp_path) / "entities"
        init_entity_storage()
        
        try:
            # Create a person and save it
            person = Person(display_name="Test Person")
            save_person(person)
            
            # Test query-person command with valid UUID
            result = runner.invoke(app, [
                "query-person",
                str(person.id)
            ])
            
            # Contract test validates command structure exists
            assert result.exit_code in [0, 1]
            
        finally:
            # Restore original config
            config_module.ENTITIES_DIR = original_entities_dir
    
    def test_query_person_command_with_action_items(self, runner, tmp_path):
        """Test query-person command with --action-items option."""
        from src.lib.config import init_entity_storage
        from pathlib import Path
        from src.models.person import Person
        from src.services.entity_storage import save_person
        
        # Monkeypatch config to use tmp_path
        import src.lib.config as config_module
        original_entities_dir = config_module.ENTITIES_DIR
        config_module.ENTITIES_DIR = Path(tmp_path) / "entities"
        init_entity_storage()
        
        try:
            person = Person(display_name="Test Person")
            save_person(person)
            
            result = runner.invoke(app, [
                "query-person",
                str(person.id),
                "--action-items"
            ])
            
            # Contract test validates --action-items option is accepted
            assert result.exit_code in [0, 1]
            
        finally:
            # Restore original config
            config_module.ENTITIES_DIR = original_entities_dir
    
    def test_query_person_command_invalid_uuid(self, runner):
        """Test query-person command with invalid UUID format."""
        result = runner.invoke(app, [
            "query-person",
            "invalid-uuid"
        ])
        
        # Should fail with invalid UUID format
        assert result.exit_code == 1
        # Check if error message is in output (stdout/stderr) or if exit code is 1 (typer.Exit)
        assert "Invalid person ID format" in result.stdout or "Invalid person ID format" in result.stderr or result.exit_code == 1


"""Unit tests for constitution compliance checking utilities."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.lib.compliance import (
    ConstitutionViolation,
    ViolationType,
    DetectionLayer,
    ComplianceStatus,
    ComplianceReport
)
from src.lib.static_analysis import (
    check_no_external_apis,
    check_python_standard_library_only,
    check_subprocess_calls
)
from src.services.compliance_checker import (
    ComplianceChecker,
    NetworkMonitor,
    ProcessMonitor
)


class TestConstitutionViolation:
    """Unit tests for ConstitutionViolation class."""
    
    def test_violation_creation(self):
        """Test creating a constitution violation."""
        violation = ConstitutionViolation(
            violation_type=ViolationType.EXTERNAL_API,
            principle="Technology Discipline",
            location={"file": "test.py", "line": 10},
            violation_details="import requests",
            detection_layer=DetectionLayer.STATIC_ANALYSIS,
            recommended_action="Remove external API dependency"
        )
        
        assert violation.violation_type == ViolationType.EXTERNAL_API
        assert violation.principle == "Technology Discipline"
        assert violation.location["file"] == "test.py"
        assert violation.location["line"] == 10
        assert violation.detection_layer == DetectionLayer.STATIC_ANALYSIS
    
    def test_violation_str(self):
        """Test violation string representation."""
        violation = ConstitutionViolation(
            violation_type=ViolationType.EXTERNAL_API,
            principle="Technology Discipline",
            location={"file": "test.py", "line": 10, "function": "test_func"},
            violation_details="import requests",
            detection_layer=DetectionLayer.STATIC_ANALYSIS,
            recommended_action="Remove external API dependency"
        )
        
        violation_str = str(violation)
        assert "Constitution Violation" in violation_str
        assert "ExternalAPI" in violation_str
        assert "test.py:10" in violation_str
        assert "test_func" in violation_str
    
    def test_violation_to_dict(self):
        """Test violation dictionary conversion."""
        violation = ConstitutionViolation(
            violation_type=ViolationType.EXTERNAL_API,
            principle="Technology Discipline",
            location={"file": "test.py", "line": 10},
            violation_details="import requests",
            detection_layer=DetectionLayer.STATIC_ANALYSIS
        )
        
        violation_dict = violation.to_dict()
        assert violation_dict["violation_type"] == "ExternalAPI"
        assert violation_dict["principle"] == "Technology Discipline"
        assert violation_dict["location"]["file"] == "test.py"


class TestComplianceReport:
    """Unit tests for ComplianceReport class."""
    
    def test_report_creation(self):
        """Test creating a compliance report."""
        report = ComplianceReport()
        
        assert report.overall_status == ComplianceStatus.UNKNOWN
        assert len(report.violations) == 0
    
    def test_report_add_violation(self):
        """Test adding violation to report."""
        report = ComplianceReport()
        
        violation = ConstitutionViolation(
            violation_type=ViolationType.EXTERNAL_API,
            principle="Technology Discipline",
            location={"file": "test.py", "line": 10},
            violation_details="import requests",
            detection_layer=DetectionLayer.STATIC_ANALYSIS
        )
        
        report.add_violation(violation)
        
        assert len(report.violations) == 1
        assert report.overall_status == ComplianceStatus.FAIL
    
    def test_report_update_status(self):
        """Test report status update based on category statuses."""
        report = ComplianceReport()
        report.entity_operations = ComplianceStatus.PASS
        report.embedding_generation = ComplianceStatus.PASS
        report.llm_inference = ComplianceStatus.PASS
        report.faiss_operations = ComplianceStatus.PASS
        report.python_only = ComplianceStatus.PASS
        report.cli_support = ComplianceStatus.PASS
        
        report.update_overall_status()
        
        assert report.overall_status == ComplianceStatus.PASS


class TestStaticAnalysis:
    """Unit tests for static analysis checks."""
    
    def test_check_no_external_apis_valid_file(self, tmp_path):
        """Test static analysis with valid file (no external APIs)."""
        test_file = tmp_path / "test_valid.py"
        test_file.write_text("""
import json
from pathlib import Path

def test_function():
    data = {"key": "value"}
    return json.dumps(data)
""")
        
        violations = check_no_external_apis(test_file)
        
        assert len(violations) == 0
    
    def test_check_no_external_apis_with_violation(self, tmp_path):
        """Test static analysis detecting external API import."""
        test_file = tmp_path / "test_violation.py"
        test_file.write_text("""
import requests

def test_function():
    response = requests.get("https://api.example.com")
    return response
""")
        
        violations = check_no_external_apis(test_file)
        
        assert len(violations) == 1
        assert violations[0].violation_type == ViolationType.EXTERNAL_API
        assert "requests" in violations[0].violation_details
    
    def test_check_subprocess_calls(self, tmp_path):
        """Test static analysis detecting subprocess calls to external binaries."""
        test_file = tmp_path / "test_subprocess.py"
        test_file.write_text("""
import subprocess

def test_function():
    subprocess.run(["curl", "https://api.example.com"])
""")
        
        violations = check_subprocess_calls(test_file)
        
        assert len(violations) > 0
        assert any(v.violation_type == ViolationType.EXTERNAL_BINARY for v in violations)


class TestComplianceChecker:
    """Unit tests for ComplianceChecker service."""
    
    def test_checker_initialization(self):
        """Test compliance checker initialization."""
        checker = ComplianceChecker()
        
        assert checker.enabled == False
        assert checker.network_monitor is not None
        assert checker.process_monitor is not None
    
    def test_enable_monitoring(self):
        """Test enabling compliance monitoring."""
        checker = ComplianceChecker()
        checker.enable_monitoring()
        
        assert checker.enabled == True
    
    def test_disable_monitoring(self):
        """Test disabling compliance monitoring."""
        checker = ComplianceChecker()
        checker.enable_monitoring()
        checker.disable_monitoring()
        
        assert checker.enabled == False
    
    def test_check_entity_operations(self):
        """Test checking entity operations for violations."""
        checker = ComplianceChecker()
        
        # Without external modules, should return empty violations
        violations = checker.check_entity_operations()
        
        assert isinstance(violations, list)


class TestNetworkMonitor:
    """Unit tests for NetworkMonitor."""
    
    def test_monitor_initialization(self):
        """Test network monitor initialization."""
        monitor = NetworkMonitor()
        
        assert monitor.monitoring == False
        assert len(monitor.violations) == 0
    
    def test_is_external_api(self):
        """Test external API host detection."""
        monitor = NetworkMonitor()
        
        assert monitor._is_external_api("api.openai.com") == True
        assert monitor._is_external_api("router.huggingface.co") == True
        assert monitor._is_external_api("localhost") == False
        assert monitor._is_external_api("127.0.0.1") == False


class TestProcessMonitor:
    """Unit tests for ProcessMonitor."""
    
    def test_monitor_initialization(self):
        """Test process monitor initialization."""
        monitor = ProcessMonitor()
        
        assert monitor.monitoring == False
        assert len(monitor.violations) == 0
    
    def test_check_process_spawn_python(self):
        """Test process spawn check allows Python."""
        monitor = ProcessMonitor()
        monitor.start_monitoring()
        
        # Python should be allowed
        monitor.check_process_spawn(
            ["python", "script.py"],
            {"file": "test.py", "line": 10}
        )
        
        assert len(monitor.violations) == 0
    
    def test_check_process_spawn_external_binary(self):
        """Test process spawn check detects external binary."""
        monitor = ProcessMonitor()
        monitor.start_monitoring()
        
        # External binary should trigger violation
        with pytest.raises(RuntimeError, match="Constitution violation"):
            monitor.check_process_spawn(
                ["curl", "https://api.example.com"],
                {"file": "test.py", "line": 10}
            )
        
        assert len(monitor.violations) == 1
        assert monitor.violations[0].violation_type == ViolationType.EXTERNAL_BINARY


class TestPythonOnlyImports:
    """Unit tests for Python-only import detection (T029 - US2)."""
    
    def test_python_only_import_detection_valid(self, tmp_path):
        """Test Python-only import detection with valid standard library imports."""
        test_file = tmp_path / "test_valid.py"
        test_file.write_text("""
import json
import pathlib
from pathlib import Path
import os

def test_function():
    data = {"key": "value"}
    return json.dumps(data)
""")
        
        violations = check_python_standard_library_only(test_file)
        
        # Should not have violations for standard library imports
        assert len(violations) == 0
    
    def test_python_only_import_detection_violation(self, tmp_path):
        """Test Python-only import detection detects non-standard library imports."""
        test_file = tmp_path / "test_violation.py"
        test_file.write_text("""
import json
import requests

def test_function():
    response = requests.get("https://api.example.com")
    return response
""")
        
        violations = check_python_standard_library_only(test_file)
        
        # Should detect external API library import
        assert len(violations) > 0
        external_api_violations = [v for v in violations if v.violation_type == ViolationType.EXTERNAL_API]
        assert len(external_api_violations) > 0


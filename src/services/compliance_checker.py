"""Runtime compliance checking service for constitution violations."""

import sys
import socket
from typing import List, Callable, Any, Optional, Dict
from functools import wraps
from threading import Lock

from src.lib.compliance import (
    ConstitutionViolation,
    ViolationType,
    DetectionLayer,
    ComplianceStatus,
    ComplianceReport
)
from src.lib.logging import get_logger

logger = get_logger(__name__)

# Singleton instance for ComplianceChecker
_compliance_checker_instance: Optional['ComplianceChecker'] = None
_compliance_checker_lock = Lock()


class NetworkMonitor:
    """Monitor network calls for external API violations."""
    
    def __init__(self):
        self.monitoring = False
        self.violations: List[ConstitutionViolation] = []
        self._original_socket = None
    
    def start_monitoring(self) -> None:
        """Start monitoring network calls."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.violations = []
        
        # Monkey-patch socket to intercept network calls
        self._original_socket = socket.socket
        
        def monitored_socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, fileno=None):
            """Monitored socket wrapper."""
            sock = self._original_socket(family, type, proto, fileno)
            original_connect = sock.connect
            
            def monitored_connect(address):
                """Monitor connect calls."""
                host, port = address[:2] if isinstance(address, tuple) else (address, None)
                
                # Check if connecting to external API
                if self._is_external_api(host):
                    violation = ConstitutionViolation(
                        violation_type=ViolationType.EXTERNAL_API,
                        principle="Technology Discipline - \"Remote embeddings and LLM inference are allowed but must be configured via environment variables\"",
                        location={
                            "file": "runtime",
                            "line": 0,
                            "function": "socket.connect"
                        },
                        violation_details=f"Unauthorized network connection to {host}:{port}",
                        detection_layer=DetectionLayer.RUNTIME,
                        recommended_action="Ensure remote APIs are properly configured via environment variables, or use local models instead."
                    )
                    self.violations.append(violation)
                    logger.error(
                        "constitution_violation_network_call",
                        host=host,
                        port=port,
                        violation_type=ViolationType.EXTERNAL_API.value
                    )
                    raise RuntimeError(f"Constitution violation: External API call to {host}:{port}")
                
                return original_connect(address)
            
            sock.connect = monitored_connect
            return sock
        
        socket.socket = monitored_socket
        logger.debug("network_monitoring_started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring network calls."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        
        # Restore original socket
        if self._original_socket:
            socket.socket = self._original_socket
        
        logger.debug("network_monitoring_stopped", violation_count=len(self.violations))
    
    def _is_external_api(self, host: str) -> bool:
        """Check if host is an external API that's not configured."""
        if not host:
            return False
        
        # Check if remote APIs are configured (per constitution v2.2.0, remote embeddings/LLM are allowed)
        from ..lib.remote_config import (
            get_embedding_remote_config,
            get_llm_remote_config
        )
        
        # Get configured remote API URLs
        emb_enabled, emb_url, _, _ = get_embedding_remote_config()
        llm_enabled, llm_url, _, _ = get_llm_remote_config()
        
        host_lower = host.lower()
        
        # Extract host from URLs for comparison
        configured_hosts = set()
        if emb_enabled and emb_url:
            # Extract host from URL (e.g., "https://api.openai.com/v1" -> "api.openai.com")
            from urllib.parse import urlparse
            try:
                parsed = urlparse(emb_url)
                if parsed.hostname:
                    configured_hosts.add(parsed.hostname.lower())
            except Exception:
                pass
        
        if llm_enabled and llm_url:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(llm_url)
                if parsed.hostname:
                    configured_hosts.add(parsed.hostname.lower())
            except Exception:
                pass
        
        # If this host is configured, it's allowed (not a violation)
        if any(conf_host in host_lower or host_lower in conf_host for conf_host in configured_hosts):
            return False
        
        # Known external API hosts (only flag if not configured)
        external_api_hosts = {
            'api.openai.com',
            'api-inference.huggingface.co',
            'router.huggingface.co',
            'api.anthropic.com',
            'api.cohere.ai',
            'api.sapling.ai'
        }
        
        # Check if host matches or contains external API domains
        for api_host in external_api_hosts:
            if api_host in host_lower:
                return True
        
        # Check for common API patterns (only flag if not configured)
        if any(pattern in host_lower for pattern in ['api.', '.api.', '-api.', 'api-']):
            return True
        
        return False
    
    def get_violations(self) -> List[ConstitutionViolation]:
        """Get detected violations."""
        return self.violations.copy()


class ProcessMonitor:
    """Monitor process spawns for external binary violations."""
    
    def __init__(self):
        self.monitoring = False
        self.violations: List[ConstitutionViolation] = []
    
    def start_monitoring(self) -> None:
        """Start monitoring process spawns."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.violations = []
        logger.debug("process_monitoring_started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring process spawns."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        logger.debug("process_monitoring_stopped", violation_count=len(self.violations))
    
    def check_process_spawn(self, command: List[str], location: Dict[str, Any]) -> None:
        """Check if process spawn is a violation."""
        if not command:
            return
        
        binary_name = command[0]
        
        # Python is allowed
        if binary_name in ('python', 'python3', 'python2'):
            return
        
        # External binary detected
        violation = ConstitutionViolation(
            violation_type=ViolationType.EXTERNAL_BINARY,
            principle="Technology Discipline - \"Python-only execution environment\"",
            location=location,
            violation_details=f"subprocess execution: {' '.join(command)}",
            detection_layer=DetectionLayer.RUNTIME,
            recommended_action="Use Python standard library or Python packages instead of external binaries."
        )
        self.violations.append(violation)
        logger.error(
            "constitution_violation_external_binary",
            binary=binary_name,
            command=command,
            violation_type=ViolationType.EXTERNAL_BINARY.value
        )
        raise RuntimeError(f"Constitution violation: External binary execution: {binary_name}")
    
    def get_violations(self) -> List[ConstitutionViolation]:
        """Get detected violations."""
        return self.violations.copy()


class ComplianceChecker:
    """Runtime compliance checking service."""
    
    def __init__(self):
        self.network_monitor = NetworkMonitor()
        self.process_monitor = ProcessMonitor()
        self.enabled = False
    
    def enable_monitoring(self) -> None:
        """Enable compliance monitoring."""
        if self.enabled:
            return
        
        self.enabled = True
        self.network_monitor.start_monitoring()
        self.process_monitor.start_monitoring()
        logger.info("compliance_monitoring_enabled")
    
    def disable_monitoring(self) -> None:
        """Disable compliance monitoring."""
        if not self.enabled:
            return
        
        self.enabled = False
        self.network_monitor.stop_monitoring()
        self.process_monitor.stop_monitoring()
        logger.info("compliance_monitoring_disabled")
    
    def monitor_operation(self, operation: Callable) -> Callable:
        """
        Wrap operation with compliance monitoring (T065 - Phase 7).
        
        Performance optimization: Only enable monitoring when explicitly requested.
        """
        @wraps(operation)
        def wrapper(*args, **kwargs):
            if not self.enabled:
                # Performance optimization: Skip monitoring when disabled (T065 - Phase 7)
                return operation(*args, **kwargs)
            
            # Start monitoring for this operation
            self.network_monitor.start_monitoring()
            try:
                result = operation(*args, **kwargs)
                violations = self.network_monitor.get_violations()
                if violations:
                    # First violation triggers fail-fast
                    raise violations[0]
                return result
            finally:
                # Always stop monitoring to minimize overhead (T065 - Phase 7)
                self.network_monitor.stop_monitoring()
        
        return wrapper
    
    def check_entity_operations(self) -> List[ConstitutionViolation]:
        """Check entity operations for compliance violations."""
        violations = []
        
        try:
            # Check if remote processing is configured (per constitution v2.2.0, remote embeddings/LLM are allowed)
            from ..lib.remote_config import (
                get_embedding_remote_config,
                get_llm_remote_config
            )
            
            # Get configured remote API settings
            emb_enabled, emb_url, _, _ = get_embedding_remote_config()
            llm_enabled, llm_url, _, _ = get_llm_remote_config()
            
            # Remote processing is allowed when properly configured
            remote_processing_enabled = (emb_enabled and emb_url) or (llm_enabled and llm_url)
            
            # Check for external API modules loaded at runtime
            # Only flag as violations if remote processing is NOT configured
            # (These modules are legitimate when remote processing is enabled)
            external_modules = {'requests', 'openai', 'httpx', 'urllib3'}
            for module_name in external_modules:
                if module_name in sys.modules:
                    if not remote_processing_enabled:
                        # Remote processing not configured - flag as violation
                        violation = ConstitutionViolation(
                            violation_type=ViolationType.EXTERNAL_API,
                            principle="Technology Discipline - \"No external API dependency for core functionality\"",
                            location={
                                "file": "runtime",
                                "module": module_name
                            },
                            violation_details=f"External API module loaded: {module_name}",
                            detection_layer=DetectionLayer.RUNTIME,
                            recommended_action=f"Remove dependency on {module_name}. Use local models instead, or configure remote processing via environment variables."
                        )
                        violations.append(violation)
                    # If remote_processing_enabled, these modules are allowed (no violation)
            
            # Add network monitor violations (network monitor will check for unauthorized connections)
            violations.extend(self.network_monitor.get_violations())
        except Exception as e:
            # Error handling and recovery for compliance check failures (T066 - Phase 7)
            from src.lib.compliance import handle_compliance_check_error
            handle_compliance_check_error(e, {"operation": "check_entity_operations"})
            # Re-raise to maintain fail-fast behavior
            raise
        
        return violations
    
    def check_embedding_operations(self) -> List[ConstitutionViolation]:
        """Check embedding operations for compliance violations."""
        violations = []
        
        # Remote embeddings are now allowed per constitution v2.2.0
        # No longer flagging remote embedding service usage or network calls as violations
        # Network calls to configured remote embedding APIs are explicitly allowed
        
        # Network monitor violations are not included here since remote embeddings are allowed
        # (Network monitoring may still run but violations are not raised for embedding operations)
        
        return violations
    
    def check_llm_operations(self) -> List[ConstitutionViolation]:
        """Check LLM inference operations for compliance violations."""
        violations = []
        
        # Remote LLM inference is now allowed per constitution v2.2.0
        # No longer flagging remote LLM service usage or network calls as violations
        # Network calls to configured remote LLM APIs are explicitly allowed
        
        # Network monitor violations are not included here since remote LLM is allowed
        # (Network monitoring may still run but violations are not raised for LLM operations)
        
        return violations
    
    def check_faiss_operations(self) -> List[ConstitutionViolation]:
        """Check FAISS operations for compliance violations (T042 - US3)."""
        violations = []
        
        # Check for remote vector database modules
        remote_vector_dbs = {'pinecone', 'weaviate', 'milvus', 'qdrant', 'chromadb'}
        for db_name in remote_vector_dbs:
            if db_name in sys.modules:
                violation = ConstitutionViolation(
                    violation_type=ViolationType.REMOTE_STORAGE,
                    principle="Technology Discipline - \"FAISS vector storage remains local for performance and determinism\"",
                    location={
                        "file": "runtime",
                        "module": db_name
                    },
                    violation_details=f"Remote vector database module loaded: {db_name}",
                    detection_layer=DetectionLayer.RUNTIME,
                    recommended_action=f"Use local FAISS storage instead of {db_name}."
                )
                violations.append(violation)
        
        # Add network monitor violations
        violations.extend(self.network_monitor.get_violations())
        
        return violations
    
    def verify_faiss_index_local_only(self, index_path: str) -> List[ConstitutionViolation]:
        """
        Verify that FAISS indexes are stored locally only (T043 - US3).
        
        Args:
            index_path: Path to FAISS index file
            
        Returns:
            List of detected violations
        """
        violations = []
        from pathlib import Path
        
        # Convert to Path object
        path = Path(index_path)
        
        # Check if path is absolute local path
        if path.is_absolute():
            # Local absolute path is OK
            if not path.exists() or not path.is_file():
                # Path doesn't exist or is not a file - might be remote
                # This is a conservative check - actual file system paths are local
                pass
        elif path.is_relative_to(Path.cwd()):
            # Relative path within current directory is OK
            pass
        elif 'http' in str(path).lower() or 's3://' in str(path).lower() or 'gs://' in str(path).lower():
            # Remote storage URL detected
            violation = ConstitutionViolation(
                violation_type=ViolationType.REMOTE_STORAGE,
                principle="Technology Discipline - \"Local embeddings + FAISS storage\"",
                location={
                    "file": "runtime",
                    "index_path": str(path)
                },
                violation_details=f"Remote storage path detected: {index_path}",
                detection_layer=DetectionLayer.RUNTIME,
                recommended_action=f"Use local file path instead of remote storage: {index_path}"
            )
            violations.append(violation)
        
        return violations
    
    def check_python_only(self) -> List[ConstitutionViolation]:
        """Check Python-only requirement compliance."""
        violations = []
        
        # Add process monitor violations
        violations.extend(self.process_monitor.get_violations())
        
        return violations
    
    def verify_python_standard_library_only(self, module_names: List[str]) -> List[ConstitutionViolation]:
        """
        Verify that entity operations use only Python standard library (json, pathlib) (T036 - US2).
        
        Args:
            module_names: List of module names used in operations
            
        Returns:
            List of detected violations
        """
        violations = []
        import sys
        
        # Python standard library modules (core set for entity operations)
        allowed_stdlib_modules = {
            'json', 'pathlib', 'os', 'sys', 'shutil', 'uuid', 'datetime',
            'typing', 'dataclasses', 'enum', 'collections', 'abc', 'functools',
            'inspect', 'importlib', 'itertools', 'operator', 'copy', 'pickle'
        }
        
        # Get actual standard library modules if available
        stdlib_modules = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else allowed_stdlib_modules
        
        for module_name in module_names:
            # Extract base module name
            base_module = module_name.split('.')[0]
            
            # Check if module is in standard library
            if base_module not in stdlib_modules and base_module not in allowed_stdlib_modules:
                # Check if it's a project module (src.*)
                if not base_module.startswith('src'):
                    violation = ConstitutionViolation(
                        violation_type=ViolationType.NON_PYTHON_DEPENDENCY,
                        principle="Technology Discipline - \"Python-only execution environment\"",
                        location={
                            "file": "runtime",
                            "module": module_name
                        },
                        violation_details=f"Non-standard library module used: {module_name}",
                        detection_layer=DetectionLayer.RUNTIME,
                        recommended_action=f"Use Python standard library or project modules (src.*) instead of {module_name}."
                    )
                    violations.append(violation)
        
        return violations
    
    def get_violations(self) -> List[ConstitutionViolation]:
        """Get all detected violations."""
        violations = []
        violations.extend(self.network_monitor.get_violations())
        violations.extend(self.process_monitor.get_violations())
        return violations


def get_compliance_checker() -> ComplianceChecker:
    """
    Get the singleton ComplianceChecker instance.
    
    This ensures all services share the same compliance checker instance,
    preventing conflicts with socket monkey-patching and network monitoring.
    
    Returns:
        The singleton ComplianceChecker instance
    """
    global _compliance_checker_instance
    
    # Double-checked locking pattern for thread-safe singleton
    if _compliance_checker_instance is None:
        with _compliance_checker_lock:
            if _compliance_checker_instance is None:
                _compliance_checker_instance = ComplianceChecker()
                logger.debug("compliance_checker_singleton_created")
    
    return _compliance_checker_instance


def reset_compliance_checker() -> None:
    """
    Reset the singleton ComplianceChecker instance (for testing).
    
    This is useful for testing to ensure clean state between tests.
    """
    global _compliance_checker_instance
    
    with _compliance_checker_lock:
        if _compliance_checker_instance is not None:
            # Disable monitoring and restore socket before resetting
            if _compliance_checker_instance.enabled:
                _compliance_checker_instance.disable_monitoring()
            _compliance_checker_instance = None
            logger.debug("compliance_checker_singleton_reset")


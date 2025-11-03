# Research: Constitution Compliance

**Feature**: Constitution Compliance  
**Date**: 2025-11-02  
**Purpose**: Resolve technical decisions for constitution compliance verification implementation

## Key Research Questions

### 1. Compliance Detection Strategy: Static Analysis vs Runtime Checks

**Decision Required**: How to detect constitution violations (external API calls, non-Python dependencies) in codebase

**Research Context**: 
- Requirement: Multiple-layer compliance checks (automated tests, runtime checks, manual verification)
- Need to detect: External API calls, non-local embeddings, non-local LLM inference, external binaries
- Constraints: Python-only tools, minimal performance overhead, clear violation reporting

**Decision**: **Hybrid Approach - Static Analysis + Runtime Monitoring + Test Coverage**

**Rationale**: 
- Static analysis provides:
  - Early detection during development (before code runs)
  - Fast checking (AST parsing is lightweight)
  - Coverage of entire codebase
  - Integration with CI/CD pipelines
  - Clear reporting of violations with file/line numbers
- Runtime monitoring provides:
  - Detection of dynamic violations (imports at runtime, conditional API calls)
  - Real-world validation during execution
  - Network monitoring for HTTP requests
  - Process monitoring for external binaries
- Test coverage provides:
  - Automated verification during development
  - Regression prevention
  - Integration with existing pytest framework
  - Measurable compliance metrics

**Implementation Pattern**:
- **Static Analysis**: Use Python `ast` module to parse source code, detect imports of `requests`, `openai`, `httpx` (external API libraries), check for HTTP URLs in code
- **Runtime Checks**: Monkey-patch or wrap network libraries to detect API calls, check `sys.modules` for external API libraries loaded at runtime
- **Test Coverage**: Unit tests mock external API calls and verify they fail, integration tests verify local-only operations succeed

**Alternatives Considered**:
1. **Static Analysis Only** ❌ Rejected - Misses runtime violations, dynamic imports
2. **Runtime Monitoring Only** ❌ Rejected - Slower feedback, harder to catch violations before deployment
3. **Test Coverage Only** ❌ Rejected - Requires comprehensive test coverage, misses untested code paths
4. **Hybrid Approach** ✅ Selected - Best coverage, early detection, runtime validation, testable

---

### 2. Violation Handling: Fail-Fast vs Warning

**Decision Required**: What should happen when constitution violations are detected?

**Research Context**: 
- Requirement: "System MUST fail gracefully with clear error messages if external dependencies are detected"
- Need to balance: User experience (clear errors) vs system availability
- Constraints: No silent fallbacks, clear violation reporting

**Decision**: **Fail-Fast with Clear Error Messages**

**Rationale**: 
- Fail-fast provides:
  - Immediate feedback on violations
  - Prevents silent fallbacks to external services
  - Clear error messages guide developers to fix issues
  - Maintains constitution compliance guarantees
- Clear error messages provide:
  - Specific violation details (what was detected, where, when)
  - Actionable guidance (how to fix)
  - Context (which constitution principle was violated)
- Graceful failure provides:
  - Clean error state (no partial operations)
  - Proper cleanup (no orphaned resources)
  - Audit trail (violation logged)

**Error Message Format**:
```
Constitution Violation: External API call detected
  Principle: Technology Discipline - "No external API dependency for core functionality"
  Location: src/services/embedding.py:45
  Violation: requests.post() call to https://api.openai.com/v1/embeddings
  Action: Use local embedding model instead of remote API
```

**Alternatives Considered**:
1. **Warning Only** ❌ Rejected - Allows violations, violates constitution requirement
2. **Silent Logging** ❌ Rejected - No user feedback, violates "fail gracefully" requirement
3. **Fail-Fast** ✅ Selected - Enforces compliance, clear feedback, maintains constitution guarantees

---

### 3. Python-Only Verification: Dependency Checking

**Decision Required**: How to verify that only Python standard library and Python packages are used (no external binaries)?

**Research Context**: 
- Requirement: "System MUST use only Python standard library and Python packages (no external binaries beyond Python runtime)"
- Need to detect: System-level binaries, native libraries, external executables
- Constraints: Python-only verification tools

**Decision**: **Import Analysis + Process Monitoring**

**Rationale**: 
- Import analysis provides:
  - Detection of non-Python dependencies in source code
  - Verification of standard library usage
  - Check for subprocess/exec calls to external binaries
  - Integration with static analysis
- Process monitoring provides:
  - Runtime detection of external process spawns
  - Validation that no external binaries are executed
  - Monitoring of subprocess calls
- Dependency checking provides:
  - Verification of installed packages (pure Python vs compiled extensions)
  - Check for system-level binary dependencies
  - Validation of package requirements

**Implementation Pattern**:
- Check imports against Python standard library list
- Detect `subprocess`, `os.system()`, `os.exec*()` calls (flag for review)
- Monitor `subprocess.Popen()` calls at runtime
- Verify installed packages are pure Python or Python wheels (not system binaries)

**Alternatives Considered**:
1. **Import Analysis Only** ❌ Rejected - Misses runtime subprocess calls
2. **Process Monitoring Only** ❌ Rejected - Slower feedback, harder to prevent violations
3. **Import Analysis + Process Monitoring** ✅ Selected - Comprehensive coverage, early detection, runtime validation

---

### 4. Compliance Test Strategy: Unit vs Integration vs Contract Tests

**Decision Required**: What types of tests are needed for constitution compliance verification?

**Research Context**: 
- Requirement: Multiple-layer compliance checks including automated tests
- Need to cover: Development-time detection, runtime violation detection, manual verification
- Constraints: Existing pytest framework, test-first governance principle

**Decision**: **Multi-Layer Test Strategy - Unit + Integration + Contract Tests**

**Rationale**: 
- Unit tests provide:
  - Fast feedback on compliance check logic
  - Isolated testing of static analysis utilities
  - Verification of violation detection logic
  - Test compliance checkers themselves
- Integration tests provide:
  - End-to-end compliance verification
  - Real-world scenario testing
  - Validation that entity operations are compliant
  - Detection of violations in actual workflows
- Contract tests provide:
  - CLI command compliance verification
  - API contract validation (no external dependencies)
  - User-facing compliance checks
  - Integration with existing contract test framework

**Test Coverage Targets**:
- Unit tests: Compliance checking utilities, static analysis tools (90%+ coverage)
- Integration tests: Entity operations, embedding operations, LLM inference (all major operations)
- Contract tests: CLI commands, API contracts (all public interfaces)

**Alternatives Considered**:
1. **Unit Tests Only** ❌ Rejected - Misses integration violations, no end-to-end verification
2. **Integration Tests Only** ❌ Rejected - Slower feedback, harder to isolate violations
3. **Contract Tests Only** ❌ Rejected - Misses internal violations, incomplete coverage
4. **Multi-Layer Strategy** ✅ Selected - Comprehensive coverage, fast feedback, end-to-end validation

---

### 5. Manual Verification: Code Review vs Automated Audit

**Decision Required**: How to implement manual verification layer for constitution compliance?

**Research Context**: 
- Requirement: Manual verification confirms compliance through code review and audit processes
- Need to support: Code review checklists, audit reports, compliance documentation
- Constraints: Human-readable reports, actionable findings

**Decision**: **Automated Audit Reports + Code Review Checklists**

**Rationale**: 
- Automated audit reports provide:
  - Comprehensive compliance status overview
  - Violation summary with details
  - Compliance metrics (percentage compliant)
  - Historical tracking of compliance status
- Code review checklists provide:
  - Manual verification of compliance
  - Human review of automated findings
  - Documentation of compliance decisions
  - Integration with PR review process

**Implementation Pattern**:
- Generate compliance audit reports (JSON + human-readable)
- Provide code review checklist (markdown with automated findings)
- Integration with PR comments (automated compliance checks)
- Compliance dashboard (summary of all compliance checks)

**Alternatives Considered**:
1. **Code Review Only** ❌ Rejected - Manual-only, no automated reporting, inconsistent
2. **Automated Audit Only** ❌ Rejected - Misses human judgment, no documentation
3. **Automated Audit + Code Review** ✅ Selected - Comprehensive, automated + human verification, documented

---

## Implementation Patterns

### Compliance Check Pattern

```python
# Static analysis check
def check_no_external_apis(file_path: Path) -> List[Violation]:
    """Check source file for external API imports/calls."""
    # Parse AST, detect requests/openai imports
    # Return violations with line numbers

# Runtime check
class ComplianceMonitor:
    """Monitor runtime operations for compliance violations."""
    def check_api_call(self, url: str) -> None:
        if not self.is_local(url):
            raise ConstitutionViolation(...)
```

### Violation Detection Pattern

```python
# Test pattern
def test_entity_storage_no_external_apis():
    """Verify entity storage doesn't use external APIs."""
    # Mock external API calls
    # Verify they fail with constitution violation
    # Verify local operations succeed
```

---

## Summary

All research questions resolved with clear decisions and rationales:
1. ✅ Compliance Detection: Hybrid approach (static analysis + runtime monitoring + tests)
2. ✅ Violation Handling: Fail-fast with clear error messages
3. ✅ Python-Only Verification: Import analysis + process monitoring
4. ✅ Compliance Test Strategy: Multi-layer (unit + integration + contract tests)
5. ✅ Manual Verification: Automated audit reports + code review checklists

All decisions align with constitution requirements and existing project constraints.


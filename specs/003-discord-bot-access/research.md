# Research: Discord Bot Interface for Archive-RAG

**Created**: 2025-01-27  
**Feature**: Discord Bot Interface for Archive-RAG  
**Plan**: [plan.md](./plan.md)

## Research Tasks

### 1. Discord Bot Library Selection: discord.py

**Decision Required**: Which Python library to use for Discord bot implementation?

**Research Context**: 
- Requirement: Python-only implementation (constitution constraint)
- Need: Slash command support, role-based permissions, message handling
- Constraints: Must support async operations, rate limiting, error handling

**Decision**: **discord.py (v2.3.0+)**

**Rationale**: 
- Official and widely-used Python Discord API library
- Full support for Discord slash commands (Application Commands)
- Built-in async/await support (asyncio-compatible)
- Role-based permission checking built-in
- Well-documented with active community
- Supports message splitting and formatting
- Compatible with existing Python 3.11+ requirements

**Alternatives Considered**:
1. **discord.py-interactions** ❌ Rejected - Less mature, fewer features
2. **nextcord** (discord.py fork) ❌ Rejected - Discord.py is sufficient, no need for fork
3. **discord.py** ✅ Selected - Official, mature, feature-complete

**Implementation Pattern**:
- Use `discord.Client` or `commands.Bot` for bot initialization
- Use `@app_commands.command()` decorator for slash commands
- Use `app_commands.checks.has_any_role()` for role-based access control
- Use `asyncio` for concurrent request handling

---

### 2. Rate Limiting Strategy: In-Memory Token Bucket

**Decision Required**: How to implement per-user rate limiting (10 queries per minute)?

**Research Context**: 
- Requirement: FR-010 - 10 queries per minute per user
- Constraint: Python-only, no external dependencies for MVP
- Scale: 100 concurrent users (SC-005)
- Need: Fast lookups, automatic cleanup of expired entries

**Decision**: **In-Memory Token Bucket with Time-Window Tracking**

**Rationale**: 
- Simple implementation using Python `dict` and `collections.deque`
- No external dependencies (constitution-compliant)
- Fast O(1) lookups for rate limit checks
- Automatic cleanup of expired entries using background task
- Sufficient for single-server deployment (100 concurrent users)
- Can be extended to Redis/persistent storage later if needed

**Implementation Pattern**:
```python
# Token bucket per user
user_rate_limits: Dict[str, deque] = {}

# Check rate limit: append current timestamp, remove old timestamps
# If len(deque) >= limit (10), reject request
# Background task cleans up old entries every minute
```

**Alternatives Considered**:
1. **Redis-based rate limiting** ❌ Rejected - External dependency, not needed for MVP scale
2. **Database-backed rate limiting** ❌ Rejected - Overkill for single-server deployment
3. **In-memory token bucket** ✅ Selected - Simple, fast, sufficient for requirements

---

### 3. Message Splitting for Long Responses

**Decision Required**: How to split responses exceeding 2000 characters?

**Research Context**: 
- Requirement: FR-012 - Split into multiple messages, answer first, then citations
- Discord limit: 2000 characters per message
- Need: Preserve formatting, maintain readability, handle citations separately

**Decision**: **Chunked Message Sending with Smart Splitting**

**Rationale**: 
- Discord.py supports sending multiple messages sequentially
- Split at word boundaries to preserve readability
- Separate answer and citations into different messages as specified
- Use Discord embeds for better formatting (optional enhancement)
- Simple implementation: split text, send sequentially with delays to avoid rate limits

**Implementation Pattern**:
```python
# Split answer into chunks of max 1900 chars (safety margin)
# Send answer chunks first
# Then send citation chunks separately
# Use asyncio.sleep() between messages to respect Discord rate limits
```

**Alternatives Considered**:
1. **Discord embeds only** ❌ Rejected - Embed limits (2000 chars total across all fields) too restrictive
2. **File upload for long responses** ❌ Rejected - Poor UX, not specified in requirements
3. **Chunked message sending** ✅ Selected - Simple, meets requirements, good UX

---

### 4. Integration with Existing RAG Services

**Decision Required**: How to integrate Discord bot with existing QueryService and entity services?

**Research Context**: 
- Requirement: FR-002 - Call local RAG inference pipeline
- Existing services: QueryService, EntityQueryService, AuditWriter
- Constraint: Must not modify core RAG services
- Need: Async-friendly interface, error handling, timeout management

**Decision**: **Wrapper Service with Async Bridge**

**Rationale**: 
- Existing QueryService is synchronous (uses blocking I/O)
- Discord bot requires async operations
- Use `asyncio.to_thread()` or `run_in_executor()` to bridge sync/async
- Create bot-specific service wrapper that handles timeouts and errors
- Reuse existing services without modification

**Implementation Pattern**:
```python
# Bot service wrapper
class BotQueryService:
    def __init__(self):
        self.query_service = create_query_service()
    
    async def execute_query_async(self, query_text: str, ...):
        # Run sync QueryService in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self.query_service.execute_query,
            index_name, query_text, ...
        )
        return result
```

**Alternatives Considered**:
1. **Refactor QueryService to async** ❌ Rejected - Too invasive, violates "no modifications to core services" constraint
2. **Separate async RAG service** ❌ Rejected - Code duplication, maintenance burden
3. **Async bridge wrapper** ✅ Selected - Non-invasive, reuses existing code, maintains separation

---

### 5. Error Handling and User Feedback

**Decision Required**: How to handle errors and provide user feedback during processing?

**Research Context**: 
- Requirement: FR-008 - Graceful error handling, FR-013 - Immediate acknowledgment
- Need: User-friendly error messages, timeout handling, RAG pipeline unavailability
- Constraint: Must maintain audit logging even on errors

**Decision**: **Layered Error Handling with User-Friendly Messages**

**Rationale**: 
- Use try/except blocks at multiple levels (command handler, service wrapper, RAG service)
- Map technical errors to user-friendly messages
- Always send acknowledgment immediately (FR-013)
- Log errors to audit logs before sending user response
- Use Discord's error response format for slash commands

**Implementation Pattern**:
```python
# Command handler
try:
    # Send acknowledgment
    await interaction.response.send_message("Processing your query...")
    
    # Execute query (async)
    result = await bot_service.execute_query_async(...)
    
    # Format and send response
    await send_formatted_response(interaction, result)
except RAGPipelineUnavailable:
    await interaction.followup.send("RAG service temporarily unavailable. Please try again later.")
except RateLimitExceeded:
    await interaction.followup.send(f"Rate limit exceeded. Please wait {remaining_time}s.")
except Exception as e:
    logger.error("unexpected_error", error=str(e))
    await interaction.followup.send("An error occurred. Please try again or contact an admin.")
```

**Alternatives Considered**:
1. **Silent error logging only** ❌ Rejected - Violates FR-008 (user-friendly messages)
2. **Technical error messages** ❌ Rejected - Poor UX, violates FR-008
3. **Layered error handling with user-friendly messages** ✅ Selected - Meets all requirements

---

## Summary

All research decisions made. No NEEDS CLARIFICATION markers remain in Technical Context. Ready to proceed to Phase 1: Design & Contracts.



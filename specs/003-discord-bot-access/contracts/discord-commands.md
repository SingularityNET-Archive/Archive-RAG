# Discord Bot Commands Contract

**Created**: 2025-01-27  
**Feature**: Discord Bot Interface for Archive-RAG

## Discord Slash Commands Interface

All commands are Discord Application Commands (slash commands) implemented using discord.py library.

### Base Command Group: `/archive`

All commands are subcommands of `/archive`:

```
/archive [COMMAND] [OPTIONS] [ARGS]
```

---

## Command: `/archive query`

**Purpose**: Execute a natural language query against the Archive-RAG system.

**Usage**:
```
/archive query query:"What decisions were made last January?"
```

**Parameters**:
- `query` (string, required): Natural language question about archived meetings

**Access Control**: 
- **Public**: All users can execute this command (FR-006)

**Rate Limiting**: 
- Per-user limit: 10 queries per minute (FR-010)

**Behavior**:
1. Bot sends immediate acknowledgment: "Processing your query..." (FR-013)
2. Validate user permissions (public access - always allowed)
3. Check rate limit for user (FR-010)
4. Call QueryService.execute_query() with query text
5. Format RAGQuery result for Discord:
   - Answer text
   - Citations in format `[meeting_id | date | speaker]`
   - Links to full meeting records
6. Split response if exceeds 2000 characters (FR-012):
   - Send answer first
   - Send citations in follow-up message(s)
7. Log query to ArchiveQueryLog (FR-005, SC-006)

**Response Format**:
```
Answer: [RAG-generated answer text]

Citations:
[meeting_id | date | speaker]
[meeting_id | date | speaker]
...

View full meeting record: [link]
```

**Error Responses**:
- Rate limit exceeded: "Rate limit exceeded. Please wait {remaining_time}s."
- RAG pipeline unavailable: "RAG service temporarily unavailable. Please try again later."
- No evidence found: "No relevant archive data found. [helpful suggestions]"
- Generic error: "An error occurred. Please try again or contact an admin."

**Examples**:
```
/archive query query:"What is the tag taxonomy?"
/archive query query:"What decisions were made about budget allocation in Q2 2024?"
```

---

## Command: `/archive topics`

**Purpose**: Search for topics/tags in archived meetings.

**Usage**:
```
/archive topics topic:"RAG ethics"
```

**Parameters**:
- `topic` (string, required): Topic or tag name to search for

**Access Control**: 
- **Contributor+**: Only users with "contributor" or "admin" role can execute (FR-006)

**Rate Limiting**: 
- Per-user limit: 10 queries per minute (FR-010)

**Behavior**:
1. Bot sends immediate acknowledgment: "Processing your topic search..."
2. Validate user permissions (contributor or admin role required)
3. Check rate limit for user
4. Call EntityQueryService to find matching tags/topics
5. Retrieve top 5 references with timestamps and links
6. Format results for Discord
7. Log query to ArchiveQueryLog

**Response Format**:
```
Topic: [topic name]

References:
1. [meeting_id | date | speaker] - [excerpt]
2. [meeting_id | date | speaker] - [excerpt]
...
(Showing top 5 results)
```

**Error Responses**:
- Permission denied: "This command requires contributor role. Contact an admin if you need access."
- No topics found: "No topics found matching '{topic}'. Try a different search term."
- Rate limit exceeded: "Rate limit exceeded. Please wait {remaining_time}s."

**Examples**:
```
/archive topics topic:"RAG ethics"
/archive topics topic:"governance"
```

---

## Command: `/archive people`

**Purpose**: Search for people/participants in archived meetings.

**Usage**:
```
/archive people person:"Gorga"
```

**Parameters**:
- `person` (string, required): Person name to search for

**Access Control**: 
- **Contributor+**: Only users with "contributor" or "admin" role can execute (FR-006)

**Rate Limiting**: 
- Per-user limit: 10 queries per minute (FR-010)

**Behavior**:
1. Bot sends immediate acknowledgment: "Processing your people search..."
2. Validate user permissions (contributor or admin role required)
3. Check rate limit for user
4. Call EntityQueryService to find matching people
5. Retrieve mentions, links, and context excerpts
6. Format results for Discord
7. Log query to ArchiveQueryLog

**Response Format**:
```
Person: [person name]

Mentions:
1. [meeting_id | date] - [context excerpt]
2. [meeting_id | date] - [context excerpt]
...

View person profile: [link]
```

**Error Responses**:
- Permission denied: "This command requires contributor role. Contact an admin if you need access."
- No people found: "No people found matching '{person}'. Try a different search term."
- Rate limit exceeded: "Rate limit exceeded. Please wait {remaining_time}s."

**Examples**:
```
/archive people person:"Gorga"
/archive people person:"John Doe"
```

---

## Command: `/archive stats` (Admin Only - Future)

**Purpose**: View bot usage statistics and manage rate limits (admin monitoring).

**Usage**:
```
/archive stats [action:"view"|"rate-limit"]
```

**Parameters**:
- `action` (string, optional): Action to perform (default: "view")
  - "view": Display usage statistics
  - "rate-limit": Manage rate limits (future)

**Access Control**: 
- **Admin**: Only users with "admin" role can execute (FR-011)

**Rate Limiting**: 
- Per-user limit: 10 queries per minute (FR-010)

**Behavior**:
1. Validate user permissions (admin role required)
2. Retrieve usage statistics from audit logs
3. Format statistics for Discord
4. Display: total queries, active users, rate limit status, etc.

**Response Format**:
```
Bot Statistics:
- Total queries: [count]
- Active users (last hour): [count]
- Rate limit status: [status]
- Average response time: [time]ms
```

**Error Responses**:
- Permission denied: "This command requires admin role."

**Note**: This command is planned for future implementation (FR-011). Not required for MVP.

---

## Common Response Patterns

### Success Response Pattern
```
[Immediate acknowledgment]
↓
[Processing...]
↓
[Answer/Citations]
```

### Error Response Pattern
```
[Immediate acknowledgment]
↓
[Error message with user-friendly description]
```

### Rate Limit Response Pattern
```
[Immediate acknowledgment]
↓
[Rate limit error with remaining time]
```

---

## Rate Limiting Contract

**Per-User Limits**:
- Maximum queries: 10 per minute per user
- Window: 60 seconds (rolling window)
- Tracking: In-memory deque of timestamps per user

**Rate Limit Response**:
- HTTP Status: 429 (Too Many Requests) - handled by Discord API
- Bot Response: "Rate limit exceeded. Please wait {remaining_time}s."
- Remaining time: Calculated from oldest timestamp in window

---

## Permission Contract

**Role Hierarchy**:
1. **Public** (default): Access to `/archive query` only
2. **Contributor**: Access to `/archive query`, `/archive topics`, `/archive people`
3. **Admin**: All contributor access + `/archive stats` (future)

**Permission Check Flow**:
1. Extract user roles from Discord interaction
2. Check if user has required role for command
3. If not authorized, return permission error immediately
4. If authorized, proceed with command execution

---

## Audit Logging Contract

**All Commands Must Log**:
- Query ID (UUID)
- Discord user ID and username
- Command name and parameters
- Timestamp
- Response hash (SHA-256)
- Citations (if applicable)
- Execution time
- Error status (if applicable)

**Log Format**: JSON files in `audit_logs/` directory (existing AuditWriter)

**Log Retention**: Follows existing audit log retention policy

---

## Notes

- All commands use Discord's Application Commands (slash commands) API
- Commands are registered with Discord on bot startup
- Command responses respect Discord's 2000 character limit per message
- Long responses are split into multiple messages (FR-012)
- All commands are logged for compliance (SC-006)



# Data Model: Discord Bot Interface for Archive-RAG

**Created**: 2025-01-27  
**Feature**: Discord Bot Interface for Archive-RAG

## Entities

### DiscordUser

**Description**: Represents a Discord user accessing the bot with their roles and permissions.

**Fields**:
- `user_id` (string, required): Discord user ID (Discord snowflake)
- `username` (string, required): Discord username
- `roles` (list[string], required): List of Discord role names (e.g., ["public", "contributor", "admin"])
- `is_public` (boolean, computed): True if user has no special roles (default access)
- `is_contributor` (boolean, computed): True if user has "contributor" role
- `is_admin` (boolean, computed): True if user has "admin" role

**Validation Rules**:
- `user_id` must be a valid Discord snowflake (numeric string)
- `username` must not be empty
- `roles` list determines access permissions (FR-006, FR-011)

**Relationships**:
- One-to-many: One DiscordUser can have multiple ArchiveQueryLog entries

**State Transitions**:
1. **Initialized**: User object created from Discord interaction
2. **Validated**: Permissions checked against role list
3. **Active**: User can execute commands based on role

---

### ArchiveQueryLog

**Description**: Represents a logged query executed through the Discord bot with complete audit trail.

**Fields**:
- `query_id` (string, required): Unique query identifier (UUID)
- `discord_user_id` (string, required): Discord user ID who executed the query
- `discord_username` (string, required): Discord username at time of query
- `command_name` (string, required): Discord slash command name (e.g., "archive query")
- `query_text` (string, required): Original user query text
- `timestamp` (datetime, required): Query execution timestamp (ISO 8601)
- `answer_hash` (string, required): SHA-256 hash of bot response (for tamper detection)
- `citations` (list[dict], required): List of citations in format `[meeting_id | date | speaker]`
- `rag_query_id` (string, optional): Reference to underlying RAGQuery if applicable
- `rate_limit_status` (string, optional): Rate limit status at time of query ("allowed", "exceeded")
- `execution_time_ms` (integer, optional): Query execution time in milliseconds
- `error_occurred` (boolean, required): Whether an error occurred during execution
- `error_message` (string, optional): Error message if error_occurred is true

**Validation Rules**:
- `query_id` must be unique UUID
- `discord_user_id` must be valid Discord snowflake
- `answer_hash` must be valid SHA-256 hash (32-byte hex string)
- `timestamp` must be valid ISO 8601 datetime
- All queries must be logged (SC-006: 100% logging compliance)

**Relationships**:
- Many-to-one: Many ArchiveQueryLog entries belong to one DiscordUser
- One-to-one: One ArchiveQueryLog can reference one RAGQuery (if query was successful)

**State Transitions**:
1. **Created**: Query log entry created when command received
2. **Processing**: Query sent to RAG pipeline
3. **Completed**: Query completed successfully, answer and citations recorded
4. **Failed**: Query failed with error, error message recorded

---

### RateLimitEntry

**Description**: Represents a rate limit tracking entry for a Discord user.

**Fields**:
- `user_id` (string, required): Discord user ID
- `query_timestamps` (deque[datetime], required): Timestamps of recent queries (last 10 queries)
- `limit` (integer, required): Maximum queries allowed (default: 10)
- `window_seconds` (integer, required): Time window in seconds (default: 60)
- `last_cleanup` (datetime, optional): Last time expired entries were cleaned up

**Validation Rules**:
- `user_id` must be valid Discord snowflake
- `query_timestamps` must only contain timestamps within the current window
- `limit` must match FR-010 requirement (10 queries per minute)

**Relationships**:
- One-to-one: One RateLimitEntry per DiscordUser

**State Transitions**:
1. **Initialized**: New user entry created with empty timestamps
2. **Active**: User has queries within rate limit window
3. **Exceeded**: User has exceeded rate limit, new queries rejected
4. **Reset**: Window expired, timestamps cleared, ready for new queries

---

### BotCommand

**Description**: Represents a Discord slash command with its metadata and permissions.

**Fields**:
- `command_name` (string, required): Discord slash command name (e.g., "archive query")
- `description` (string, required): Command description shown in Discord
- `required_roles` (list[string], optional): List of required roles for access (empty = public)
- `rate_limit_enabled` (boolean, required): Whether rate limiting applies (default: true)
- `handler_function` (string, required): Python function name that handles the command

**Validation Rules**:
- `command_name` must match Discord command naming conventions (lowercase, no spaces, use hyphens)
- `required_roles` must be subset of ["public", "contributor", "admin"]
- All commands must have handler functions defined

**Relationships**:
- One-to-many: One BotCommand can be executed multiple times (creates ArchiveQueryLog entries)

**Commands**:
- `/archive query` - Public access, rate limited
- `/archive topics` - Contributor+ access, rate limited
- `/archive people` - Contributor+ access, rate limited
- `/archive stats` - Admin access, rate limited (future: admin monitoring)

---

## Data Flow

### Query Execution Flow

1. **Discord Interaction** → DiscordUser created from interaction
2. **Permission Check** → Validate user roles against BotCommand requirements
3. **Rate Limit Check** → Check RateLimitEntry for user, update if allowed
4. **Query Execution** → Call QueryService.execute_query() or EntityQueryService methods
5. **Response Formatting** → Format RAGResult or entity results for Discord
6. **Message Splitting** → Split long responses into multiple messages (FR-012)
7. **Audit Logging** → Create ArchiveQueryLog entry with all metadata
8. **Response Delivery** → Send formatted messages to Discord channel

---

## Integration with Existing Models

### RAGQuery (existing)

The bot uses the existing `RAGQuery` model from `src/models/rag_query.py`:
- Bot creates RAGQuery via QueryService.execute_query()
- Extracts citations, answer, and metadata from RAGQuery
- Formats RAGQuery data for Discord messages

### Entity Models (existing)

The bot uses existing entity models for `/archive topics` and `/archive people`:
- `Person` - For person search results
- `Tag` - For topic search results  
- `Meeting` - For meeting references in citations
- Entity models are accessed via EntityQueryService

---

## Storage

### In-Memory Storage

- **RateLimitEntry**: Stored in memory (dict mapping user_id → RateLimitEntry)
- **DiscordUser**: Created on-demand from Discord interactions, not persisted
- **BotCommand**: Defined in code, not persisted

### Persistent Storage

- **ArchiveQueryLog**: Stored in `audit_logs/` directory as JSON files (existing AuditWriter)
- **RAGQuery**: Stored in audit logs via existing audit system
- **Entity data**: Stored in `entities/` directory (existing entity storage system)

---

## Notes

- Rate limiting uses in-memory storage for MVP (single-server deployment)
- Future scaling could use Redis for distributed rate limiting
- All queries are logged to existing audit system (no new logging infrastructure needed)
- Bot does not modify existing data models, only consumes them



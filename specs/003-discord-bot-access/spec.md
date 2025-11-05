# Feature Specification: Discord Bot Interface for Archive-RAG

**Feature Branch**: `003-discord-bot-access`  
**Created**: 2025-01-27  
**Status**: Draft  
**Input**: User description: "Add Discord bot access to query the Archive RAG with natural language"

## Clarifications

### Session 2025-01-27

- Q: Should there be per-user rate limits to prevent abuse and ensure fair access? → A: Yes, per-user limits (e.g., 10 queries per minute per user)
- Q: What specific capabilities should admins have beyond contributor access? → A: Admins have all contributor capabilities plus system monitoring/management commands (e.g., view usage stats, manage rate limits)
- Q: What should the bot do when the RAG pipeline is temporarily unavailable (e.g., service down, network error)? → A: Bot returns user-friendly error message indicating temporary unavailability and suggests retrying later
- Q: How should the bot handle responses that exceed Discord's 2000 character limit per message? → A: Split response into multiple messages, with answer first, then citations in follow-up messages
- Q: Should the bot provide immediate feedback (e.g., typing indicator, acknowledgment message) when a query is received? → A: Bot sends immediate acknowledgment (e.g., "Processing your query...") then follows with answer

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask Questions About Archive Meeting Data (Priority: P1)

**As** a Discord community member

**I want** to ask natural-language questions about archived meetings

**So that** I can quickly retrieve institutional knowledge without browsing dashboards

**Why this priority**: This is the core interaction. Must work independently.

**Independent Test**: Send `/archive query "What decisions were made last January?"` → bot returns answer + citations

**Acceptance Scenarios**:

1. **Given** the bot is in the server,

   **When** I run `/archive query "What is the tag taxonomy?"`,

   **Then** it returns a concise RAG answer + citation links

2. **Given** a question that cannot be answered,

   **When** I query "When is the next ambassador party?",

   **Then** bot replies `No relevant archive data found.` with helpful suggestions

---

### User Story 2 - Retrieve Entities & Topics (Priority: P2)

**As** a contributor

**I want** to search by person/topic tags

**So that** I can understand workgroup participation and themes

**Why this priority**: Enhances discovery and exploration of archived content beyond basic queries. This is a contributor-only feature.

**Independent Test**: `/archive people "Gorga"` → returns mentions, links, context excerpts (requires contributor role)

**Acceptance Scenarios**:

1. **Given** I am a contributor with the appropriate role

   **When** I run `/archive topics "RAG ethics"`

   **Then** bot returns top 5 references with timestamps + links

2. **Given** I am a contributor with the appropriate role

   **When** I run `/archive people "Gorga"`

   **Then** bot returns mentions, links, and context excerpts from relevant meetings

3. **Given** I am a public user (not a contributor)

   **When** I attempt to run `/archive topics "RAG ethics"` or `/archive people "Gorga"`

   **Then** bot replies with a permission error indicating that contributor role is required

---

### User Story 3 - Provide Provenance & Transparency (Priority: P3)

**As** a governance stakeholder

**I want** answers to include citations and source log IDs

**So that** the bot remains truthful and auditable

**Why this priority**: Maintains trust and allows verification of information sources.

**Independent Test**: Ask any question → response must include `[meeting_id | date | speaker]`

**Acceptance Scenarios**:

1. **When** a query is answered

   **Then** the bot displays citations + "View full meeting record" link

2. **Given** a response with citations

   **When** I review the output

   **Then** each citation follows the format `[meeting_id | date | speaker]` and links to the source

---

### Edge Cases

- What happens when **RAG index not initialized**? → bot replies with an error description + admin guidance

- How does system handle **malicious prompts**? → respond with safe-completion + moderation note

- What happens for **empty / unclear queries**? → "Please restate your question; examples: …"

- What happens when **Discord API rate limits are exceeded**? → bot queues requests and responds when capacity available

- What happens when **RAG pipeline timeout occurs**? → bot returns error message with suggestion to try a simpler query

- What happens when **public user attempts to use contributor-only commands**? → bot returns permission error message indicating contributor role required

- What happens when **user exceeds per-user rate limit**? → bot returns rate limit error message with remaining time until limit resets

- What happens when **RAG pipeline service is temporarily unavailable**? → bot returns user-friendly error message indicating temporary unavailability and suggests retrying later

- What happens when **bot response exceeds Discord's 2000 character limit**? → bot splits response into multiple messages, with answer first, then citations in follow-up messages

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bot MUST authenticate to Discord and respond to slash commands

- **FR-002**: Bot MUST call the local RAG inference pipeline to process queries

- **FR-003**: Bot MUST return answers with citations in format `[meeting_id | date | speaker]`

- **FR-004**: Bot MUST support `/archive query`, `/archive topics`, `/archive people` slash commands

- **FR-005**: Bot MUST log queries + output hashes for audit purposes

- **FR-006**: Bot MUST support role-based access control: public users have access to `/archive query` command only, while contributors have access to `/archive query`, `/archive topics`, and `/archive people` commands

- **FR-007**: Bot MUST redact private/PII data before responding in Discord messages

- **FR-008**: Bot MUST handle errors gracefully with user-friendly messages

- **FR-009**: Bot MUST validate user permissions before processing queries

- **FR-010**: Bot MUST enforce per-user rate limits (e.g., 10 queries per minute per user) to prevent abuse and ensure fair resource distribution

- **FR-011**: Bot MUST support admin role with system monitoring/management capabilities (e.g., view usage statistics, manage rate limits) in addition to all contributor capabilities

- **FR-012**: Bot MUST handle responses exceeding Discord's 2000 character limit by splitting into multiple messages, with answer first, then citations in follow-up messages

- **FR-013**: Bot MUST send immediate acknowledgment message (e.g., "Processing your query...") when a query is received, then follow with the answer when ready

### Key Entities *(include if feature involves data)*

- **DiscordUser**: Represents a Discord user with id, username, and roles (ambassador / public / admin). Used for authentication and authorization.

- **ArchiveQueryLog**: Represents a logged query with query text, timestamp, answer_hash, and citations. Used for audit trail and compliance.

- **RAGResult**: Represents the result from RAG pipeline with answer text, citations, and token statistics. Used to format bot responses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of valid queries respond in under 3 seconds from user command to bot response

- **SC-002**: 100% of answers include citation metadata in the specified format

- **SC-003**: Zero hallucinated answers in benchmark test set (all answers must be grounded in archive data)

- **SC-004**: ≥ 80% user comprehension rating in UX feedback poll (users understand the answers provided)

- **SC-005**: Bot successfully handles 100 concurrent users without degradation in response time

- **SC-006**: All queries are logged with complete audit trail (100% logging compliance)

## Assumptions

- Discord bot token is securely stored and managed through environment variables or secure configuration

- RAG pipeline is already deployed and accessible locally from the bot process

- Discord server has role-based permissions configured (public, contributor, admin roles exist)

- Bot responses are formatted to fit Discord message limits (2000 characters per message)

- Citation links reference a web interface or document viewer for full meeting records

- PII redaction follows the same policies as the main RAG system

- Bot runs continuously and maintains connection to Discord API

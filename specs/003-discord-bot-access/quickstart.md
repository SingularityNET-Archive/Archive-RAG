# Quickstart Guide: Discord Bot Interface for Archive-RAG

**Created**: 2025-01-27  
**Feature**: Discord Bot Interface for Archive-RAG

## Overview

This guide provides step-by-step instructions for setting up and using the Discord bot interface for Archive-RAG. The bot allows Discord community members to query archived meeting data using natural language slash commands.

## Prerequisites

- Python 3.11+ installed
- Discord bot token (from Discord Developer Portal)
- Existing Archive-RAG installation with indexed meeting data
- Discord server with appropriate roles configured (public, contributor, admin)

## Setup

### 1. Install Dependencies

Add Discord bot dependencies to your environment:

```bash
pip install discord.py>=2.3.0
pip install pytest-asyncio>=0.21.0  # For testing
```

Or add to `requirements.txt`:
```
discord.py>=2.3.0
pytest-asyncio>=0.21.0
```

### 2. Create Discord Bot Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Navigate to "Bot" section
4. Create a bot user
5. Copy the bot token (save securely)
6. Enable "Message Content Intent" (if needed for future features)
7. Enable "Server Members Intent" (for role checking)

### 3. Invite Bot to Discord Server

1. Navigate to "OAuth2" → "URL Generator"
2. Select scopes:
   - `bot`
   - `applications.commands` (required for slash commands)
3. Select bot permissions:
   - Send Messages
   - Use Slash Commands
   - Read Message History (optional, for future features)
4. Copy the generated URL and open in browser
5. Select your Discord server and authorize

### 4. Configure Bot Token

Set the Discord bot token as an environment variable:

```bash
export DISCORD_BOT_TOKEN="your-bot-token-here"
```

Or create a `.env` file:
```bash
DISCORD_BOT_TOKEN=your-bot-token-here
```

### 5. Configure Discord Roles

Ensure your Discord server has the following roles configured:
- **public** (default role, or no role = public access)
- **contributor** (for enhanced access)
- **admin** (for system monitoring)

Role names must match exactly (case-sensitive).

### 6. Configure RAG Index

Ensure you have a FAISS index created with meeting data:

```bash
# Index meeting data (if not already done)
archive-rag index data/meetings/ indexes/meetings.faiss
```

Set the default index path in bot configuration:

```bash
export ARCHIVE_RAG_INDEX_PATH="indexes/meetings.faiss"
```

## Running the Bot

### Start the Bot

Run the bot from the project root:

```bash
python -m src.bot.bot
```

Or create a CLI command:

```bash
archive-rag bot start
```

The bot will:
1. Connect to Discord
2. Register slash commands
3. Log connection status
4. Start listening for commands

### Verify Bot is Running

1. Check Discord server - bot should appear online
2. Type `/archive` in a channel - slash command should appear
3. Check bot logs for connection confirmation

## Usage Examples

### Basic Query (Public Access)

Any user can ask questions about archived meetings:

```
/archive query query:"What decisions were made last January?"
```

**Response**:
```
Processing your query...

Answer: [RAG-generated answer with citations]

Citations:
[meeting_id | date | speaker]
[meeting_id | date | speaker]

View full meeting record: [link]
```

### Topic Search (Contributor+)

Contributors and admins can search by topics:

```
/archive topics topic:"RAG ethics"
```

**Response**:
```
Topic: RAG ethics

References:
1. [meeting_id | date | speaker] - [excerpt]
2. [meeting_id | date | speaker] - [excerpt]
...
(Showing top 5 results)
```

### People Search (Contributor+)

Contributors and admins can search for people:

```
/archive people person:"Gorga"
```

**Response**:
```
Person: Gorga

Mentions:
1. [meeting_id | date] - [context excerpt]
2. [meeting_id | date] - [context excerpt]
...

View person profile: [link]
```

## Testing

### Run Unit Tests

```bash
pytest tests/bot/ -v
```

### Test Rate Limiting

1. Execute 10 queries rapidly
2. 11th query should return rate limit error
3. Wait 60 seconds, query should work again

### Test Permissions

1. As public user, try `/archive topics` → should get permission error
2. As contributor, try `/archive topics` → should work
3. As admin, try `/archive stats` → should work (when implemented)

### Test Error Handling

1. Stop RAG service, execute query → should get "service unavailable" error
2. Send empty query → should get validation error
3. Send malformed query → should get graceful error message

## Troubleshooting

### Bot Not Responding

- Check bot token is correct: `echo $DISCORD_BOT_TOKEN`
- Check bot is online in Discord server
- Check bot has permissions in channel
- Check bot logs for errors

### Slash Commands Not Appearing

- Ensure bot has `applications.commands` scope
- Wait up to 1 hour for Discord to sync commands (or re-invite bot)
- Check bot logs for command registration errors

### Rate Limit Errors

- Check rate limit configuration (default: 10 queries/minute)
- Verify user is not exceeding limit
- Check rate limiter cleanup is working (logs)

### Permission Errors

- Verify Discord role names match exactly (case-sensitive)
- Check user has correct role assigned
- Verify bot has "Server Members Intent" enabled

### RAG Pipeline Errors

- Check RAG index exists and is accessible
- Verify `ARCHIVE_RAG_INDEX_PATH` is set correctly
- Check RAG service logs for errors
- Verify FAISS index is compatible with current embedding model

## Configuration Options

### Environment Variables

```bash
# Required
DISCORD_BOT_TOKEN=your-bot-token

# Optional
ARCHIVE_RAG_INDEX_PATH=indexes/meetings.faiss  # Default index path
DISCORD_RATE_LIMIT_PER_MINUTE=10               # Rate limit per user
DISCORD_MAX_MESSAGE_LENGTH=2000                 # Discord message limit
DISCORD_ENABLE_STATS=false                      # Enable /archive stats command
```

### Bot Configuration File

Create `config/bot.yaml` (optional):

```yaml
discord:
  token: ${DISCORD_BOT_TOKEN}
  rate_limit:
    per_minute: 10
    window_seconds: 60
  max_message_length: 2000

archive_rag:
  index_path: indexes/meetings.faiss
  default_top_k: 5
```

## Monitoring

### Audit Logs

All queries are logged to `audit_logs/` directory:

```bash
# View recent queries
ls -lt audit_logs/ | head

# View specific query log
cat audit_logs/query-{query_id}.json
```

### Bot Logs

Bot logs are written to console (structured logging):

```bash
# Run bot with verbose logging
LOG_LEVEL=DEBUG python -m src.bot.bot
```

### Metrics (Future)

Admin commands will provide usage statistics:
- Total queries executed
- Active users
- Rate limit status
- Average response time

## Next Steps

1. **Test all commands** in your Discord server
2. **Configure roles** for your community members
3. **Monitor audit logs** for compliance
4. **Set up monitoring** for bot health
5. **Plan scaling** if needed (Redis for distributed rate limiting)

## Support

- Check bot logs for detailed error messages
- Review audit logs for query history
- Consult [spec.md](./spec.md) for requirements
- Consult [plan.md](./plan.md) for implementation details



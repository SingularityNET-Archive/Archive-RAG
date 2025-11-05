# Testing Discord Bot with Slash Commands

This guide explains how to test your Archive-RAG Discord bot using slash commands.

## Prerequisites

- Bot is running (you should see log messages indicating it's online)
- Bot appears online in Discord (green status indicator)
- Bot has been invited to your Discord server

## Step 1: Verify Bot is Online

1. Open Discord and navigate to your server
2. Check the member list on the right side
3. Your bot should appear with a **green status indicator** (online)
4. If the bot is offline (gray), check your bot logs for errors

## Step 2: Use Slash Commands

### How to Access Slash Commands

1. **In any text channel**, type `/` (forward slash)
2. Discord will show a list of available commands
3. Start typing `archive` - you should see `/archive query` appear
4. Click on it or press Enter to select it

### If Commands Don't Appear

- **Wait up to 1 hour**: Discord can take time to sync commands globally
- **Re-invite bot**: Use the OAuth2 URL again with `applications.commands` scope
- **Check bot logs**: Look for "bot_commands_synced" message
- **Restart bot**: Sometimes restarting helps sync commands

## Step 3: Test the `/archive query` Command

### Basic Test Query

1. Type: `/archive query`
2. Fill in the `query` parameter: `"What is this bot?"`
3. Press Enter or click the command

**Expected Behavior:**
1. Bot immediately responds: "Processing your query..."
2. After a few seconds, bot sends the answer with citations
3. Citations formatted as: `[meeting_id | date | workgroup_name]`

### Example Queries to Try

```
/archive query query:"What decisions were made last January?"
/archive query query:"What is the tag taxonomy?"
/archive query query:"What meetings discussed budget allocation?"
/archive query query:"Tell me about recent decisions"
```

### What to Look For

✅ **Success Indicators:**
- Bot responds with "Processing your query..."
- Answer appears with relevant information
- Citations are included
- Response is formatted correctly

❌ **Error Indicators:**
- "Rate limit exceeded" - You've sent too many queries (wait 60 seconds)
- "RAG service temporarily unavailable" - Index file not found or bot can't access it
- "No relevant archive data found" - Query didn't match any content
- Bot doesn't respond at all - Check bot logs

## Step 4: Test Rate Limiting

### Test Rate Limit Enforcement

1. Send 10 queries rapidly (within 1 minute)
2. The 11th query should return: **"Rate limit exceeded. Please wait Xs."**
3. Wait 60 seconds
4. Query should work again

**Expected Message:**
```
Rate limit exceeded. Please wait 45s.
```

## Step 5: Test Error Handling

### Test with Empty/Invalid Query

Try queries that might not find results:
```
/archive query query:"xyzabc123nonexistent"
```

**Expected Response:**
```
No relevant archive data found. Try rephrasing your question or check the archive index.
```

### Test RAG Service Unavailable

If your index file doesn't exist or is inaccessible:
- Bot should respond: "RAG service temporarily unavailable. Please try again later."
- Check bot logs for specific error details

## Step 6: Check Bot Logs

While testing, monitor your bot's terminal output for:

**Success Messages:**
```
[INFO] bot_ready: bot_user=YourBotName#1234 guild_count=1
[INFO] bot_commands_synced: synced_count=1
[INFO] query_command_executed: user_id=123456 query_id=uuid-123
```

**Error Messages:**
```
[ERROR] query_execution_failed: error=...
[WARNING] rate_limit_exceeded: user_id=123456
```

## Troubleshooting

### Bot Doesn't Respond to Commands

1. **Check bot is online** - Green status in Discord
2. **Check bot logs** - Look for errors
3. **Verify command is registered** - Look for "bot_commands_synced" in logs
4. **Check permissions** - Bot needs "Send Messages" permission in channel
5. **Try restarting bot** - Stop (Ctrl+C) and restart

### Commands Not Appearing in Discord

1. **Wait longer** - Discord can take up to 1 hour to sync commands
2. **Re-invite bot** - Use OAuth2 URL with `applications.commands` scope
3. **Check bot logs** - Look for command sync errors
4. **Verify bot is in server** - Bot must be in the server to use commands

### "RAG service unavailable" Error

1. **Check index file exists:**
   ```bash
   ls -la indexes/meetings.faiss
   ```
2. **Check environment variable:**
   ```bash
   echo $ARCHIVE_RAG_INDEX_PATH
   ```
3. **Check bot logs** - Look for file not found errors
4. **Verify file permissions** - Bot process must be able to read the file

### Rate Limit Errors When Testing

- **Normal behavior** - 10 queries per minute is the limit
- **Wait 60 seconds** - Rate limit resets after the window expires
- **Check rate limit config** - Default is 10 queries/minute per user

## Quick Test Checklist

- [ ] Bot appears online in Discord
- [ ] `/archive` command appears when typing `/`
- [ ] `/archive query` command works
- [ ] Bot responds with "Processing your query..."
- [ ] Bot sends answer with citations
- [ ] Rate limiting works (11th query gets rate limit error)
- [ ] Error messages are user-friendly
- [ ] Bot logs show successful execution

## Example Test Session

```
You: /archive query query:"What is this bot?"
Bot: Processing your query...

Bot: [Answer text with information about the bot]

Citations:
[meeting_001 | 2024-01-15 | Archive Team]
[meeting_002 | 2024-02-20 | Archive Team]

View full meeting record: [link]
```

## Next Steps

After basic testing works:

1. **Test with different queries** - Try various question types
2. **Test error scenarios** - Invalid queries, rate limits, etc.
3. **Check audit logs** - Verify queries are being logged
4. **Monitor performance** - Check response times in logs
5. **Set up roles** - Test contributor/admin features (Phase 4)
6. **See comprehensive examples** - Check [Discord Bot Testing Examples](./discord-bot-testing-examples.md) for detailed test scenarios

## Support

If you encounter issues:
- Check bot logs for detailed error messages
- Review [Discord Bot Setup Guide](./discord-bot-setup.md)
- Check [Troubleshooting Section](./discord-bot-setup.md#troubleshooting)
- Verify all prerequisites are met



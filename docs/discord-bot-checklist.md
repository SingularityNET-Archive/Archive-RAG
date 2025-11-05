# Discord Bot Setup Checklist

Use this checklist to ensure you've completed all required steps to set up and test the Archive-RAG Discord bot.

## Pre-Setup Requirements

- [ ] Python 3.11+ installed
- [ ] Archive-RAG project cloned and dependencies installed
- [ ] A Discord account
- [ ] A Discord server where you can add bots (have "Manage Server" permission)
- [ ] FAISS index created (or plan to create one)

## Discord Developer Portal Setup

### Application Creation
- [ ] Go to [Discord Developer Portal](https://discord.com/developers/applications/)
- [ ] Click "New Application"
- [ ] Name your application (e.g., "Archive-RAG Bot")
- [ ] Click "Create"

### Bot User Creation
- [ ] Go to "Bot" section (left sidebar)
- [ ] Click "Add Bot" → "Yes, do it!"
- [ ] Bot user created successfully

### Bot Configuration
- [ ] **Bot Username**: Set if desired (optional)
- [ ] **Bot Icon**: Upload if desired (optional)
- [ ] **Bot Token**: Click "Reset Token" → Copy token (save securely!)
- [ ] **Privileged Gateway Intents**:
  - [ ] ✅ **"Server Members Intent"** - ENABLED (REQUIRED)
  - [ ] ❌ "Message Content Intent" - DISABLED (not needed)
- [ ] Save changes (if prompted)

### OAuth2 URL Generation
- [ ] Go to "OAuth2" → "URL Generator"
- [ ] **Installation Type**: Select "Guild Install"
- [ ] **SCOPES**:
  - [ ] ✅ `bot`
  - [ ] ✅ `applications.commands`
- [ ] **BOT PERMISSIONS**:
  - [ ] ✅ Send Messages
  - [ ] ✅ Use Slash Commands
  - [ ] ✅ Read Message History (optional)
- [ ] Copy generated URL

### Bot Invitation
- [ ] Open OAuth2 URL in browser
- [ ] Logged into Discord (same account that has server permissions)
- [ ] Select Discord server from dropdown
- [ ] Click "Authorize"
- [ ] Complete CAPTCHA if prompted
- [ ] Bot appears in server member list

## Local Environment Setup

### Dependencies
- [ ] Install Discord bot dependencies:
  ```bash
  pip install discord.py>=2.3.0 pytest-asyncio>=0.21.0
  ```
- [ ] Or ensure `requirements.txt` includes these dependencies

### Environment Variables
Choose one method:

**Option A: Export in Terminal**
- [ ] Set `DISCORD_BOT_TOKEN`:
  ```bash
  export DISCORD_BOT_TOKEN="your-bot-token-here"
  ```
- [ ] Set `ARCHIVE_RAG_INDEX_PATH` (optional):
  ```bash
  export ARCHIVE_RAG_INDEX_PATH="indexes/meetings.faiss"
  ```

**Option B: Create .env File (Recommended)**
- [ ] Create `.env` file in project root
- [ ] Add `DISCORD_BOT_TOKEN=your-bot-token-here`
- [ ] Add `ARCHIVE_RAG_INDEX_PATH=indexes/meetings.faiss` (optional)
- [ ] Verify `.env` is in `.gitignore` (should already be)

### RAG Index Preparation
- [ ] Create FAISS index (if not already done):
  ```bash
  archive-rag index data/meetings/ indexes/meetings.faiss
  ```
- [ ] Or use existing index path
- [ ] Verify index file exists:
  ```bash
  ls -la indexes/*.faiss
  ```

## Bot Startup

### Initial Startup
- [ ] Start bot from project root:
  ```bash
  archive-rag bot
  ```
- [ ] Or with explicit options:
  ```bash
  archive-rag bot --token "your-token" --index-name "indexes/meetings.faiss"
  ```
- [ ] Bot starts without errors
- [ ] See log messages indicating:
  - [ ] Bot setup hook executed
  - [ ] Bot ready and connected
  - [ ] Commands synced successfully

### Verification
- [ ] Check Discord - bot appears **online** (green status)
- [ ] Type `/archive` in Discord channel
- [ ] `/archive query` command appears in autocomplete
- [ ] No errors in bot logs

## Testing

### Basic Functionality
- [ ] Execute `/archive query query:"What is this bot?"`
- [ ] Bot responds with "Processing your query..."
- [ ] Bot sends answer with citations
- [ ] Citations formatted as `[meeting_id | date | workgroup_name]`

### Rate Limiting
- [ ] Send 10 queries rapidly (within 1 minute)
- [ ] 11th query returns rate limit error
- [ ] Wait 60 seconds
- [ ] Query works again after rate limit reset

### Error Handling
- [ ] Test with empty/invalid query
- [ ] Verify error messages are user-friendly
- [ ] Check bot logs for errors

### Role-Based Access (Optional)
- [ ] Create `contributor` role in Discord server
- [ ] Create `admin` role in Discord server
- [ ] Assign roles to test users
- [ ] Test `/archive topics` (should require contributor role)
- [ ] Test `/archive people` (should require contributor role)

## Troubleshooting Checklist

If something isn't working:

- [ ] **Bot not online?**
  - [ ] Check `DISCORD_BOT_TOKEN` is set correctly
  - [ ] Verify token is valid (not expired/reset)
  - [ ] Check bot has permissions in channel
  - [ ] Review bot logs for errors

- [ ] **Slash commands not appearing?**
  - [ ] Wait up to 1 hour (Discord sync delay)
  - [ ] Verify `applications.commands` scope in OAuth2 URL
  - [ ] Re-invite bot with correct scopes
  - [ ] Check bot logs for sync errors

- [ ] **No servers showing in authorization?**
  - [ ] Logged into Discord in browser
  - [ ] Have "Manage Server" permission (not just admin role)
  - [ ] Bot not already in server
  - [ ] Try different browser/incognito mode

- [ ] **Role checking not working?**
  - [ ] Server Members Intent enabled in Developer Portal
  - [ ] Bot restarted after enabling intent
  - [ ] Bot re-invited after enabling intent
  - [ ] Role names match exactly (case-sensitive)

- [ ] **RAG service unavailable?**
  - [ ] Verify index file exists and is readable
  - [ ] Check `ARCHIVE_RAG_INDEX_PATH` is correct
  - [ ] Verify index file permissions
  - [ ] Check RAG service logs

## Security Checklist

- [ ] Bot token saved securely (not in version control)
- [ ] `.env` file in `.gitignore` (verify)
- [ ] Bot token not shared publicly
- [ ] Bot permissions limited to necessary only
- [ ] Separate bot token for testing vs production

## Post-Setup

- [ ] All commands working correctly
- [ ] Rate limiting functioning
- [ ] Error handling working
- [ ] Audit logs being written to `audit_logs/` directory
- [ ] Bot logs showing expected information
- [ ] Documentation reviewed for additional features

## Quick Reference

**Start Bot:**
```bash
archive-rag bot
```

**Check Token:**
```bash
echo $DISCORD_BOT_TOKEN
```

**Check Index:**
```bash
ls -la indexes/*.faiss
```

**View Bot Logs:**
- Check console output when running bot
- Look for structured log messages

**View Audit Logs:**
```bash
ls -lt audit_logs/ | head
```

## Next Steps

After completing this checklist:

1. Test all commands thoroughly
2. Configure roles for your community
3. Monitor audit logs for compliance
4. Set up monitoring/alerting (optional)
5. Plan for scaling if needed

## Support Resources

- [Discord Bot Setup Guide](./discord-bot-setup.md)
- [Bot Permission Settings](./discord-bot-permissions.md)
- [Quickstart Guide](../specs/003-discord-bot-access/quickstart.md)
- [Bot Specification](../specs/003-discord-bot-access/spec.md)



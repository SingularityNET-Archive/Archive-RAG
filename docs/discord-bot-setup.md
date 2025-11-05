# Discord Bot Setup Guide

This guide will walk you through setting up Discord to test the Archive-RAG Discord bot.

## Prerequisites

- Python 3.11+ installed
- Archive-RAG installed with dependencies
- A Discord account
- A Discord server where you can add bots (create a test server if needed)

## Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** in the top right
3. Give your application a name (e.g., "Archive-RAG Bot")
4. Click **"Create"**

## Step 2: Create a Bot User

1. In your application, go to the **"Bot"** section (left sidebar)
2. Click **"Add Bot"** → **"Yes, do it!"**
3. Your bot user is now created

## Step 3: Configure Bot Settings

1. In the **"Bot"** section, configure the following:

   **Bot Username**: Change if desired (optional)
   
   **Icon**: Upload an icon (optional)
   
   **Token**: Click **"Reset Token"** → **"Yes, do it!"** → **Copy the token** (save it securely!)
   
   **Privileged Gateway Intents** (IMPORTANT - Scroll down to find this section):
   - ✅ **Enable "Server Members Intent"** (REQUIRED - enables role checking for contributor/admin permissions)
   - ❌ "Message Content Intent" - Leave disabled (not needed for slash commands)
   
   **⚠️ Important**: After enabling Server Members Intent, you must:
   - Save the changes
   - Restart your bot for the setting to take effect
   - Re-invite the bot if it was already added to your server

**See [Bot Permission Settings Guide](./discord-bot-permissions.md) for detailed information.**

## Step 4: Generate Bot Invite URL

1. Go to the **"OAuth2"** → **"URL Generator"** section
2. **Installation Type**: Select **"Guild Install"** (server install) - this is the default and correct option for bots that operate in Discord servers
3. Under **"SCOPES"**, select:
   - ✅ `bot`
   - ✅ `applications.commands` (required for slash commands)
4. Under **"BOT PERMISSIONS"**, select:
   - ✅ **Send Messages**
   - ✅ **Use Slash Commands**
   - ✅ **Read Message History** (optional, for future features)
5. Copy the generated URL at the bottom (looks like: `https://discord.com/api/oauth2/authorize?client_id=...`)
6. Open the URL in your browser
7. Select your Discord server
8. Click **"Authorize"**
9. Complete any CAPTCHA if prompted

**Note**: Use **Guild Install** (not User Install) because:
- The bot needs to be added to a Discord server
- It uses slash commands in server channels
- It checks server roles (contributor, admin)
- It operates in server context, not DM context

Your bot should now appear in your Discord server (offline initially).

## Step 5: Configure Environment Variables

Set up the required environment variables:

### Option 1: Export in Terminal (Temporary)

```bash
export DISCORD_BOT_TOKEN="your-bot-token-here"
export ARCHIVE_RAG_INDEX_PATH="indexes/meetings.faiss"  # or your index path
```

### Option 2: Create a `.env` File (Recommended)

Create a `.env` file in the project root:

```bash
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your-bot-token-here

# RAG Index Configuration
ARCHIVE_RAG_INDEX_PATH=indexes/meetings.faiss
```

**Note**: Make sure `.env` is in your `.gitignore` to avoid committing your bot token!

### Option 3: Use Command Line Options

You can also pass these directly when running the bot:

```bash
archive-rag bot --token "your-bot-token" --index-name "indexes/meetings.faiss"
```

## Step 6: Prepare Your RAG Index

Ensure you have a FAISS index ready:

```bash
# If you haven't created an index yet:
archive-rag index data/meetings/ indexes/meetings.faiss

# Or use the sample data:
archive-rag index "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" indexes/sample-meetings.faiss --no-redact-pii
```

## Step 7: Install Bot Dependencies

Make sure Discord bot dependencies are installed:

```bash
pip install discord.py>=2.3.0 pytest-asyncio>=0.21.0
```

Or if using `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Step 8: Start the Bot

Run the bot using the CLI command:

```bash
archive-rag bot
```

Or with explicit options:

```bash
archive-rag bot --token "your-bot-token" --index-name "indexes/meetings.faiss"
```

You should see output like:

```
Starting Discord bot with index: indexes/meetings.faiss
[INFO] bot_setup_hook: index_name=indexes/meetings.faiss
[INFO] bot_ready: bot_user=YourBotName#1234 guild_count=1
[INFO] bot_commands_synced: synced_count=1
```

## Step 9: Verify Bot is Running

1. Check Discord - your bot should appear **online** (green status)
2. In any text channel, type `/archive` - you should see the `/archive query` command appear
3. Check bot logs for any errors

## Step 10: Test the Bot

### Basic Query Test

1. In Discord, type: `/archive query query:"What is this bot?"`
2. You should see:
   - Immediate response: "Processing your query..."
   - Follow-up with the answer and citations

### Verify Rate Limiting

1. Send 10 queries rapidly
2. The 11th query should return: "Rate limit exceeded. Please wait Xs."

### Test Error Handling

1. Stop the bot (Ctrl+C)
2. Try a query - you should see an error (or nothing if bot is offline)

## Step 11: Configure Roles (Optional)

For testing contributor/admin features, set up roles:

1. In Discord Server Settings → **Roles**
2. Create roles:
   - `contributor` (for `/archive topics` and `/archive people`)
   - `admin` (for future `/archive stats`)
3. Assign roles to test users:
   - Server Settings → **Members** → Select user → **Roles**

**Note**: Role names must match exactly (case-sensitive)!

## Troubleshooting

### Bot Not Appearing Online

- **Check token**: Verify `DISCORD_BOT_TOKEN` is set correctly
  ```bash
  echo $DISCORD_BOT_TOKEN
  ```
- **Check permissions**: Ensure bot has "Send Messages" permission in the channel
- **Check logs**: Look for error messages in bot output

### No Servers Showing in Guild Install Authorization

If you don't see any Discord servers when trying to authorize the bot:

1. **Check your Discord account**
   - Make sure you're logged into Discord with the same account that has admin/manage server permissions
   - Try logging out and back into Discord in your browser

2. **Verify server permissions**
   - You need **"Manage Server"** permission (not just admin role) to add bots
   - Check your role/permissions in the server settings
   - Server Owner can always add bots

3. **Check if bot is already added**
   - The bot might already be in the server
   - Check the server's member list for the bot
   - If present, you can't add it again (but it may need to be re-authorized)

4. **Try different browser/session**
   - Clear browser cookies/cache for discord.com
   - Try incognito/private browsing mode
   - Try a different browser

5. **Check OAuth2 URL scopes**
   - Ensure both `bot` and `applications.commands` scopes are selected
   - Regenerate the OAuth2 URL if needed

6. **Verify server visibility**
   - Make sure the server is not hidden/filtered in your Discord client
   - Try using a server where you are the owner

7. **Check Discord server status**
   - Ensure Discord servers are accessible (not down for maintenance)
   - Try refreshing the authorization page

8. **Alternative: Use direct invite link**
   - If OAuth2 URL doesn't work, you can create a direct invite link:
     - Go to your bot application → OAuth2 → URL Generator
     - Copy the generated URL
     - Or manually construct: `https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=PERMISSIONS&scope=bot%20applications.commands`

### Slash Commands Not Appearing

- **Wait up to 1 hour**: Discord can take time to sync commands globally
- **Re-invite bot**: Use the OAuth2 URL again with `applications.commands` scope
- **Check bot logs**: Look for "bot_command_sync_failed" errors
- **Verify scope**: Ensure `applications.commands` is selected in OAuth2 URL

### "Rate limit exceeded" Immediately

- **Check rate limit config**: Default is 10 queries/minute per user
- **Wait 60 seconds**: Rate limit resets after the window expires
- **Check logs**: Verify rate limiter is working correctly

### "RAG service unavailable" Error

- **Check index path**: Verify `ARCHIVE_RAG_INDEX_PATH` points to a valid FAISS index
- **Check index exists**: 
  ```bash
  ls -la indexes/meetings.faiss
  ```
- **Check permissions**: Ensure bot process can read the index file

### Permission Errors

- **Verify role names**: Must match exactly (case-sensitive): `contributor`, `admin`
- **Check Server Members Intent**: Must be enabled in Discord Developer Portal
- **Check role hierarchy**: Ensure bot has permission to see member roles

### Bot Crashes on Startup

- **Check dependencies**: Ensure `discord.py>=2.3.0` is installed
- **Check Python version**: Requires Python 3.11+
- **Check logs**: Look for stack traces in error output

## Security Best Practices

1. **Never commit your bot token** to version control
2. **Use environment variables** or `.env` files (add to `.gitignore`)
3. **Reset token if exposed**: If token is leaked, reset it in Discord Developer Portal
4. **Limit bot permissions**: Only grant necessary permissions
5. **Use separate bot for testing**: Don't use production bot tokens for testing

## Next Steps

Once your bot is running:

1. Test all commands (`/archive query`)
2. Test rate limiting
3. Set up roles for contributor/admin testing
4. Monitor audit logs in `audit_logs/` directory
5. Check bot logs for any issues

## Additional Resources

- [Discord Developer Portal](https://discord.com/developers/applications)
- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Quickstart Guide](../specs/003-discord-bot-access/quickstart.md)
- [Bot Specification](../specs/003-discord-bot-access/spec.md)


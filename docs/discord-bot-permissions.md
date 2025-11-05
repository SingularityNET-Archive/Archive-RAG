# Discord Bot Permission Settings Guide

This guide explains what settings you need to configure in the [Discord Developer Portal](https://discord.com/developers/applications/) for the Archive-RAG bot.

## Required Settings in Developer Portal

### 1. Bot Settings (Required)

1. Go to your application → **"Bot"** section
2. Scroll down to **"Privileged Gateway Intents"**
3. Enable the following:

   **✅ Server Members Intent** (REQUIRED)
   - This is **required** for the bot to check user roles (contributor, admin)
   - Without this, the bot cannot access member role information
   - The bot code uses `intents.members = True` which requires this setting

   **❌ Message Content Intent** (NOT NEEDED)
   - The bot uses slash commands, not message-based commands
   - This intent is not required for the Archive-RAG bot

### 2. OAuth2 URL Generator Settings (When Inviting Bot)

When generating the bot invite URL in **"OAuth2"** → **"URL Generator"**:

**SCOPES:**
- ✅ `bot` (required)
- ✅ `applications.commands` (required for slash commands)

**BOT PERMISSIONS:**
- ✅ **Send Messages** (required)
- ✅ **Use Slash Commands** (required)
- ✅ **Read Message History** (optional, for future features)

**INSTALLATION TYPE:**
- ✅ **Guild Install** (server install - default)

## Why Server Members Intent is Required

The Archive-RAG bot needs to check user roles to enforce permission-based access:

```python
# From src/bot/bot.py
intents = discord.Intents.default()
intents.members = True  # Needed for role checking
```

Without this intent enabled:
- The bot cannot see member roles
- Role-based permission checks will fail
- Contributor/admin features won't work
- You'll get errors when trying to check user permissions

## How to Enable Server Members Intent

1. Go to [Discord Developer Portal](https://discord.com/developers/applications/)
2. Select your application
3. Click **"Bot"** in the left sidebar
4. Scroll down to **"Privileged Gateway Intents"**
5. Toggle **"Server Members Intent"** to **ON** (green)
6. **Save Changes** (if prompted)

**Important**: After enabling this intent, you may need to:
- Restart your bot for the change to take effect
- Re-invite the bot to your server (if it was already added)

## Verification

After enabling Server Members Intent:

1. **Check the setting** - It should show as enabled (green toggle)
2. **Restart your bot** - Stop and restart the bot process
3. **Test role checking** - Try using commands that require contributor/admin roles
4. **Check bot logs** - Look for any errors related to member intents

## Troubleshooting

### Bot Still Can't See Member Roles

- **Restart the bot** - The intent setting change requires a restart
- **Re-invite the bot** - Remove and re-add the bot to your server
- **Check bot logs** - Look for errors about missing intents
- **Verify intent is enabled** - Double-check the Developer Portal setting

### Intent Not Available

- **Bot must be created** - You need to create a bot user first
- **Wait for approval** - Some intents require Discord approval (Server Members Intent usually doesn't)
- **Check Discord status** - Ensure Discord Developer Portal is accessible

## What Other Settings Don't Need Changing

You **don't need** to change:

- ❌ **Public Bot** - Can stay enabled or disabled (your choice)
- ❌ **Requires OAuth2 Code Grant** - Not needed for this bot
- ❌ **Message Content Intent** - Not needed (bot uses slash commands)
- ❌ **Presence Intent** - Not needed
- ❌ **Server Members Intent** - Already enabled (see above)

## Summary

**Required Settings:**
1. ✅ Enable **Server Members Intent** in Bot settings
2. ✅ Use **Guild Install** when generating OAuth2 URL
3. ✅ Select `bot` and `applications.commands` scopes
4. ✅ Grant **Send Messages** and **Use Slash Commands** permissions

**Not Required:**
- ❌ Message Content Intent
- ❌ Presence Intent
- ❌ Other privileged intents

## Next Steps

After configuring these settings:

1. Restart your bot
2. Test role-based commands
3. Verify permission checks work correctly
4. Check bot logs for any errors



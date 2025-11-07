# Discord Bot Troubleshooting Guide

## Slash Commands Not Appearing

### Issue: `/archive relationships` command not showing in Discord

**Common Causes:**
1. Bot needs to be restarted after adding new commands
2. Discord's global sync can take up to 1 hour
3. Command sync might have failed silently

**Solutions:**

#### 1. Restart the Bot
```bash
# Stop the bot (Ctrl+C) and restart it
python -m src.cli.main bot
```

#### 2. Wait for Global Sync
- Global slash commands can take **up to 1 hour** to appear
- The bot now automatically syncs to each guild for faster availability
- Check bot logs for `bot_commands_synced` and `bot_commands_synced_to_guild`

#### 3. Check Bot Logs
Look for these log messages when the bot starts:
```
bot_commands_synced synced_count=5 command_names=['query', 'topics', 'people', 'list', 'relationships']
```

If you see `bot_command_sync_failed`, check the error message.

#### 4. Force Sync to Specific Guild (For Testing)

If you need the command immediately, you can add a temporary sync command:

```python
# Add this to your bot's on_ready method temporarily
@bot.event
async def on_ready():
    # Force sync to your test guild
    guild = discord.utils.get(bot.guilds, name="Your Test Guild Name")
    if guild:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"Commands synced to {guild.name}")
```

#### 5. Verify Command Registration

Check that the command is registered in the setup hook:
```python
# In src/bot/bot.py, setup_hook should call:
register_relationships_command(...)
```

#### 6. Check Discord Permissions

- Ensure the bot has "Use Slash Commands" permission
- Ensure the bot is in the server and has proper permissions
- Check that the bot appears online in Discord

#### 7. Discord Cache Issues

Sometimes Discord's client cache can cause issues:
- **Discord Desktop**: Try restarting Discord
- **Discord Web**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
- **Discord Mobile**: Force close and reopen the app

#### 8. Test Command Directly

If the command appears in autocomplete but doesn't work:
- Try typing the full command: `/archive relationships person:"Test"`
- Check if it appears when typing `/archive` and then `relationships`

### Checking Command Registration

You can verify which commands are registered by checking the bot logs:

```
bot_commands_synced synced_count=5 command_names=['query', 'topics', 'people', 'list', 'relationships']
```

If `relationships` is not in the list, the command wasn't registered properly.

### Force Refresh Commands (Discord API)

If commands still don't appear after 1 hour:

1. **Go to Discord Developer Portal**: https://discord.com/developers/applications
2. **Select your bot application**
3. **Go to "OAuth2" → "URL Generator"**
4. **Re-generate the bot invite URL**
5. **Re-invite the bot** (this can sometimes force refresh commands)

### Debugging Steps

1. **Check bot is running**: The bot should be online in Discord
2. **Check logs for errors**: Look for `bot_command_sync_failed` or other errors
3. **Verify command registration**: Check that `register_relationships_command` is called
4. **Check guild sync**: Look for `bot_commands_synced_to_guild` in logs
5. **Wait for global sync**: Can take up to 1 hour for global commands

### Expected Behavior

After restarting the bot:
- Commands sync to each guild immediately (for testing)
- Global sync happens in background (can take up to 1 hour)
- Command should appear in Discord within a few minutes (guild sync) or up to 1 hour (global sync)

### If Still Not Working

1. Check the bot console output for any errors
2. Verify the command code is correct (no syntax errors)
3. Ensure the bot has the latest code changes
4. Try removing and re-adding the bot to your server
5. Check Discord's status page for API issues



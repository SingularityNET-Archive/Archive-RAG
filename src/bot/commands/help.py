"""Help command handler for /archive help slash command."""

import discord
from discord import app_commands

from ..bot import ArchiveRAGBot
from src.lib.logging import get_logger

logger = get_logger(__name__)


def register_help_command(bot: ArchiveRAGBot) -> None:
    """
    Register /archive help command with Discord bot.
    
    Args:
        bot: Discord bot client
    """
    # Get or create the archive command group
    archive_group = None
    for command in bot.tree.get_commands():
        if command.name == "archive":
            archive_group = command
            break
    
    if archive_group is None:
        # Create archive group if it doesn't exist
        archive_group = app_commands.Group(name="archive", description="Archive-RAG commands")
        bot.tree.add_command(archive_group)
    
    # Register help command
    @archive_group.command(name="help", description="Show available commands and examples")
    async def help_command(interaction: discord.Interaction):
        """Execute /archive help command."""
        try:
            # Send first message with public commands
            public_commands = """**Archive-RAG Bot Commands**

**Public Commands:**
• `/archive query` - Ask questions about meetings
  Example: `/archive query query:"What topics has the Archive Workgroup discussed in 2025?"`
  
• `/archive list` - List topics or meetings
  Example: `/archive list query:"List all topics"`
  
• `/archive relationships` - Query entity relationships
  Example: `/archive relationships person:"Stephen"`
  
• `/archive topics` - Search for topics/tags
  Example: `/archive topics topic:"budget"`
  
• `/archive people` - Search for people
  Example: `/archive people person:"Stephen"`"""

            await interaction.response.send_message(public_commands)
            
            # Send second message with admin commands and tips
            admin_commands = """**Admin Commands:**
• `/archive reports` - View issue reports
  Example: `/archive reports`

**Tips:**
• Use quotes for multi-word parameters
• Rate limit: 10 queries/minute
• Use "Report Issue" button if information is incorrect"""

            await interaction.followup.send(admin_commands)
            
            logger.info(
                "help_command_executed",
                user_id=str(interaction.user.id),
                username=interaction.user.name
            )
            
        except Exception as e:
            logger.error("help_command_error", error=str(e))
            try:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ An error occurred while displaying help. Please try again.")
                else:
                    await interaction.response.send_message("❌ An error occurred while displaying help. Please try again.")
            except Exception as send_error:
                logger.error("failed_to_send_error_message", error=str(send_error))


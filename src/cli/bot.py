"""Bot CLI command for starting the Discord bot."""

import asyncio
from typing import Optional

import typer

from ..bot.bot import create_bot, run_bot
from ..bot.config import get_discord_token, get_index_path, validate_config
from ..lib.logging import get_logger

logger = get_logger(__name__)


def bot_command(
    token: Optional[str] = typer.Option(
        None,
        "--token",
        help="Discord bot token (overrides DISCORD_BOT_TOKEN env var)"
    ),
    index_name: Optional[str] = typer.Option(
        None,
        "--index-name",
        help="RAG index name (overrides INDEX_NAME env var)"
    )
):
    """
    Start the Discord bot for Archive-RAG.
    
    The bot allows users to query the Archive-RAG system using Discord slash commands.
    """
    try:
        # Validate configuration
        validate_config()
        
        # Get Discord token (from env var or command line)
        discord_token = token or get_discord_token()
        if not discord_token:
            typer.echo("Error: Discord bot token not provided. Set DISCORD_BOT_TOKEN env var or use --token option.", err=True)
            raise typer.Exit(1)
        
        # Get index name (from env var or command line)
        rag_index_name = index_name or get_index_path()
        
        typer.echo(f"Starting Discord bot with index: {rag_index_name}")
        
        # Create bot instance
        bot = create_bot(index_name=rag_index_name)
        
        # Run bot (blocking)
        asyncio.run(run_bot(token=discord_token, bot=bot))
        
    except KeyboardInterrupt:
        typer.echo("\nBot stopped by user.")
        logger.info("bot_stopped_by_user")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        logger.error("bot_command_failed", error=str(e))
        raise typer.Exit(1)



"""Main Discord bot client for Archive-RAG."""

import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import tasks

from .config import get_discord_token, get_index_path, validate_config
from .services.rate_limiter import RateLimiter, create_rate_limiter
from .services.permission_checker import PermissionChecker, create_permission_checker
from .services.async_query_service import AsyncQueryService, create_async_query_service
from .services.message_formatter import MessageFormatter, create_message_formatter
from src.services.audit_writer import AuditWriter
from src.services.entity_query import EntityQueryService
from src.lib.logging import get_logger

logger = get_logger(__name__)


class ArchiveRAGBot(discord.Client):
    """
    Discord bot client for Archive-RAG.
    
    Handles Discord connection, command registration, and message processing.
    """
    
    def __init__(
        self,
        *,
        intents: discord.Intents,
        index_name: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
        permission_checker: Optional[PermissionChecker] = None,
        async_query_service: Optional[AsyncQueryService] = None
    ):
        """
        Initialize Discord bot.
        
        Args:
            intents: Discord intents (required for bot functionality)
            index_name: Optional RAG index name (uses default if not provided)
            rate_limiter: Optional rate limiter instance (creates new if not provided)
            permission_checker: Optional permission checker instance (creates new if not provided)
            async_query_service: Optional async query service instance (creates new if not provided)
        """
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        
        # Initialize services
        self.index_name = index_name or get_index_path()
        self.rate_limiter = rate_limiter or create_rate_limiter()
        self.permission_checker = permission_checker or create_permission_checker()
        self.async_query_service = async_query_service or create_async_query_service(
            index_name=self.index_name
        )
        self.message_formatter = create_message_formatter()
        self.audit_writer = AuditWriter()
        self.entity_query_service = EntityQueryService()
        
        # Command handlers will be registered here
        self._commands_registered = False
    
    async def setup_hook(self) -> None:
        """
        Setup hook called when bot is starting up.
        
        Registers slash commands with Discord.
        """
        logger.info("bot_setup_hook", index_name=self.index_name)
        
        # Register commands
        if not self._commands_registered:
            from .commands.query import register_query_command
            from .commands.topics import register_topics_command
            from .commands.people import register_people_command
            
            # Register query command
            register_query_command(
                bot=self,
                rate_limiter=self.rate_limiter,
                permission_checker=self.permission_checker,
                async_query_service=self.async_query_service,
                message_formatter=self.message_formatter,
                audit_writer=self.audit_writer,
                index_name=self.index_name
            )
            
            # Register topics command
            register_topics_command(
                bot=self,
                rate_limiter=self.rate_limiter,
                permission_checker=self.permission_checker,
                message_formatter=self.message_formatter,
                entity_query_service=self.entity_query_service
            )
            
            # Register people command
            register_people_command(
                bot=self,
                rate_limiter=self.rate_limiter,
                permission_checker=self.permission_checker,
                message_formatter=self.message_formatter,
                entity_query_service=self.entity_query_service
            )
            
            # Register list command
            from .commands.list import register_list_command
            register_list_command(
                bot=self,
                rate_limiter=self.rate_limiter,
                permission_checker=self.permission_checker,
                message_formatter=self.message_formatter,
                entity_query_service=self.entity_query_service
            )
            
            self._commands_registered = True
    
    async def on_ready(self) -> None:
        """
        Event handler called when bot is ready.
        
        Logs connection status and syncs command tree.
        """
        logger.info(
            "bot_ready",
            bot_user=str(self.user),
            bot_user_id=str(self.user.id) if self.user else None,
            guild_count=len(self.guilds),
            guild_names=[guild.name for guild in self.guilds] if self.guilds else [],
            index_name=self.index_name
        )
        
        # Sync command tree with Discord
        try:
            synced = await self.tree.sync()
            synced_command_names = [cmd.name for cmd in synced]
            logger.info(
                "bot_commands_synced",
                synced_count=len(synced),
                command_names=synced_command_names
            )
        except Exception as e:
            logger.error("bot_command_sync_failed", error=str(e))
        
        # Start background tasks
        self.rate_limiter_cleanup.start()
        logger.debug("bot_background_tasks_started")
    
    async def on_error(self, event: str, *args, **kwargs) -> None:
        """
        Event handler for errors.
        
        Args:
            event: Event name that caused the error
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        logger.error("bot_error", event=event, args=args, kwargs=kwargs)
    
    @tasks.loop(minutes=5.0)
    async def rate_limiter_cleanup(self) -> None:
        """
        Background task to clean up expired rate limit entries.
        
        Runs every 5 minutes to remove stale entries.
        """
        try:
            # Get cleanup stats if available
            entries_before = len(self.rate_limiter._rate_limits) if hasattr(self.rate_limiter, '_rate_limits') else None
            self.rate_limiter.cleanup_expired_entries()
            entries_after = len(self.rate_limiter._rate_limits) if hasattr(self.rate_limiter, '_rate_limits') else None
            
            if entries_before is not None and entries_after is not None:
                cleaned = entries_before - entries_after
                logger.debug(
                    "rate_limiter_cleanup_completed",
                    entries_before=entries_before,
                    entries_after=entries_after,
                    entries_cleaned=cleaned
                )
            else:
                logger.debug("rate_limiter_cleanup_completed")
        except Exception as e:
            logger.error("rate_limiter_cleanup_failed", error=str(e))
    
    @rate_limiter_cleanup.before_loop
    async def before_rate_limiter_cleanup(self) -> None:
        """Wait until bot is ready before starting cleanup task."""
        await self.wait_until_ready()
    
    async def close(self) -> None:
        """Cleanup when bot is closing."""
        logger.info("bot_closing")
        self.rate_limiter_cleanup.cancel()
        await super().close()


def create_bot(
    index_name: Optional[str] = None,
    rate_limiter: Optional[RateLimiter] = None,
    permission_checker: Optional[PermissionChecker] = None,
    async_query_service: Optional[AsyncQueryService] = None
) -> ArchiveRAGBot:
    """
    Create a Discord bot instance.
    
    Args:
        index_name: Optional RAG index name
        rate_limiter: Optional rate limiter instance
        permission_checker: Optional permission checker instance
        async_query_service: Optional async query service instance
        
    Returns:
        ArchiveRAGBot instance
    """
    # Configure intents
    intents = discord.Intents.default()
    intents.message_content = False  # Not needed for slash commands
    intents.members = True  # Needed for role checking
    
    return ArchiveRAGBot(
        intents=intents,
        index_name=index_name,
        rate_limiter=rate_limiter,
        permission_checker=permission_checker,
        async_query_service=async_query_service
    )


async def run_bot(token: str, bot: Optional[ArchiveRAGBot] = None) -> None:
    """
    Run the Discord bot.
    
    Args:
        token: Discord bot token
        bot: Optional bot instance (creates new if not provided)
    """
    if bot is None:
        bot = create_bot()
    
    try:
        logger.info("bot_starting")
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("bot_login_failed", message="Invalid Discord bot token")
        raise
    except Exception as e:
        logger.error("bot_run_failed", error=str(e))
        raise
    finally:
        await bot.close()


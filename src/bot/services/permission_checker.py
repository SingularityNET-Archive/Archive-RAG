"""Permission checker service for role-based access control."""

from typing import List, Optional

from ..models.discord_user import DiscordUser
from ...lib.logging import get_logger

logger = get_logger(__name__)


class PermissionChecker:
    """
    Permission checker service for role-based access control.
    
    Enforces role-based permissions for Discord bot commands:
    - Public: Access to `/archive query` only
    - Contributor: Access to `/archive query`, `/archive topics`, `/archive people`
    - Admin: All contributor access + `/archive stats` (future)
    """
    
    # Command to role mapping
    COMMAND_ROLES: dict[str, List[str]] = {
        "archive query": [],  # Public (empty list = public access)
        "archive topics": ["contributor", "admin"],
        "archive people": ["contributor", "admin"],
        "archive stats": ["admin"],  # Future admin command
    }
    
    def __init__(self):
        """Initialize permission checker."""
        pass
    
    def has_permission(self, user: DiscordUser, command_name: str) -> bool:
        """
        Check if user has permission to execute a command.
        
        Args:
            user: DiscordUser model with roles
            command_name: Command name (e.g., "archive query")
            
        Returns:
            True if user has permission, False otherwise
        """
        required_roles = self.COMMAND_ROLES.get(command_name, [])
        
        # Empty list means public access (everyone can use)
        if not required_roles:
            return True
        
        # Check if user has any of the required roles
        user_roles = set(user.roles)
        required_roles_set = set(required_roles)
        
        has_permission = bool(user_roles & required_roles_set)
        
        if not has_permission:
            logger.debug(
                "permission_denied",
                user_id=user.user_id,
                username=user.username,
                command=command_name,
                user_roles=user.roles,
                required_roles=required_roles
            )
        
        return has_permission
    
    def get_permission_error_message(self, command_name: str) -> str:
        """
        Get user-friendly error message for permission denied.
        
        Args:
            command_name: Command name that was denied
            
        Returns:
            Error message string
        """
        required_roles = self.COMMAND_ROLES.get(command_name, [])
        
        if "admin" in required_roles:
            return "This command requires admin role."
        elif "contributor" in required_roles:
            return "This command requires contributor role. Contact an admin if you need access."
        else:
            return "You do not have permission to use this command."


def create_permission_checker() -> PermissionChecker:
    """
    Create a permission checker instance.
    
    Returns:
        PermissionChecker instance
    """
    return PermissionChecker()


"""Discord user model for bot authentication and authorization."""

from typing import List
from pydantic import BaseModel, Field, computed_field


class DiscordUser(BaseModel):
    """
    Represents a Discord user accessing the bot with their roles and permissions.
    
    This model is created from Discord interactions and is not persisted.
    It is used for permission checking and rate limiting.
    """
    
    user_id: str = Field(..., description="Discord user ID (Discord snowflake)")
    username: str = Field(..., description="Discord username", min_length=1)
    roles: List[str] = Field(default_factory=list, description="List of Discord role names")
    
    @computed_field
    @property
    def is_public(self) -> bool:
        """True if user has no special roles (default access)."""
        return not self.is_contributor and not self.is_admin
    
    @computed_field
    @property
    def is_contributor(self) -> bool:
        """True if user has 'contributor' role."""
        return "contributor" in self.roles
    
    @computed_field
    @property
    def is_admin(self) -> bool:
        """True if user has 'admin' role."""
        return "admin" in self.roles
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "user_id": "123456789012345678",
                "username": "alice",
                "roles": ["contributor"],
                "is_public": False,
                "is_contributor": True,
                "is_admin": False,
            }
        }



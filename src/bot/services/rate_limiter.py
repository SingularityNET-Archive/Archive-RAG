"""Rate limiter service for per-user query limits."""

from collections import deque
from datetime import datetime
from typing import Dict, Optional, Tuple
import threading

from ..config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
from ...lib.logging import get_logger

logger = get_logger(__name__)


class RateLimitEntry:
    """
    Rate limit tracking entry for a Discord user.
    
    Uses a deque to track timestamps of recent queries within a time window.
    """
    
    def __init__(self, user_id: str, limit: int = RATE_LIMIT_PER_MINUTE, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        """
        Initialize rate limit entry.
        
        Args:
            user_id: Discord user ID
            limit: Maximum queries allowed per window
            window_seconds: Time window in seconds
        """
        self.user_id = user_id
        self.query_timestamps: deque = deque()
        self.limit = limit
        self.window_seconds = window_seconds
        self.last_cleanup: Optional[datetime] = None
        self._lock = threading.Lock()
    
    def cleanup_expired(self, current_time: datetime) -> None:
        """
        Remove expired timestamps from the deque.
        
        Args:
            current_time: Current timestamp to compare against
        """
        cutoff_time = current_time.timestamp() - self.window_seconds
        
        # Remove timestamps older than the window
        while self.query_timestamps and self.query_timestamps[0].timestamp() < cutoff_time:
            self.query_timestamps.popleft()
        
        self.last_cleanup = current_time
    
    def is_allowed(self, current_time: datetime) -> Tuple[bool, Optional[float]]:
        """
        Check if user is allowed to make a query.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Tuple of (is_allowed, remaining_seconds_until_reset)
            remaining_seconds is None if allowed, or seconds until oldest query expires
        """
        with self._lock:
            self.cleanup_expired(current_time)
            
            if len(self.query_timestamps) < self.limit:
                return True, None
            
            # Rate limit exceeded, calculate remaining time
            oldest_timestamp = self.query_timestamps[0]
            reset_time = oldest_timestamp.timestamp() + self.window_seconds
            remaining_seconds = max(0, reset_time - current_time.timestamp())
            
            return False, remaining_seconds
    
    def add_query(self, current_time: datetime) -> None:
        """
        Add a query timestamp to the deque.
        
        Args:
            current_time: Current timestamp
        """
        with self._lock:
            self.cleanup_expired(current_time)
            self.query_timestamps.append(current_time)


class RateLimiter:
    """
    Rate limiter service for enforcing per-user query limits.
    
    Uses in-memory token bucket with time-window tracking.
    """
    
    def __init__(self, limit: int = RATE_LIMIT_PER_MINUTE, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        """
        Initialize rate limiter.
        
        Args:
            limit: Maximum queries allowed per window per user
            window_seconds: Time window in seconds
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self._rate_limits: Dict[str, RateLimitEntry] = {}
        self._lock = threading.Lock()
    
    def check_rate_limit(self, user_id: str) -> Tuple[bool, Optional[float]]:
        """
        Check if user is allowed to make a query.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (is_allowed, remaining_seconds_until_reset)
            remaining_seconds is None if allowed, or seconds until oldest query expires
        """
        current_time = datetime.utcnow()
        
        with self._lock:
            if user_id not in self._rate_limits:
                self._rate_limits[user_id] = RateLimitEntry(user_id, self.limit, self.window_seconds)
            
            entry = self._rate_limits[user_id]
        
        return entry.is_allowed(current_time)
    
    def record_query(self, user_id: str) -> None:
        """
        Record a query for rate limiting.
        
        Args:
            user_id: Discord user ID
        """
        current_time = datetime.utcnow()
        
        with self._lock:
            if user_id not in self._rate_limits:
                self._rate_limits[user_id] = RateLimitEntry(user_id, self.limit, self.window_seconds)
            
            entry = self._rate_limits[user_id]
        
        entry.add_query(current_time)
    
    def cleanup_expired_entries(self) -> None:
        """
        Clean up expired rate limit entries (call periodically).
        
        Removes entries for users with no recent queries.
        """
        current_time = datetime.utcnow()
        cutoff_time = current_time.timestamp() - (self.window_seconds * 2)  # Keep entries for 2 windows
        
        with self._lock:
            expired_users = []
            for user_id, entry in self._rate_limits.items():
                entry.cleanup_expired(current_time)
                # Remove if no recent queries and last cleanup was more than 2 windows ago
                if (not entry.query_timestamps and 
                    entry.last_cleanup and 
                    entry.last_cleanup.timestamp() < cutoff_time):
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self._rate_limits[user_id]
                logger.debug("rate_limit_entry_cleaned", user_id=user_id)


def create_rate_limiter(
    limit: int = RATE_LIMIT_PER_MINUTE,
    window_seconds: int = RATE_LIMIT_WINDOW_SECONDS
) -> RateLimiter:
    """
    Create a rate limiter instance.
    
    Args:
        limit: Maximum queries allowed per window per user
        window_seconds: Time window in seconds
        
    Returns:
        RateLimiter instance
    """
    return RateLimiter(limit, window_seconds)


"""Bot services for Discord bot interface."""

# Import existing services
from .async_query_service import AsyncQueryService, create_async_query_service
from .message_formatter import MessageFormatter, create_message_formatter
from .permission_checker import PermissionChecker, create_permission_checker
from .rate_limiter import RateLimiter, create_rate_limiter

# Import new services for entity extraction enhancements
from ...services.entity_normalization import EntityNormalizationService
from ...services.relationship_triple_generator import RelationshipTripleGenerator
try:
    from ...services.semantic_chunking import SemanticChunkingService
except ImportError:
    # Fallback if semantic_chunking module doesn't exist yet
    SemanticChunkingService = None

# Import new bot-specific services
from .enhanced_citation_formatter import EnhancedCitationFormatter, create_enhanced_citation_formatter
from .issue_reporting_service import IssueReportingService, create_issue_reporting_service
from .relationship_query_service import RelationshipQueryService, create_relationship_query_service
from .issue_storage import IssueStorage, create_issue_storage

__all__ = [
    "AsyncQueryService",
    "create_async_query_service",
    "MessageFormatter",
    "create_message_formatter",
    "PermissionChecker",
    "create_permission_checker",
    "RateLimiter",
    "create_rate_limiter",
    # Entity extraction services
    "EntityNormalizationService",
    "RelationshipTripleGenerator",
    "SemanticChunkingService",
    # New bot services
    "EnhancedCitationFormatter",
    "create_enhanced_citation_formatter",
    "IssueReportingService",
    "create_issue_reporting_service",
    "RelationshipQueryService",
    "create_relationship_query_service",
    "IssueStorage",
    "create_issue_storage",
]


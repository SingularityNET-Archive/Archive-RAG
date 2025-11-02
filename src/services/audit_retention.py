"""Audit log retention logic (3-year retention per FR-014)."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from ..lib.config import AUDIT_RETENTION_DAYS, AUDIT_LOGS_DIR
from ..lib.audit import list_audit_logs
from ..lib.logging import get_logger

logger = get_logger(__name__)


class AuditRetentionService:
    """Service for managing audit log retention."""
    
    def __init__(self, retention_days: int = AUDIT_RETENTION_DAYS):
        """
        Initialize audit retention service.
        
        Args:
            retention_days: Number of days to retain logs (default: 3 years)
        """
        self.retention_days = retention_days
        self.retention_threshold = datetime.utcnow() - timedelta(days=retention_days)
    
    def list_expired_logs(self, log_dir: Optional[Path] = None) -> List[Path]:
        """
        List audit logs that have expired based on retention policy.
        
        Args:
            log_dir: Directory to scan (default: AUDIT_LOGS_DIR)
            
        Returns:
            List of expired log file paths
        """
        if log_dir is None:
            log_dir = AUDIT_LOGS_DIR
        
        all_logs = list_audit_logs(log_dir)
        expired_logs = []
        
        for log_path in all_logs:
            try:
                # Check file modification time
                mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
                if mtime < self.retention_threshold:
                    expired_logs.append(log_path)
            except Exception as e:
                logger.warning(
                    "log_retention_check_failed",
                    log_path=str(log_path),
                    error=str(e)
                )
        
        logger.info(
            "expired_logs_listed",
            total_logs=len(all_logs),
            expired_logs=len(expired_logs)
        )
        
        return expired_logs
    
    def delete_expired_logs(self, log_dir: Optional[Path] = None, dry_run: bool = False) -> int:
        """
        Delete expired audit logs.
        
        Args:
            log_dir: Directory to scan (default: AUDIT_LOGS_DIR)
            dry_run: If True, only list logs without deleting
            
        Returns:
            Number of logs deleted (or would be deleted in dry run)
        """
        expired_logs = self.list_expired_logs(log_dir)
        
        if dry_run:
            logger.info(
                "expired_logs_listed_dry_run",
                count=len(expired_logs)
            )
            return len(expired_logs)
        
        deleted_count = 0
        for log_path in expired_logs:
            try:
                log_path.unlink()
                deleted_count += 1
                logger.info("expired_log_deleted", log_path=str(log_path))
            except Exception as e:
                logger.error(
                    "log_deletion_failed",
                    log_path=str(log_path),
                    error=str(e)
                )
        
        logger.info(
            "expired_logs_deleted",
            deleted_count=deleted_count,
            total_expired=len(expired_logs)
        )
        
        return deleted_count


def create_audit_retention_service(retention_days: int = AUDIT_RETENTION_DAYS) -> AuditRetentionService:
    """
    Create an audit retention service instance.
    
    Args:
        retention_days: Number of days to retain logs
        
    Returns:
        AuditRetentionService instance
    """
    return AuditRetentionService(retention_days)


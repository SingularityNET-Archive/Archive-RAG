"""Audit-view CLI command for viewing and analyzing audit logs."""

from pathlib import Path
from typing import Optional
import typer
import json
from datetime import datetime

from ..lib.audit import list_audit_logs, read_audit_log
from ..lib.config import AUDIT_LOGS_DIR
from ..lib.logging import get_logger

logger = get_logger(__name__)


def audit_view_command(
    log_file: Optional[Path] = typer.Argument(None, help="Path to specific audit log file"),
    query_id: Optional[str] = typer.Option(None, "--query-id", help="Filter by query ID"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="Filter by user ID"),
    date_from: Optional[str] = typer.Option(None, "--date-from", help="Filter logs from date (ISO 8601)"),
    date_to: Optional[str] = typer.Option(None, "--date-to", help="Filter logs to date (ISO 8601)"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    export: Optional[Path] = typer.Option(None, "--export", help="Export filtered logs to file")
):
    """
    View and analyze audit logs.
    """
    try:
        if log_file:
            # View specific log file
            audit_data = read_audit_log(log_file.stem)
            
            if output_format == "json":
                typer.echo(json.dumps(audit_data, indent=2))
            else:
                # Text format
                _display_audit_log_text(audit_data)
        else:
            # List and filter logs
            all_logs = list_audit_logs()
            filtered_logs = _filter_logs(
                all_logs,
                query_id=query_id,
                user_id=user_id,
                date_from=date_from,
                date_to=date_to
            )
            
            if export:
                # Export to file
                export_data = []
                for log_path in filtered_logs:
                    try:
                        audit_data = read_audit_log(log_path.stem)
                        export_data.append(audit_data)
                    except Exception as e:
                        logger.warning("log_read_failed", log_path=str(log_path), error=str(e))
                
                with open(export, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                typer.echo(f"Exported {len(export_data)} logs to {export}")
            else:
                # Display logs
                if output_format == "json":
                    export_data = []
                    for log_path in filtered_logs:
                        try:
                            audit_data = read_audit_log(log_path.stem)
                            export_data.append(audit_data)
                        except Exception as e:
                            logger.warning("log_read_failed", log_path=str(log_path), error=str(e))
                    typer.echo(json.dumps(export_data, indent=2))
                else:
                    # Text format
                    typer.echo(f"Audit Logs ({len(filtered_logs)} entries):")
                    typer.echo("")
                    for log_path in filtered_logs[:50]:  # Limit to first 50
                        try:
                            audit_data = read_audit_log(log_path.stem)
                            _display_audit_log_summary(audit_data)
                        except Exception as e:
                            logger.warning("log_read_failed", log_path=str(log_path), error=str(e))
    
    except Exception as e:
        logger.error("audit_view_failed", error=str(e))
        typer.echo(f"Audit view failed: {e}", err=True)
        raise typer.Exit(code=1)


def _filter_logs(
    log_paths: list[Path],
    query_id: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> list[Path]:
    """Filter audit logs by criteria."""
    filtered = []
    
    for log_path in log_paths:
        try:
            audit_data = read_audit_log(log_path.stem)
            
            # Filter by query_id
            if query_id and audit_data.get("query_id") != query_id:
                continue
            
            # Filter by user_id
            if user_id and audit_data.get("user_id") != user_id:
                continue
            
            # Filter by date range
            timestamp = audit_data.get("timestamp")
            if timestamp:
                try:
                    log_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    
                    if date_from:
                        from_date = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                        if log_date < from_date:
                            continue
                    
                    if date_to:
                        to_date = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                        if log_date > to_date:
                            continue
                except (ValueError, TypeError):
                    pass
            
            filtered.append(log_path)
        except Exception:
            # Skip logs that can't be read
            continue
    
    return filtered


def _display_audit_log_text(audit_data: dict):
    """Display audit log in text format."""
    typer.echo(f"Query ID: {audit_data.get('query_id', 'N/A')}")
    typer.echo(f"User: {audit_data.get('user_id', 'N/A')}")
    typer.echo(f"Timestamp: {audit_data.get('timestamp', 'N/A')}")
    typer.echo(f"Query: {audit_data.get('user_input', 'N/A')}")
    typer.echo(f"Evidence Found: {audit_data.get('evidence_found', 'N/A')}")
    typer.echo(f"Citations: {len(audit_data.get('citations', []))}")
    typer.echo(f"Model Version: {audit_data.get('model_version', 'N/A')}")
    typer.echo(f"Answer: {audit_data.get('output', 'N/A')}")
    typer.echo("")


def _display_audit_log_summary(audit_data: dict):
    """Display audit log summary."""
    typer.echo(f"- Query ID: {audit_data.get('query_id', 'N/A')}")
    typer.echo(f"  User: {audit_data.get('user_id', 'N/A')}")
    typer.echo(f"  Timestamp: {audit_data.get('timestamp', 'N/A')}")
    typer.echo(f"  Query: {audit_data.get('user_input', 'N/A')[:100]}...")
    typer.echo("")


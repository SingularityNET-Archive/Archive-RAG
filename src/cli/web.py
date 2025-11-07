"""Web server CLI command."""

import typer
from ..web.app import run_server


def web_command(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False
):
    """Start the FastAPI web server."""
    typer.echo(f"Starting Archive-RAG web server on http://{host}:{port}")
    typer.echo("Press CTRL+C to stop")
    run_server(host=host, port=port, reload=reload)



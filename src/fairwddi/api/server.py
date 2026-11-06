"""Standalone WSGI web server runner for FAIRwDDI API & Visual Explorer."""

from __future__ import annotations

import webbrowser
from threading import Timer

from fairwddi.db.config import configure_django_for_cli

configure_django_for_cli()

import django.core.servers.basehttp as basehttp
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from rich.console import Console

console = Console()


def run_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = False) -> None:
    """Launch the FAIRwDDI API and Visual Explorer development server."""
    configure_django_for_cli()

    # Ensure ROOT_URLCONF points to fairwddi.api.urls
    if not hasattr(settings, "ROOT_URLCONF") or not settings.ROOT_URLCONF:
        settings.ROOT_URLCONF = "fairwddi.api.urls"

    app_url = f"http://{host}:{port}/explorer"
    docs_url = f"http://{host}:{port}/api/docs"
    api_url = f"http://{host}:{port}/api"

    console.print("\n[bold green]FAIRwDDI Question Bank & Harmonization Server[/bold green]")
    console.print(f"  • [bold]Visual Explorer:[/bold] [cyan]{app_url}[/cyan]")
    console.print(f"  • [bold]Swagger API Docs:[/bold] [cyan]{docs_url}[/cyan]")
    console.print(f"  • [bold]REST API Base:[/bold]    [cyan]{api_url}[/cyan]\n")
    console.print("[dim]Press Ctrl+C to stop the server.[/dim]\n")

    if open_browser:
        Timer(1.0, lambda: webbrowser.open(app_url)).start()

    application = get_wsgi_application()
    basehttp.run(host, port, application)

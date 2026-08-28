"""FAIRwDDI Lifecycle CLI application using Typer and Rich."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import fairwddi
from fairwddi.db.config import configure_django_for_cli, get_database_config
from fairwddi.db.ddl import export_postgres_ddl
from fairwddi.db.seed import seed_sample_data

app = typer.Typer(
    name="fairwddi",
    help="FAIR DDI-Lifecycle CLI for social science question bank interoperability.",
    no_args_is_help=True,
)
db_app = typer.Typer(
    name="db",
    help="Database management, migrations, seeding, and DDL export commands.",
    no_args_is_help=True,
)
app.add_typer(db_app, name="db")

console = Console()


def version_callback(value: bool) -> None:
    """Print the version of fairwddi and exit."""
    if value:
        ver = fairwddi.__version__
        console.print(f"[bold green]fairwddi[/bold green] version [bold cyan]{ver}[/bold cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show fairwddi version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """FAIRwDDI Lifecycle management CLI tool."""
    pass


@app.command()
def version() -> None:
    """Display the version of fairwddi."""
    ver = fairwddi.__version__
    console.print(f"[bold green]fairwddi[/bold green] version [bold cyan]{ver}[/bold cyan]")


@app.command()
def info() -> None:
    """Display information about the fairwddi environment and resolved database config."""
    db_config = get_database_config()
    db_engine = db_config.get("ENGINE", "").split(".")[-1]
    db_name = db_config.get("NAME", "")
    db_host = db_config.get("HOST", "")
    db_target = f"{db_name} (host: {db_host})" if db_host else db_name

    console.print(
        Panel.fit(
            f"[bold green]FAIRwDDI Lifecycle[/bold green]\n"
            f"[dim]Version:[/dim] {fairwddi.__version__}\n"
            f"[dim]Active DB Engine:[/dim] [cyan]{db_engine}[/cyan]\n"
            f"[dim]Active DB Target:[/dim] [yellow]{db_target}[/yellow]\n"
            f"[dim]Target Specification:[/dim] PostgreSQL >= 17 (DDI 4 / DDI-CDI / DDI-L)\n"
            f"[dim]Multilingual Format:[/dim] JSONB Array of Objects",
            title="Environment & Configuration Info",
            border_style="cyan",
        )
    )


@db_app.command("export-ddl")
def export_ddl(
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination file path to save the PostgreSQL DDL script.",
    ),
) -> None:
    """Export the standalone PostgreSQL >= 17 SQL DDL script."""
    sql = export_postgres_ddl(output)
    if output:
        console.print(f"[bold green]Success:[/bold green] DDL written to [cyan]{output}[/cyan]")
    else:
        console.print(sql)


@db_app.command("init")
def db_init() -> None:
    """Initialize the database by running pending Django migrations."""
    from django.core.management import call_command

    configure_django_for_cli()
    console.print("[dim]Applying database migrations...[/dim]")
    call_command("migrate", interactive=False, verbosity=1)
    console.print("[bold green]Database initialized successfully.[/bold green]")


@db_app.command("seed")
def db_seed(
    reset: bool = typer.Option(
        False,
        "--reset",
        "-r",
        help="Clear existing data before seeding demonstration records.",
    ),
) -> None:
    """Seed the database with standard DDI demonstration entities."""
    from django.core.management import call_command

    configure_django_for_cli()
    call_command("migrate", interactive=False, verbosity=0)

    console.print("[dim]Seeding DDI-Lifecycle demonstration data...[/dim]")
    summary = seed_sample_data(reset=reset)

    table = Table(title="Demonstration Data Seed Summary", border_style="green")
    table.add_column("Entity / Layer", style="bold cyan")
    table.add_column("Count", justify="right", style="yellow")

    for key, count in summary.items():
        table.add_row(key.replace("_", " ").title(), str(count))

    console.print(table)
    console.print("[bold green]Database seeded successfully.[/bold green]")


@db_app.command("status")
def db_status() -> None:
    """Display database connection status and model table inventory."""
    from django.apps import apps
    from django.core.management import call_command

    configure_django_for_cli()
    call_command("migrate", interactive=False, verbosity=0)

    db_config = get_database_config()
    db_engine = db_config.get("ENGINE", "").split(".")[-1]
    db_name = db_config.get("NAME", "")

    table = Table(
        title=f"FAIRwDDI Model Inventory [{db_engine}: {db_name}]",
        border_style="cyan",
    )
    table.add_column("Model Name", style="bold green")
    table.add_column("Database Table", style="cyan")
    table.add_column("Record Count", justify="right", style="yellow")

    app_config = apps.get_app_config("fairwddi")
    for model in app_config.get_models():
        count = model.objects.count()
        table.add_row(model.__name__, model._meta.db_table, str(count))

    console.print(table)


@db_app.command("wipe")
def db_wipe(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Bypass string confirmation prompt.",
    ),
    confirm: str | None = typer.Option(
        None,
        "--confirm",
        help="Pass confirmation string directly (must equal 'WIPE').",
    ),
) -> None:
    """Permanently delete ALL data in the database (requires string confirmation)."""
    from django.core.management import call_command

    from fairwddi.db.wipe import wipe_database

    configure_django_for_cli()
    call_command("migrate", interactive=False, verbosity=0)

    db_config = get_database_config()
    db_engine = db_config.get("ENGINE", "").split(".")[-1]
    db_name = db_config.get("NAME", "")

    if not force:
        confirmation_input = confirm
        if confirmation_input is None:
            console.print(
                f"[bold red]⚠️  WARNING:[/bold red] You are about to permanently delete "
                f"[bold red]ALL records[/bold red] from [cyan]{db_engine}[/cyan] database "
                f"[yellow]{db_name}[/yellow]!"
            )
            confirmation_input = typer.prompt(
                "Type 'WIPE' to confirm complete database erasure",
                type=str,
            )

        if confirmation_input.strip() != "WIPE":
            console.print(
                "[yellow]Aborted. Confirmation did not match 'WIPE'. "
                "Database was not modified.[/yellow]"
            )
            raise typer.Abort()

    console.print("[dim]Wiping database records...[/dim]")
    summary = wipe_database()

    table = Table(title=f"Wipe Summary [{db_engine}: {db_name}]", border_style="red")
    table.add_column("Entity / Table", style="bold red")
    table.add_column("Deleted Count", justify="right", style="yellow")

    total_deleted = 0
    for key, count in summary.items():
        if count > 0:
            table.add_row(key.replace("_", " ").title(), str(count))
            total_deleted += count

    if total_deleted > 0:
        console.print(table)
        console.print(
            f"[bold green]Database wiped successfully "
            f"({total_deleted} records removed).[/bold green]"
        )
    else:
        console.print("[green]Database was already empty (0 records removed).[/green]")


@db_app.command("load-vocab")
def db_load_vocab(
    file_path: str = typer.Argument(
        "vocab/ELSST_R6.ttl",
        help="Path to RDF vocabulary file (.ttl, .rdf, .xml, .jsonld, .nt, etc.).",
    ),
    levels: int | None = typer.Option(
        None,
        "--levels",
        "-l",
        help="Limit hierarchy depth (1 for top concepts, 2 for top + level 1, etc.).",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Force reload / overwrite concepts if already loaded.",
    ),
    vocabulary: str | None = typer.Option(
        None,
        "--vocabulary",
        "-v",
        help="Vocabulary name / scheme (inferred from file/metadata if omitted).",
    ),
    rdf_format: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Explicit RDF serialization format (turtle, xml, json-ld, nt).",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Check if vocabulary is already loaded without modifying data.",
    ),
) -> None:
    """Load any SKOS / XKOS controlled vocabulary into the Concept table."""
    from django.core.management import call_command

    from fairwddi.db.vocab import check_vocabulary_loaded, load_skos_vocabulary

    configure_django_for_cli()
    call_command("migrate", interactive=False, verbosity=0)

    vocab_target = vocabulary or "ELSST"

    if check:
        status = check_vocabulary_loaded(vocabulary=vocab_target)
        if status["loaded"]:
            console.print(
                f"[bold green]Vocabulary '{vocab_target}' is LOADED:[/bold green] "
                f"{status['total_concepts']} concepts ({status['top_concepts']} top concepts), "
                f"{status['relationships']} relationships."
            )
        else:
            console.print(
                f"[yellow]Vocabulary '{vocab_target}' is NOT loaded in the database.[/yellow]"
            )
        return

    resolved_path = Path(file_path)
    if not resolved_path.exists():
        console.print(
            f"[bold red]Error:[/bold red] Vocabulary file not found: [cyan]{resolved_path}[/cyan]"
        )
        raise typer.Exit(code=1)

    console.print(
        f"[dim]Loading SKOS vocabulary from [cyan]{resolved_path}[/cyan] "
        f"(Levels: [yellow]{levels or 'ALL'}[/yellow])...[/dim]"
    )

    result = load_skos_vocabulary(
        file_path=resolved_path,
        max_levels=levels,
        reload=reload,
        vocabulary_name=vocabulary,
        rdf_format=rdf_format,
    )

    if result.get("status") == "already_loaded":
        console.print(f"[bold yellow]Notice:[/bold yellow] {result['message']}")
        return

    loaded_vocab = result["vocabulary"]
    table = Table(
        title=f"Vocabulary Load Summary [{loaded_vocab} ({result.get('format', 'rdf')})]",
        border_style="green",
    )
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", justify="right", style="yellow")

    table.add_row("Total Concepts Loaded", str(result["total_concepts"]))
    table.add_row("Top Concepts (Level 1)", str(result["top_concepts"]))
    table.add_row("Levels Traversed", str(result["levels_loaded"]))
    table.add_row("Relationships Created", str(result["relationships_created"]))
    table.add_row("Elapsed Time", f"{result['elapsed_seconds']}s")

    console.print(table)
    console.print(f"[bold green]Vocabulary '{loaded_vocab}' loaded successfully.[/bold green]")


@db_app.command("check-vocab")
def db_check_vocab(
    vocabulary: str | None = typer.Option(
        None,
        "--vocabulary",
        "-v",
        help="Name of the controlled vocabulary / scheme to check (e.g. 'ELSST').",
    ),
) -> None:
    """Check if controlled vocabularies are loaded in the database."""
    from django.core.management import call_command

    from fairwddi.db.vocab import check_vocabulary_loaded

    configure_django_for_cli()
    call_command("migrate", interactive=False, verbosity=0)

    status = check_vocabulary_loaded(vocabulary=vocabulary)
    if vocabulary:
        if status["loaded"]:
            vocab_name = status.get("vocabulary", vocabulary)
            console.print(
                f"[bold green]Vocabulary '{vocab_name}' is LOADED:[/bold green] "
                f"{status['total_concepts']} concepts ({status['top_concepts']} top concepts), "
                f"{status['relationships']} relationships."
            )
        else:
            console.print(
                f"[yellow]Vocabulary '{vocabulary}' is NOT loaded in the database.[/yellow]"
            )
    else:
        if status["loaded"]:
            table = Table(title="Loaded Controlled Vocabularies", border_style="cyan")
            table.add_column("Vocabulary Scheme", style="bold green")
            table.add_column("Concepts Count", justify="right", style="yellow")
            for item in status.get("vocabularies", []):
                table.add_row(item["vocabulary"] or "Uncategorized", str(item["total"]))
            console.print(table)
            console.print(
                f"[dim]Total Concept Records:[/dim] "
                f"[bold green]{status['total_concepts']}[/bold green]"
            )
        else:
            console.print(
                "[yellow]No controlled vocabularies are currently loaded in the database.[/yellow]"
            )


if __name__ == "__main__":
    app()

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

import_app = typer.Typer(
    name="import",
    help="Metadata document import, staging, profiles, and logs (legacy alias for stage).",
    no_args_is_help=True,
    hidden=True,
)
app.add_typer(import_app, name="import")

preflight_app = typer.Typer(
    name="preflight",
    help="Stage 1: Preflight readiness checks, profile QA, URN audits, and DDI-C upgrades.",
    no_args_is_help=True,
)
app.add_typer(preflight_app, name="preflight")

stage_app = typer.Typer(
    name="stage",
    help="Stage 2a: Load DDI-Lifecycle metadata into staging, inspect, and compact storage.",
    no_args_is_help=True,
)
app.add_typer(stage_app, name="stage")

promote_app = typer.Typer(
    name="promote",
    help="Stage 2b: Plan, apply, and undo promotion of staged resources into ReQuest core tables.",
    no_args_is_help=True,
)
app.add_typer(promote_app, name="promote")

compare_app = typer.Typer(
    name="compare",
    help="Stage 3a: Compare batches against ReQuest bank and discover harmonization candidates.",
    no_args_is_help=True,
)
app.add_typer(compare_app, name="compare")

harmonize_app = typer.Typer(
    name="harmonize",
    help="Stage 3b: Plan, apply, and undo review-gated resource harmonization.",
    no_args_is_help=True,
)
app.add_typer(harmonize_app, name="harmonize")

ingest_app = typer.Typer(
    name="ingest",
    help="End-to-end convenience pipeline orchestrating preflight, stage, promote, and harmonize.",
    no_args_is_help=True,
)
app.add_typer(ingest_app, name="ingest")

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
        help="Bypass confirmation prompt (for automated scripts).",
    ),
    confirm: str | None = typer.Option(
        None,
        "--confirm",
        help="Pass confirmation code directly.",
    ),
) -> None:
    """Permanently delete ALL data in the database (requires confirmation code)."""
    import secrets

    from django.core.management import call_command

    from fairwddi.db.wipe import wipe_database

    configure_django_for_cli()
    call_command("migrate", interactive=False, verbosity=0)

    db_config = get_database_config()
    db_engine = db_config.get("ENGINE", "").split(".")[-1]
    db_name = db_config.get("NAME", "")

    if not force:
        # Generate a random 4-digit verification code
        expected_code = str(secrets.randbelow(9000) + 1000)

        if confirm is not None:
            if confirm.strip() not in (expected_code, "WIPE"):
                console.print(
                    "[yellow]Aborted. Confirmation did not match. "
                    "Database was not modified.[/yellow]"
                )
                raise typer.Abort()
        else:
            console.print(
                f"[bold red]⚠️  WARNING:[/bold red] You are about to permanently delete "
                f"[bold red]ALL records[/bold red] from [cyan]{db_engine}[/cyan] database "
                f"[yellow]{db_name}[/yellow]!"
            )
            confirmation_input = typer.prompt(
                f"Type confirmation code '{expected_code}' to confirm complete database erasure",
                type=str,
            )

            if confirmation_input.strip() != expected_code:
                console.print(
                    f"[yellow]Aborted. Confirmation code did not match '{expected_code}'. "
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


@db_app.command("recreate")
def db_recreate(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Bypass confirmation prompt (for automated scripts).",
    ),
    seed: bool = typer.Option(
        False,
        "--seed",
        "-s",
        help="Seed demonstration data after recreating tables.",
    ),
    load_vocab: bool = typer.Option(
        False,
        "--load-vocab",
        "-v",
        help="Load top ELSST concepts into Concept table after recreation.",
    ),
) -> None:
    """Drop and recreate all database tables from scratch, re-applying all migrations."""
    import secrets
    from pathlib import Path

    from django.core.management import call_command
    from django.db import connection

    from fairwddi.db.seed import seed_sample_data
    from fairwddi.db.vocab import load_skos_vocabulary

    configure_django_for_cli()
    db_config = get_database_config()
    db_engine = db_config.get("ENGINE", "").split(".")[-1]
    db_name = db_config.get("NAME", "")

    if not force:
        expected_code = str(secrets.randbelow(9000) + 1000)
        console.print(
            f"[bold red]⚠️  WARNING:[/bold red] You are about to DROP and RECREATE "
            f"all tables in [cyan]{db_engine}[/cyan] database [yellow]{db_name}[/yellow]!"
        )
        confirmation_input = typer.prompt(
            f"Type confirmation code '{expected_code}' to confirm database recreation",
            type=str,
        )
        if confirmation_input.strip() != expected_code:
            console.print(
                f"[yellow]Aborted. Confirmation code did not match '{expected_code}'. "
                "Database was not modified.[/yellow]"
            )
            raise typer.Abort()

    console.print(f"[dim]Dropping existing schema in {db_engine} database {db_name}...[/dim]")
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    elif connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names()
            cursor.execute("PRAGMA foreign_keys = OFF;")
            for table in tables:
                cursor.execute(f'DROP TABLE IF EXISTS "{table}";')
            cursor.execute("PRAGMA foreign_keys = ON;")
        if db_name != ":memory:":
            db_path = Path(db_name)
            if db_path.exists():
                db_path.unlink(missing_ok=True)

    console.print("[dim]Applying migrations from scratch...[/dim]")
    call_command("migrate", interactive=False, verbosity=1)
    console.print("[bold green]Database schema recreated successfully.[/bold green]")

    if seed:
        console.print("[dim]Seeding demonstration data...[/dim]")
        summary = seed_sample_data(reset=False)
        table = Table(title="Demonstration Data Seed Summary", border_style="green")
        table.add_column("Entity / Layer", style="bold cyan")
        table.add_column("Count", justify="right", style="yellow")
        for key, count in summary.items():
            table.add_row(key.replace("_", " ").title(), str(count))
        console.print(table)
        console.print("[bold green]Database seeded successfully.[/bold green]")

    if load_vocab:
        vocab_file = Path("vocab/ELSST_R6.ttl")
        if vocab_file.exists():
            console.print("[dim]Loading standard ELSST vocabulary...[/dim]")
            stats = load_skos_vocabulary(str(vocab_file), max_levels=1)
            loaded_count = stats.get("concepts_loaded", 0)
            console.print(f"[bold green]Loaded {loaded_count} top ELSST concepts.[/bold green]")


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
                f"{status['total_concepts']} concepts ({status['top_concepts']} top concepts)."
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
                f"{status['total_concepts']} concepts ({status['top_concepts']} top concepts)."
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


# -----------------------------------------------------------------------------
# Metadata Import Subcommands
# -----------------------------------------------------------------------------


@import_app.command("file")
def import_file_cmd(
    file_path: str = typer.Argument(
        ...,
        help="Path to metadata document file to import (e.g. .ddi33.xml, .ddi40.json, .ddic.xml).",
    ),
    profile: str = typer.Option(
        "request",
        "--profile",
        "-p",
        help="Profile preset name (request, all_ddi) or path to custom YAML/JSON profile.",
    ),
    format_override: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Explicit format override (e.g. 'ddi-l:3.3:xml', 'ddi-c:2.5:xml').",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Parse and validate without committing records to the database.",
    ),
    force_reload: bool = typer.Option(
        False,
        "--force-reload",
        "-r",
        help="Force re-importing even if this exact file was previously staged.",
    ),
    batch_size: int = typer.Option(
        1000,
        "--batch-size",
        help="Database bulk insertion batch size.",
    ),
    show_progress: bool = typer.Option(
        True,
        "--progress/--no-progress",
        help="Show real-time progress bar during extraction and database staging.",
    ),
) -> None:
    """Import and stage a metadata document into StagedImport and StagedResourceNode."""
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )

    from fairwddi.importer import import_metadata_file

    configure_django_for_cli()

    path = Path(file_path)
    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: [cyan]{path}[/cyan]")
        raise typer.Exit(code=1)

    console.print(
        f"[dim]Processing metadata file [cyan]{path.name}[/cyan] "
        f"with profile [yellow]{profile}[/yellow]...[/dim]"
    )

    if show_progress:
        with Progress(
            SpinnerColumn(style="bold cyan"),
            TextColumn("[bold cyan]{task.description}[/bold cyan]"),
            BarColumn(bar_width=35, complete_style="green", finished_style="bold green"),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False,
        ) as progress:
            parse_task = progress.add_task("[cyan]Streaming & parsing document...", total=None)
            stage_task = progress.add_task(
                "[yellow]Staging resources to database...", total=None, visible=False
            )

            def on_progress(
                stage: str, current: int, total: int | None, message: str | None
            ) -> None:
                if stage == "parse":
                    desc = f"[cyan]Parsing fragments...[/cyan] [dim]({current:,} items)[/dim]"
                    progress.update(parse_task, completed=current, description=desc)
                elif stage == "parse_done":
                    desc = f"[bold green]Parsed {current:,} resource fragments[/bold green]"
                    progress.update(parse_task, total=current, completed=current, description=desc)
                    progress.update(
                        stage_task,
                        visible=True,
                        total=current,
                        completed=0,
                        description="[yellow]Filtering & staging to database...[/yellow]",
                    )
                elif stage == "stage":
                    desc = f"[yellow]Staging...[/yellow] [dim]({message or ''})[/dim]"
                    progress.update(stage_task, completed=current, total=total, description=desc)
                elif stage == "stage_done":
                    desc = f"[bold green]Staged {current:,} resources into db[/bold green]"
                    progress.update(stage_task, completed=current, total=total, description=desc)

            try:
                summary = import_metadata_file(
                    file_path=path,
                    profile=profile,
                    source_format=format_override,
                    batch_size=batch_size,
                    dry_run=dry_run,
                    force_reload=force_reload,
                    progress_callback=on_progress,
                )
            except Exception as exc:
                console.print(f"[bold red]Import Error:[/bold red] {exc}")
                raise typer.Exit(code=1) from exc
    else:
        try:
            summary = import_metadata_file(
                file_path=path,
                profile=profile,
                source_format=format_override,
                batch_size=batch_size,
                dry_run=dry_run,
                force_reload=force_reload,
            )
        except Exception as exc:
            console.print(f"[bold red]Import Error:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc

    if summary.get("status") == "already_staged":
        console.print(f"[bold yellow]Notice:[/bold yellow] {summary.get('message')}")
        console.print(
            f"[dim]Staged Import ID:[/dim] [cyan]#{summary.get('staged_import_id')}[/cyan]"
        )
        return

    fmt = summary.get("format_info", {})
    mode_tag = " [bold yellow][DRY RUN][/bold yellow]" if dry_run else ""
    table = Table(
        title=f"Metadata Import Summary{mode_tag} [{summary.get('file_name')}]",
        border_style="green" if not dry_run else "yellow",
    )
    table.add_column("Metric / Property", style="bold cyan")
    table.add_column("Value", style="yellow")

    if summary.get("staged_import_id"):
        table.add_row("Staged Import ID", f"#{summary.get('staged_import_id')}")
    spec_desc = f"{fmt.get('specification')} {fmt.get('version')} ({fmt.get('serialization')})"
    table.add_row("Detected Specification", spec_desc)
    table.add_row("Producer Flavor", fmt.get("flavor") or "Generic")
    table.add_row("Active Profile", summary.get("profile", ""))
    table.add_row("Total Resources Staged", f"{summary.get('total_staged', 0):,}")
    table.add_row("Skipped Duplicates", f"{summary.get('skipped_duplicates', 0):,}")
    table.add_row("Quarantined Drift Items", f"{summary.get('quarantined_count', 0):,}")
    table.add_row("Elapsed Time", f"{summary.get('elapsed_seconds', 0):.3f}s")
    table.add_row("Throughput", f"{summary.get('throughput_per_sec', 0):.1f} resources/sec")
    if summary.get("log_file"):
        table.add_row("Session Audit Log", str(summary.get("log_file")))

    console.print(table)

    if summary.get("counts_by_type"):
        counts_table = Table(title="Staged Nodes by Resource Type", border_style="cyan")
        counts_table.add_column("Resource Type", style="bold green")
        counts_table.add_column("Count", justify="right", style="yellow")
        for r_type, count in sorted(
            summary["counts_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            counts_table.add_row(r_type, f"{count:,}")
        console.print(counts_table)

    console.print("[bold green]Stage 1 import completed successfully.[/bold green]")


@import_app.command("list-profiles")
def import_list_profiles() -> None:
    """List available import profiles and their configuration rules."""
    from fairwddi.importer import list_available_profiles

    profiles = list_available_profiles()
    if not profiles:
        console.print("[yellow]No YAML/JSON profiles found in profiles/ directory.[/yellow]")
        return

    table = Table(title="Available Import Profiles", border_style="cyan")
    table.add_column("Profile Name", style="bold green")
    table.add_column("Description", style="white")
    table.add_column("Include Types", justify="right", style="yellow")
    table.add_column("Exclude Types", justify="right", style="red")
    table.add_column("Resolve Refs", justify="center", style="cyan")

    for p in profiles:
        inc = str(p["include_types_count"]) if p["include_types_count"] > 0 else "ALL"
        exc = str(p["exclude_types_count"]) if p["exclude_types_count"] > 0 else "None"
        refs = "✓" if p["include_referenced_resources"] else "✗"
        table.add_row(p["name"], p["description"], inc, exc, refs)

    console.print(table)


@import_app.command("list")
def import_list_cmd(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status."),
    source_format: str | None = typer.Option(None, "--format", help="Filter by format substring."),
    limit: int = typer.Option(20, "--limit", "-n", help="Max imports to list."),
) -> None:
    """List staged imports with status and resource counts."""
    from fairwddi.importer import list_staged_imports

    configure_django_for_cli()
    imports = list_staged_imports(status=status, source_format=source_format, limit=limit)
    if not imports:
        console.print("[yellow]No staged imports found matching criteria.[/yellow]")
        return

    table = Table(title="Staged Imports", border_style="cyan")
    table.add_column("ID", style="bold cyan", justify="right")
    table.add_column("File Name", style="bold green")
    table.add_column("Format", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Total Resources", justify="right", style="magenta")
    table.add_column("Created At", style="dim")

    for imp in imports:
        table.add_row(
            f"#{imp['id']}",
            imp["file_name"],
            imp["source_format"],
            imp["status"],
            f"{imp['total_resources']:,}",
            str(imp["created_at"] or "")[:19],
        )
    console.print(table)


@import_app.command("stats")
def import_stats_cmd(
    import_id: int = typer.Argument(..., help="StagedImport primary key ID."),
    format_type: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: 'table', 'json', 'markdown' (or 'md').",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional file path to write output to.",
    ),
) -> None:
    """Display comprehensive statistics, normalization metrics, and cross-tabulation."""
    from rich.markdown import Markdown

    from fairwddi.importer import (
        get_import_statistics,
        render_statistics_json,
        render_statistics_markdown,
    )

    configure_django_for_cli()
    try:
        stats = get_import_statistics(import_id)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    fmt = format_type.lower()
    if fmt == "json":
        json_text = render_statistics_json(stats, indent=2)
        if output_path:
            output_path.write_text(json_text, encoding="utf-8")
            console.print(
                f"[bold green]Saved JSON statistics to [cyan]{output_path}[/cyan][/bold green]"
            )
        else:
            console.print(json_text)
        return

    if fmt in ("markdown", "md"):
        md_text = render_statistics_markdown(stats)
        if output_path:
            output_path.write_text(md_text, encoding="utf-8")
            console.print(
                f"[bold green]Saved Markdown report to [cyan]{output_path}[/cyan][/bold green]"
            )
        else:
            console.print(Markdown(md_text))
        return

    # Default: Rich Table output
    table = Table(
        title=f"Import #{stats['staged_import_id']} Statistics [{stats['file_name']}]",
        border_style="cyan",
    )
    table.add_column("Metric / Indicator", style="bold cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Status", stats["status"])
    table.add_row("Source Format", stats["source_format"])
    table.add_row("Total Staged Resources", f"{stats['total_resources']:,}")
    table.add_row("Normalized Resources", f"{stats['normalized_count']:,}")
    table.add_row("Normalization Progress", f"{stats['normalization_progress_pct']}%")
    table.add_row("Downstream URN Aliases", f"{stats['alias_count']:,}")
    table.add_row("Quarantined Collisions", f"{stats['quarantine_count']:,}")
    table.add_row("Created At", str(stats["created_at"]))

    console.print(table)

    if stats["counts_by_type"]:
        counts_table = Table(title="Resource Types & Status Cross-Tabulation", border_style="green")
        counts_table.add_column("Resource Type", style="bold green")
        counts_table.add_column("Total", justify="right", style="magenta")
        counts_table.add_column("Staged", justify="right", style="cyan")
        counts_table.add_column("Normalized", justify="right", style="yellow")
        counts_table.add_column("Quarantined", justify="right", style="red")

        for r_type, total in stats["counts_by_type"].items():
            breakdown = stats["cross_tab"].get(r_type, {})
            staged = str(breakdown.get("staged", 0))
            norm = str(breakdown.get("normalized", 0))
            quar = str(breakdown.get("quarantined", 0))
            counts_table.add_row(r_type, f"{total:,}", staged, norm, quar)

        console.print(counts_table)


@import_app.command("query")
def import_query_cmd(
    import_id: int | None = typer.Option(
        None, "--import-id", "-i", help="Filter by StagedImport ID."
    ),
    resource_type: str | None = typer.Option(None, "--type", "-t", help="Filter by resource type."),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status."),
    search: str | None = typer.Option(None, "--search", "-q", help="Search URN substring."),
    limit: int = typer.Option(20, "--limit", "-n", help="Max records to display."),
    show_json: bool = typer.Option(False, "--show-json", help="Display raw JSON value preview."),
) -> None:
    """Query, filter, and inspect staged resource nodes."""
    import json

    from fairwddi.importer import query_staged_resources

    configure_django_for_cli()
    res = query_staged_resources(
        import_id=import_id,
        resource_type=resource_type,
        status=status,
        search=search,
        limit=limit,
    )

    console.print(
        f"[dim]Found [bold cyan]{res['total_count']:,}[/bold cyan] matching nodes "
        f"(displaying {len(res['results'])}):[/dim]"
    )
    if not res["results"]:
        return

    table = Table(title="Staged Resource Query Results", border_style="cyan")
    table.add_column("ID", style="bold cyan", justify="right")
    table.add_column("Import", style="dim", justify="right")
    table.add_column("Resource Type", style="bold green")
    table.add_column("Raw URN", style="yellow")
    table.add_column("Status", style="magenta")

    for node in res["results"]:
        table.add_row(
            str(node["id"]),
            f"#{node['staged_import_id']}",
            node["resource_type"],
            node["raw_urn"],
            node["status"],
        )
    console.print(table)

    if show_json:
        for node in res["results"][:3]:
            console.print(
                Panel(
                    json.dumps(node["raw_value"], indent=2),
                    title=f"Payload for Node #{node['id']} [{node['resource_type']}]",
                    border_style="green",
                )
            )


@import_app.command("status")
def import_status_cmd(
    import_id: int = typer.Argument(..., help="StagedImport primary key ID."),
) -> None:
    """Display status and breakdown for a specific staged import job."""
    configure_django_for_cli()
    from fairwddi.models import StagedImport, StagedResourceNode

    staged_import = StagedImport.objects.filter(id=import_id).first()
    if not staged_import:
        console.print(f"[bold red]Error:[/bold red] StagedImport #{import_id} not found.")
        raise typer.Exit(code=1)

    table = Table(
        title=f"Staged Import #{staged_import.id} [{staged_import.file_name}]",
        border_style="cyan",
    )
    table.add_column("Attribute", style="bold cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Status", staged_import.status)
    table.add_row("Source Format", staged_import.source_format)
    table.add_row("Total Resources", str(staged_import.total_resources))
    table.add_row("Processed Resources", str(staged_import.processed_resources))
    table.add_row("Created At", str(staged_import.created_at))
    if staged_import.processed_at:
        table.add_row("Processed At", str(staged_import.processed_at))
    log_file = staged_import.import_options.get("log_file")
    if log_file:
        table.add_row("Session Log File", str(log_file))

    console.print(table)

    nodes = StagedResourceNode.objects.filter(staged_import=staged_import)
    if nodes.exists():
        from django.db.models import Count

        counts = (
            nodes.values("resource_type", "status").annotate(total=Count("id")).order_by("-total")
        )
        breakdown_table = Table(title="Staged Resource Nodes Breakdown", border_style="green")
        breakdown_table.add_column("Resource Type", style="bold green")
        breakdown_table.add_column("Status", style="cyan")
        breakdown_table.add_column("Count", justify="right", style="yellow")

        for row in counts:
            breakdown_table.add_row(row["resource_type"], row["status"], str(row["total"]))
        console.print(breakdown_table)


@import_app.command("log")
def import_log_cmd(
    import_id: int = typer.Argument(..., help="StagedImport primary key ID."),
) -> None:
    """Display the session log for a specific staged import job."""
    configure_django_for_cli()
    from fairwddi.models import StagedImport

    staged_import = StagedImport.objects.filter(id=import_id).first()
    if not staged_import:
        console.print(f"[bold red]Error:[/bold red] StagedImport #{import_id} not found.")
        raise typer.Exit(code=1)

    log_file_str = staged_import.import_options.get("log_file")
    if not log_file_str:
        console.print(f"[yellow]No log file recorded for StagedImport #{import_id}.[/yellow]")
        return

    log_path = Path(log_file_str)
    if not log_path.exists():
        console.print(
            f"[bold red]Error:[/bold red] Log file not found on disk: [cyan]{log_path}[/cyan]"
        )
        raise typer.Exit(code=1)

    log_content = log_path.read_text(encoding="utf-8")
    panel = Panel(log_content, title=f"Log: {log_path.name}", border_style="cyan")
    console.print(panel)


@import_app.command("delete")
def import_delete_cmd(
    import_id: int = typer.Argument(..., help="StagedImport primary key ID to delete."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt and proceed with deletion.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force deletion even if resources have been normalized or referenced downstream.",
    ),
    delete_log: bool = typer.Option(
        False,
        "--delete-log",
        help="Also delete the session audit log file from disk.",
    ),
) -> None:
    configure_django_for_cli()
    from fairwddi.importer import ProtectedImportError, delete_staged_import
    from fairwddi.models import StagedImport

    staged_import = StagedImport.objects.filter(id=import_id).first()
    if not staged_import:
        console.print(f"[bold red]Error:[/bold red] StagedImport #{import_id} not found.")
        raise typer.Exit(code=1)

    if not yes:
        confirmed = typer.confirm(
            f"Are you sure you want to delete StagedImport #{import_id} "
            f"('{staged_import.file_name}', {staged_import.total_resources:,} nodes)?",
            default=False,
        )
        if not confirmed:
            console.print("[dim]Deletion cancelled.[/dim]")
            raise typer.Exit()

    try:
        res = delete_staged_import(import_id=import_id, force=force, delete_log_file=delete_log)
    except ProtectedImportError as exc:
        console.print(f"[bold red]Deletion Blocked:[/bold red] {exc}")
        console.print(
            f"[yellow]Normalized resources:[/yellow] {exc.normalized_count} | "
            f"[yellow]Downstream URN aliases:[/yellow] {exc.alias_count}"
        )
        console.print("[dim]Use --force / -f to override dependency checks and force delete.[/dim]")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Deleted StagedImport #{res['staged_import_id']}[/bold green] "
        f"([cyan]{res['file_name']}[/cyan]): "
        f"removed [yellow]{res['deleted_nodes_count']:,}[/yellow] staged node(s)."
    )
    if res["log_file_deleted"]:
        console.print("[dim]Session audit log file removed from disk.[/dim]")


# -----------------------------------------------------------------------------
# Phase 2 Multi-Stage Ingestion CLI Groups
# (preflight, stage, promote, compare, harmonize, ingest)
# -----------------------------------------------------------------------------


@preflight_app.command("check")
def preflight_check_cmd(
    file_path: str = typer.Argument(..., help="Path to incoming DDI-C or DDI-L metadata file."),
    profile: str = typer.Option("request", "--profile", "-p", help="Profile preset or YAML path."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .preflight.plan.yaml & .report.md."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Mark the preflight review gate as approved."
    ),
) -> None:
    """Inspect a DDI-C or DDI-L file for readiness, profile compliance, URNs, and links."""
    from fairwddi.ingest.preflight import run_preflight_check

    configure_django_for_cli()
    try:
        plan = run_preflight_check(
            file_path=file_path,
            profile=profile,
            output_dir=output_dir,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Preflight Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    status_color = "green" if plan.is_ready_to_execute() else "yellow"
    table = Table(
        title=f"Preflight Readiness Check [{Path(file_path).name}]",
        border_style=status_color,
    )
    table.add_column("Property / Metric", style="bold cyan")
    table.add_column("Value", style="yellow")
    table.add_row("Job ID", plan.job_id)
    table.add_row("Detected Format", str(plan.source_format))
    table.add_row("File SHA-256", str(plan.file_sha256)[:24] + "...")
    table.add_row("Ready to Proceed", "YES" if plan.is_ready_to_execute() else "PENDING REVIEW")
    table.add_row("Errors / Warnings", f"{plan.error_count} / {plan.warning_count}")
    for k, v in plan.summary.items():
        if not isinstance(v, (dict, list)):
            table.add_row(str(k), str(v))
    console.print(table)

    if plan.issues:
        iss_table = Table(title="Preflight Findings", border_style="yellow")
        iss_table.add_column("Severity", style="bold")
        iss_table.add_column("Code", style="cyan")
        iss_table.add_column("Message", style="white")
        for iss in plan.issues:
            iss_table.add_row(iss.severity.upper(), iss.code, iss.message)
        console.print(iss_table)


@preflight_app.command("upgrade")
def preflight_upgrade_cmd(
    file_path: str = typer.Argument(..., help="Path to DDI-Codebook (.xml) file to upgrade."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Explicit output path for upgraded DDI-L file."
    ),
    format_type: str = typer.Option(
        "ddi4-json",
        "--format",
        "-f",
        help="Target DDI-L format: ddi4-json, ddi4-jsonl, ddi4-xml, ddi33-xml.",
    ),
    agency: str | None = typer.Option(None, "--agency", "-a", help="Override DDI agency ID."),
    version: str | None = typer.Option(None, "--version", help="Override DDI version."),
    identifier: str | None = typer.Option(None, "--identifier", help="Override study ID."),
    id_strategy: str = typer.Option(
        "hierarchical",
        "--id-strategy",
        help="ID strategy: hierarchical, content_hash, prefix, original, uuid, sequential.",
    ),
    harmonize_codes: bool = typer.Option(
        True,
        "--harmonize-codes/--no-harmonize-codes",
        help="Deduplicate identical categories and code lists during upgrade.",
    ),
) -> None:
    """Explicitly upgrade a classic or multilingual DDI-Codebook file to DDI-Lifecycle on disk."""
    from fairwddi.ingest.preflight import upgrade_ddic_to_ddil

    try:
        res = upgrade_ddic_to_ddil(
            file_path=file_path,
            output_path=output,
            output_format=format_type,  # type: ignore[arg-type]
            agency=agency,
            version=version,
            identifier=identifier,
            id_strategy=id_strategy,
            harmonize_codes=harmonize_codes,
        )
    except Exception as exc:
        console.print(f"[bold red]Upgrade Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="DDI-C to DDI-L Upgrade Summary", border_style="green")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="yellow")
    table.add_row("Output DDI-L File", res["output_file"])
    table.add_row("Upgrade Report", res["report_file"])
    table.add_row("Agency / Version", f"{res['agency']} / {res['version']}")
    table.add_row("Variables", f"{res['variable_count']:,}")
    table.add_row("CodeLists (Deduplicated)", f"{res['codelist_count']:,}")
    table.add_row("Categories (Deduplicated)", f"{res['category_count']:,}")
    table.add_row("Questions", f"{res['question_count']:,}")
    table.add_row("Physical Instances", f"{res['physical_instance_count']:,}")
    console.print(table)


# Stage 2a subcommands
stage_app.command("load")(import_file_cmd)
stage_app.command("list")(import_list_cmd)
stage_app.command("status")(import_status_cmd)
stage_app.command("stats")(import_stats_cmd)
stage_app.command("query")(import_query_cmd)
stage_app.command("profiles")(import_list_profiles)


@stage_app.command("cleanup")
def stage_cleanup_cmd(
    import_id: int | None = typer.Argument(
        None, help="Optional StagedImport ID. Omit to compact all promoted batches."
    ),
    delete_batch: bool = typer.Option(
        False,
        "--delete",
        help="Permanently delete the batch instead of compacting JSONB payloads.",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion of promoted batch."),
) -> None:
    """Compact `raw_value` JSONB payloads on promoted nodes (or delete a batch)."""
    from fairwddi.ingest.staging import cleanup_staged_import

    configure_django_for_cli()
    try:
        res = cleanup_staged_import(
            import_id=import_id,
            compact_only=not delete_batch,
            force=force,
        )
    except Exception as exc:
        console.print(f"[bold red]Cleanup Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if res["mode"] == "compacted":
        console.print(
            f"[bold green]Compacted [yellow]{res['compacted_nodes_count']:,}[/yellow] "
            f"promoted staging node(s) (lineage preserved for undo).[/bold green]"
        )
    else:
        console.print(
            f"[bold green]Deleted StagedImport #{res['staged_import_id']} "
            f"({res['deleted_nodes_count']:,} nodes).[/bold green]"
        )


@promote_app.command("plan")
def promote_plan_cmd(
    import_id: int = typer.Argument(..., help="StagedImport batch ID to plan promotion for."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .promote.plan.yaml & .report.md."
    ),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Approve review gate."),
) -> None:
    """Generate a review-gated Promotion Plan (.promote.plan.yaml & .report.md) for a batch."""
    from fairwddi.ingest.promoter import plan_promotion

    configure_django_for_cli()
    try:
        plan = plan_promotion(
            import_id=import_id,
            output_dir=output_dir,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Promote Plan Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Promotion Plan [{plan.job_id}]", border_style="cyan")
    table.add_column("Action / Metric", style="bold cyan")
    table.add_column("Count", justify="right", style="yellow")
    for k, v in plan.summary.items():
        table.add_row(str(k), str(v))
    table.add_row("Pending Review Items", str(plan.pending_review_count))
    console.print(table)


@promote_app.command("apply")
def promote_apply_cmd(
    batch_or_plan: str = typer.Argument(
        ..., help="StagedImport batch ID (int) or path to a .promote.plan.yaml file."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Bypass review gate for pending drift/quarantine items."
    ),
    compact: bool = typer.Option(
        False, "--compact", help="Compact staged JSONB payloads immediately after promotion."
    ),
) -> None:
    """Promote staged resources into ReQuest core tables (resolving cascade & shortcuts)."""
    from fairwddi.ingest.promoter import apply_promotion

    configure_django_for_cli()
    try:
        res = apply_promotion(
            import_id_or_plan=batch_or_plan,
            auto_approve=auto_approve,
            compact=compact,
        )
    except Exception as exc:
        console.print(f"[bold red]Promote Apply Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(
        title=f"Promotion Completed [Batch #{res['staged_import_id']}]",
        border_style="green",
    )
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", justify="right", style="yellow")
    table.add_row("Job ID", res["job_id"])
    table.add_row("Batch Status", res["status"])
    table.add_row("Created Core Resources", f"{res['created_count']:,}")
    table.add_row("Reused Existing Resources", f"{res['reused_count']:,}")
    table.add_row("Registered URN Aliases", f"{res['alias_count']:,}")
    table.add_row("Quarantined Drift Items", f"{res['quarantine_count']:,}")
    if compact:
        table.add_row("Compacted Staged Nodes", f"{res['compacted_nodes_count']:,}")
    console.print(table)


@promote_app.command("undo")
def promote_undo_cmd(
    import_id: int = typer.Argument(..., help="StagedImport batch ID to roll back."),
    force: bool = typer.Option(False, "--force", "-f", help="Force rollback."),
) -> None:
    """Roll back a promoted batch, removing created core entities and resetting staging status."""
    from fairwddi.ingest.promoter import undo_promotion

    configure_django_for_cli()
    try:
        res = undo_promotion(import_id=import_id, force=force)
    except Exception as exc:
        console.print(f"[bold red]Promote Undo Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Rolled back Batch #{res['staged_import_id']}:[/bold green] "
        f"removed [yellow]{res['deleted_core_resources_count']:,}[/yellow] core resource(s), "
        f"[yellow]{res['deleted_aliases_count']:,}[/yellow] alias(es), and reset "
        f"[cyan]{res['reset_staged_nodes_count']:,}[/cyan] staged node(s)."
    )


@compare_app.command("batch")
def compare_batch_cmd(
    import_id: int = typer.Argument(..., help="StagedImport batch ID to compare against the bank."),
    threshold: float = typer.Option(0.75, "--threshold", "-t", help="Minimum similarity score."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .compare.plan.yaml & .report.md."
    ),
) -> None:
    """Compare resources from a specific batch against existing ReQuest bank entities."""
    from fairwddi.ingest.comparator import compare_batch

    configure_django_for_cli()
    try:
        plan = compare_batch(import_id=import_id, threshold=threshold, output_dir=output_dir)
    except Exception as exc:
        console.print(f"[bold red]Compare Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Comparison complete ({plan.job_id}):[/bold green] "
        f"found [yellow]{len(plan.actions):,}[/yellow] candidate pair(s)."
    )


@compare_app.command("discover")
def compare_discover_cmd(
    resource_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by type: Category, CodeList, QuestionItem, RepresentedVariable.",
    ),
    study_urn: str | None = typer.Option(None, "--study", "-s", help="Scope to StudyUnit URN."),
    batch_id: int | None = typer.Option(None, "--batch-id", "-b", help="Scope to StagedImport ID."),
    query: str | None = typer.Option(None, "--query", "-q", help="Substring filter."),
    threshold: float = typer.Option(0.75, "--threshold", help="Minimum similarity confidence."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max candidate pairs to return."),
) -> None:
    """Discover harmonization candidate pairs across the ReQuest question bank."""
    from fairwddi.ingest.comparator import discover_candidates

    configure_django_for_cli()
    candidates = discover_candidates(
        resource_type=resource_type,
        study_urn=study_urn,
        batch_id=batch_id,
        query=query,
        threshold=threshold,
        limit=limit,
    )
    if not candidates:
        console.print("[yellow]No harmonization candidates found matching criteria.[/yellow]")
        return

    table = Table(
        title=f"Discovered Harmonization Candidates ({len(candidates)})",
        border_style="cyan",
    )
    table.add_column("Type", style="bold green")
    table.add_column("Match Tier", style="magenta")
    table.add_column("Conf", justify="right", style="yellow")
    table.add_column("Action", style="cyan")
    table.add_column("Source URN", style="white")
    table.add_column("Target URN", style="white")
    for c in candidates:
        table.add_row(
            c["resource_type"],
            c["match_type"],
            f"{c['confidence']:.2f}",
            c["recommended_action"],
            c["source_urn"],
            c["target_urn"],
        )
    console.print(table)


@harmonize_app.command("plan")
def harmonize_plan_cmd(
    batch_id: int | None = typer.Option(None, "--batch-id", "-b", help="Scope to StagedImport ID."),
    resource_type: str | None = typer.Option(None, "--type", "-t", help="Filter by resource type."),
    threshold: float = typer.Option(0.75, "--threshold", help="Similarity threshold."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .harmonize.plan.yaml & .report.md."
    ),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Approve review gate."),
) -> None:
    """Generate a review-gated Harmonization Plan (.harmonize.plan.yaml & .report.md)."""
    from fairwddi.ingest.harmonizer import plan_harmonization

    configure_django_for_cli()
    plan = plan_harmonization(
        import_id=batch_id,
        resource_type=resource_type,
        threshold=threshold,
        output_dir=output_dir,
        auto_approve=auto_approve,
    )
    console.print(
        f"[bold green]Generated Harmonization Plan [cyan]{plan.job_id}[/cyan]:[/bold green] "
        f"[yellow]{len(plan.actions)}[/yellow] action(s), "
        f"[yellow]{plan.pending_review_count}[/yellow] pending review."
    )


@harmonize_app.command("apply")
def harmonize_apply_cmd(
    plan_file: Path = typer.Argument(..., help="Path to .harmonize.plan.yaml file to apply."),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Execute even if review gate is not marked approved."
    ),
) -> None:
    """Apply an approved Harmonization Plan (multilingual merges, URN aliases, semantic links)."""
    from fairwddi.ingest.harmonizer import apply_harmonization

    configure_django_for_cli()
    try:
        res = apply_harmonization(plan_file, auto_approve=auto_approve)
    except Exception as exc:
        console.print(f"[bold red]Harmonize Apply Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Applied Harmonization Job [cyan]{res['job_id']}[/cyan]:[/bold green] "
        f"merged={res['merged_multilingual_count']}, aliased={res['aliased_count']}, "
        f"semantic_links={res['semantic_links_created']}."
    )


@harmonize_app.command("undo")
def harmonize_undo_cmd(
    job_id: str = typer.Argument(..., help="Harmonization job_id to revert."),
) -> None:
    """Revert an applied Harmonization Job using EventLog snapshots."""
    from fairwddi.ingest.harmonizer import undo_harmonization

    configure_django_for_cli()
    try:
        res = undo_harmonization(job_id)
    except Exception as exc:
        console.print(f"[bold red]Harmonize Undo Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Reverted Harmonization Job [cyan]{res['job_id']}[/cyan]:[/bold green] "
        f"restored {res['restored_targets']} resource(s), "
        f"removed {res['removed_aliases']} alias(es)."
    )


@ingest_app.command("run")
def ingest_run_cmd(
    file_path: str = typer.Argument(..., help="Path to DDI-C or DDI-L metadata file to ingest."),
    profile: str = typer.Option("request", "--profile", "-p", help="Import profile."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory for stage plans, upgraded files, and reports."
    ),
    agency: str | None = typer.Option(None, "--agency", help="Agency override for DDI-C upgrade."),
    id_strategy: str = typer.Option("hierarchical", "--id-strategy", help="ID strategy."),
    stage_only: bool = typer.Option(False, "--stage-only", help="Stop after staging."),
    harmonize: bool = typer.Option(
        False, "--harmonize", help="Also run comparison and harmonization after promotion."
    ),
    compact: bool = typer.Option(
        False, "--compact", help="Compact staged JSONB payloads after promotion."
    ),
    force_reload: bool = typer.Option(
        False, "--force-reload", help="Force reload if already staged."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Auto-approve review gates across stages."
    ),
) -> None:
    """Run the end-to-end ingestion pipeline (preflight -> upgrade -> stage -> promote)."""
    from fairwddi.ingest.pipeline import run_ingestion_pipeline

    configure_django_for_cli()
    try:
        res = run_ingestion_pipeline(
            file_path=file_path,
            profile=profile,
            output_dir=output_dir,
            agency=agency,
            id_strategy=id_strategy,
            stage_only=stage_only,
            harmonize=harmonize,
            compact_after_promote=compact,
            force_reload=force_reload,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Ingestion Pipeline Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Ingestion Pipeline Status:[/bold green] [cyan]{res['status']}[/cyan]"
    )
    if res.get("staged_import_id"):
        console.print(
            f"[dim]Staged Import Batch ID:[/dim] [yellow]#{res['staged_import_id']}[/yellow]"
        )


if __name__ == "__main__":
    app()

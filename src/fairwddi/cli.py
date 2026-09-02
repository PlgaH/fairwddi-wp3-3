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
    help="Metadata document import, staging, profiles, and logs.",
    no_args_is_help=True,
)
app.add_typer(import_app, name="import")

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
        "request_core",
        "--profile",
        "-p",
        help="Profile preset name (request_core, all_ddi) or path to custom YAML/JSON profile.",
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
) -> None:
    """Import and stage a metadata document into StagedImport and StagedResourceNode."""
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
    """Delete a staged import and its resource nodes with downstream dependency safety."""
    from fairwddi.importer import ProtectedImportError, delete_staged_import

    configure_django_for_cli()

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


if __name__ == "__main__":
    app()

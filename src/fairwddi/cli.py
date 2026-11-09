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

preflight_app = typer.Typer(
    name="preflight",
    help="Stage 1: Preflight readiness checks, profile QA, URN audits, and DDI-C upgrades.",
    no_args_is_help=True,
)
app.add_typer(preflight_app, name="preflight")

ingest_app = typer.Typer(
    name="ingest",
    help="Stage 2: Direct file-to-core-tables ingestion, batch receipts, and undo.",
    no_args_is_help=True,
)
app.add_typer(ingest_app, name="ingest")

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
# Phase 2 Multi-Stage Ingestion CLI Groups
# (preflight, ingest, compare, harmonize)
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
    agency: str | None = typer.Option(
        None,
        "--agency",
        "-a",
        help="Override DDI agency ID (default: 'fr.cdsp' or $DDI_AGENCY).",
    ),
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
    harmonize_questions: bool = typer.Option(
        True,
        "--harmonize-questions/--no-harmonize-questions",
        help="Deduplicate identical questions across variables during upgrade.",
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
            harmonize_questions=harmonize_questions,
        )
    except Exception as exc:
        console.print(f"[bold red]Upgrade Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="DDI-C to DDI-L Upgrade Summary", border_style="green")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="yellow")
    table.add_row("Output DDI-L File", res["output_file"])
    if res.get("stats_file"):
        table.add_row("Statistics DDI-L File", res["stats_file"])
    table.add_row("Upgrade Report", res["report_file"])
    table.add_row("Agency / Version", f"{res['agency']} / {res['version']}")
    table.add_row("Variables", f"{res['variable_count']:,}")

    cl_text = f"{res['codelist_count']:,}"
    if res.get("codelist_duplicates_removed", 0) > 0:
        cl_rem = res["codelist_duplicates_removed"]
        cl_pct = res.get("codelist_reduction_pct", 0.0)
        cl_text += f" ({cl_rem:,} duplicates removed, {cl_pct:.1f}% reduction)"
    table.add_row("CodeLists (Deduplicated)", cl_text)

    cat_text = f"{res['category_count']:,}"
    if res.get("category_duplicates_removed", 0) > 0:
        cat_rem = res["category_duplicates_removed"]
        cat_pct = res.get("category_reduction_pct", 0.0)
        cat_text += f" ({cat_rem:,} duplicates removed, {cat_pct:.1f}% reduction)"
    table.add_row("Categories (Deduplicated)", cat_text)

    q_text = f"{res['question_count']:,}"
    if res.get("question_duplicates_removed", 0) > 0:
        q_rem = res["question_duplicates_removed"]
        q_pct = res.get("question_reduction_pct", 0.0)
        q_text += f" ({q_rem:,} duplicates removed, {q_pct:.1f}% reduction)"
    table.add_row("Questions (Deduplicated)", q_text)
    table.add_row("Physical Instances", f"{res['physical_instance_count']:,}")
    if res.get("variable_statistics_count", 0) > 0:
        vs_cnt = res["variable_statistics_count"]
        f_cnt = res.get("total_frequencies_count", 0)
        s_cnt = res.get("total_summary_statistics_count", 0)
        table.add_row(
            "Variable Statistics",
            f"{vs_cnt:,} ({f_cnt:,} frequencies, {s_cnt:,} summary stats)",
        )
    console.print(table)


@preflight_app.command("profiles")
def preflight_profiles_cmd() -> None:
    """List available import profiles and their configuration rules."""
    from fairwddi.ingest.profiles import list_available_profiles

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


@ingest_app.command("plan")
def ingest_plan_cmd(
    file_path: str = typer.Argument(
        ..., help="Path to DDI-Lifecycle (.xml/.json/.jsonl) or DDI-Codebook (.xml) file."
    ),
    profile: str = typer.Option("request", "--profile", "-p", help="Import profile."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .ingest.plan.yaml & .report.md."
    ),
    force_reload: bool = typer.Option(
        False, "--force-reload", help="Plan reload even if file SHA-256 was already ingested."
    ),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Approve review gate."),
) -> None:
    """Generate a zero-write Ingestion Plan (.ingest.plan.yaml & .report.md) for a metadata file."""
    from fairwddi.ingest.loader import plan_ingestion

    configure_django_for_cli()
    path = Path(file_path)
    if not path.exists():
        candidate_temp = Path("temp") / path.name
        if candidate_temp.exists():
            console.print(
                f"[yellow]Notice:[/yellow] File not found at '{file_path}'. "
                f"Found at '{candidate_temp}', using that."
            )
            path = candidate_temp
            file_path = str(candidate_temp)

    effective_output_dir = output_dir if output_dir is not None else path.resolve().parent
    try:
        plan = plan_ingestion(
            file_path=file_path,
            profile=profile,
            output_dir=effective_output_dir,
            force_reload=force_reload,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Ingest Plan Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Ingestion Plan [{plan.job_id}]", border_style="cyan")
    table.add_column("Action / Metric", style="bold cyan")
    table.add_column("Count", justify="right", style="yellow")
    table.add_row("Source Format", str(plan.source_format))
    for k, v in plan.summary.items():
        if k == "skipped_types":
            if v:
                table.add_row("Skipped Types", ", ".join(v))
        else:
            table.add_row(str(k), str(v))
    table.add_row("Pending Review Items", str(plan.pending_review_count))
    table.add_row("Errors", str(plan.error_count))
    console.print(table)

    plan_path = effective_output_dir / f"{path.stem}.ingest.plan.yaml"
    report_path = effective_output_dir / f"{path.stem}.ingest.report.md"
    console.print()
    console.print("[bold green]✓ Ingestion Plan saved to disk:[/bold green]")
    console.print(f"  • Plan YAML: [cyan]{plan_path}[/cyan]")
    console.print(f"  • Report:    [cyan]{report_path}[/cyan]")
    console.print()
    console.print("[dim]To execute this plan in PostgreSQL:[/dim]")
    console.print(f"  [yellow]fairwddi ingest execute {plan_path}[/yellow]\n")


@ingest_app.command("execute")
def ingest_execute_cmd(
    plan: str = typer.Argument(
        ..., help="Path to approved .ingest.plan.yaml file or metadata file."
    ),
    profile: str = typer.Option("request", "--profile", "-p", help="Import profile."),
    force_reload: bool = typer.Option(
        False, "--force-reload", help="Re-ingest even if file SHA-256 was already ingested."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Bypass review gate for pending drift/quarantine items."
    ),
) -> None:
    """Stream metadata directly into ReQuest core tables and record an IngestBatch receipt."""
    from fairwddi.ingest.loader import execute_ingestion

    configure_django_for_cli()
    try:
        res = execute_ingestion(
            file_or_plan=plan,
            profile=profile,
            force_reload=force_reload,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Ingest Execution Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if res["status"] == "already_ingested":
        console.print(
            f"[bold yellow]Notice:[/bold yellow] File already ingested in "
            f"[cyan]Batch #{res['batch_id']}[/cyan]. Use --force-reload to replace."
        )
        return

    table = Table(
        title=f"Ingestion Completed [Batch #{res['batch_id']}]",
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
    table.add_row("Inserted Frequency Rows", f"{res['frequency_rows_count']:,}")
    console.print(table)


@ingest_app.command("run")
def ingest_run_cmd(
    file_path: str = typer.Argument(..., help="Path to DDI-C or DDI-L metadata file to ingest."),
    profile: str = typer.Option("request", "--profile", "-p", help="Import profile."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory for stage plans, upgraded files, and reports."
    ),
    agency: str | None = typer.Option(
        None,
        "--agency",
        help="Agency override for DDI-C upgrade (default: 'fr.cdsp' or $DDI_AGENCY).",
    ),
    id_strategy: str = typer.Option("hierarchical", "--id-strategy", help="ID strategy."),
    plan_only: bool = typer.Option(
        False, "--plan-only", help="Stop after generating the preflight & ingestion plans."
    ),
    harmonize: bool = typer.Option(
        False, "--harmonize", help="Also run comparison and harmonization after ingestion."
    ),
    force_reload: bool = typer.Option(
        False, "--force-reload", help="Force reload if already ingested."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Auto-approve review gates across stages."
    ),
) -> None:
    """Run the end-to-end ingestion pipeline (preflight -> upgrade -> ingest -> harmonize)."""
    from fairwddi.ingest.pipeline import run_ingestion_pipeline

    configure_django_for_cli()
    try:
        res = run_ingestion_pipeline(
            file_path=file_path,
            profile=profile,
            output_dir=output_dir,
            agency=agency,
            id_strategy=id_strategy,
            plan_only=plan_only,
            harmonize=harmonize,
            force_reload=force_reload,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Ingestion Pipeline Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Ingestion Pipeline Status:[/bold green] [cyan]{res['status']}[/cyan]"
    )
    if res.get("batch_id"):
        console.print(f"[dim]Ingest Batch ID:[/dim] [yellow]#{res['batch_id']}[/yellow]")


@ingest_app.command("undo")
def ingest_undo_cmd(
    batch_id: int = typer.Argument(..., help="IngestBatch ID to roll back."),
) -> None:
    """Roll back an IngestBatch, removing created core resources, frequencies, and aliases."""
    from fairwddi.ingest.loader import undo_ingestion

    configure_django_for_cli()
    try:
        res = undo_ingestion(batch_id=batch_id)
    except Exception as exc:
        console.print(f"[bold red]Ingest Undo Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Rolled back Batch #{res['batch_id']}:[/bold green] "
        f"removed [yellow]{res['deleted_core_resources_count']:,}[/yellow] core resource(s) "
        f"and [yellow]{res['deleted_aliases_count']:,}[/yellow] alias(es)."
    )


@ingest_app.command("list")
def ingest_list_cmd(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by batch status."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max batches to list."),
) -> None:
    """List IngestBatch receipts with status and resource counts."""
    from fairwddi.ingest.loader import list_ingest_batches

    configure_django_for_cli()
    batches = list_ingest_batches(status=status, limit=limit)
    if not batches:
        console.print("[yellow]No ingestion batches found matching criteria.[/yellow]")
        return

    table = Table(title="Ingestion Batches", border_style="cyan")
    table.add_column("ID", style="bold cyan", justify="right")
    table.add_column("File Name", style="bold green")
    table.add_column("Format", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Created", justify="right", style="magenta")
    table.add_column("Reused", justify="right", style="cyan")
    table.add_column("Aliases", justify="right", style="blue")
    table.add_column("Created At", style="dim")

    for b in batches:
        table.add_row(
            f"#{b['id']}",
            b["file_name"],
            b["source_format"],
            b["status"],
            f"{b['created_count']:,}",
            f"{b['reused_count']:,}",
            f"{b['alias_count']:,}",
            str(b["created_at"] or "")[:19],
        )
    console.print(table)


@ingest_app.command("status")
def ingest_status_cmd(
    batch_id: int = typer.Argument(..., help="IngestBatch ID to inspect."),
) -> None:
    """Display status and per-entity statistics for a specific IngestBatch receipt."""
    from fairwddi.ingest.loader import get_ingest_batch_status

    configure_django_for_cli()
    try:
        info_dict = get_ingest_batch_status(batch_id=batch_id)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(
        title=f"IngestBatch #{info_dict['id']} [{info_dict['file_name']}]",
        border_style="cyan",
    )
    table.add_column("Attribute", style="bold cyan")
    table.add_column("Value", style="yellow")
    table.add_row("Status", info_dict["status"])
    table.add_row("Source Format", info_dict["source_format"])
    table.add_row("File SHA-256", info_dict["file_sha256"][:24] + "...")
    table.add_row("Created Core Resources", f"{info_dict['created_count']:,}")
    table.add_row("Reused Existing Resources", f"{info_dict['reused_count']:,}")
    table.add_row("Registered URN Aliases", f"{info_dict['alias_count']:,}")
    table.add_row("Created At", str(info_dict["created_at"] or ""))
    console.print(table)

    stats = info_dict.get("stats") or {}
    if stats:
        s_table = Table(title="Ingested Entities Breakdown", border_style="green")
        s_table.add_column("Entity / Table", style="bold green")
        s_table.add_column("Count", justify="right", style="yellow")
        for entity_name, count in sorted(stats.items()):
            s_table.add_row(entity_name, f"{count:,}")
        console.print(s_table)


def _format_urn_id(urn: str) -> str:
    """Extract a human-friendly identifier from a URN."""
    if not urn:
        return ""
    parts = urn.split(":")
    if len(parts) >= 4:
        return parts[-2].split(".")[-1]
    return urn.split(".")[-1]


@compare_app.command("batch")
def compare_batch_cmd(
    batch_id: int = typer.Argument(..., help="IngestBatch ID to compare against the bank."),
    resource_type: str | None = typer.Option(
        None, "--type", "-t", help="Filter comparison by resource type (e.g. QuestionItem)."
    ),
    threshold: float = typer.Option(0.75, "--threshold", help="Minimum similarity score."),
    limit: int = typer.Option(15, "--limit", "-n", help="Max candidate pairs to display in table."),
    max_candidates: int = typer.Option(
        1000, "--max-candidates", "-m", help="Max candidate pairs to include in the plan."
    ),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .compare.plan.yaml & .report.md."
    ),
    no_write: bool = typer.Option(
        False, "--no-write", help="Do not write .compare.plan.yaml and .report.md to disk."
    ),
) -> None:
    """Compare resources from a specific IngestBatch against existing ReQuest bank entities."""
    configure_django_for_cli()
    from fairwddi.ingest.comparator import compare_batch
    from fairwddi.models import IngestBatch

    batch = IngestBatch.objects.filter(id=batch_id).first()
    if not batch:
        console.print(f"[bold red]Compare Error:[/bold red] IngestBatch #{batch_id} not found.")
        raise typer.Exit(code=1)

    effective_output_dir = (
        output_dir if output_dir is not None else (None if no_write else Path("."))
    )

    try:
        plan = compare_batch(
            batch_id=batch_id,
            threshold=threshold,
            output_dir=effective_output_dir,
            limit=max_candidates,
            resource_type=resource_type,
        )
    except Exception as exc:
        console.print(f"[bold red]Compare Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        Panel(
            f"[bold]Batch #{batch_id}[/bold]: [cyan]{batch.file_name}[/cyan] "
            f"({batch.source_format})\n"
            f"[dim]Threshold:[/dim] [yellow]{threshold:.2f}[/yellow]   "
            f"[dim]Candidates Found:[/dim] [bold green]{len(plan.actions):,}[/bold green]   "
            f"[dim]Job ID:[/dim] [magenta]{plan.job_id}[/magenta]",
            title="[bold green]Ingest Batch Harmonization Comparison[/bold green]",
            border_style="green",
        )
    )

    total = len(plan.actions)
    if total == 0:
        console.print("[yellow]No harmonization candidate pairs found above threshold.[/yellow]\n")
        return

    # 1. Summary Breakdown Table
    summary_table = Table(title="Candidate Pair Breakdown", border_style="cyan")
    summary_table.add_column("Dimension", style="bold")
    summary_table.add_column("Category / Tier", style="cyan")
    summary_table.add_column("Count", justify="right", style="yellow")
    summary_table.add_column("% Share", justify="right", style="dim")

    by_res = plan.summary.get("by_resource_type", {})
    for r_type, count in sorted(by_res.items(), key=lambda x: -x[1]):
        pct = f"{(count / total * 100):.1f}%"
        summary_table.add_row("Resource Type", r_type, f"{count:,}", pct)

    by_match = plan.summary.get("by_match_type", {})
    for m_type, count in sorted(by_match.items(), key=lambda x: -x[1]):
        pct = f"{(count / total * 100):.1f}%"
        summary_table.add_row("Match Tier", m_type, f"{count:,}", pct)

    console.print(summary_table)

    # 2. Sample Candidates Table
    display_limit = min(limit, total)
    cand_table = Table(
        title=f"Sample Discovered Candidates (Showing {display_limit} of {total:,})",
        border_style="yellow",
    )
    cand_table.add_column("Type", style="bold green")
    cand_table.add_column("Match Tier", style="magenta")
    cand_table.add_column("Conf", justify="right", style="yellow")
    cand_table.add_column("Action", style="cyan")
    cand_table.add_column("Source Candidate", style="white")
    cand_table.add_column("Target (Bank Entity)", style="white")

    for a in plan.actions[:display_limit]:
        src_info = (
            a.details.get("source_name")
            or a.details.get("source_text")
            or _format_urn_id(a.source_urn)
        )
        tgt_info = (
            a.details.get("target_name")
            or a.details.get("target_text")
            or (_format_urn_id(a.target_urn) if a.target_urn else "")
        )
        if isinstance(src_info, dict):
            src_info = src_info.get("fr") or src_info.get("en") or next(iter(src_info.values()), "")
        if isinstance(tgt_info, dict):
            tgt_info = tgt_info.get("fr") or tgt_info.get("en") or next(iter(tgt_info.values()), "")

        src_disp = (
            f"[bold cyan]{str(src_info)[:45]}[/bold cyan]\n[dim]{a.source_urn}[/dim]"
            if src_info
            else a.source_urn
        )
        tgt_disp = (
            f"[bold cyan]{str(tgt_info)[:45]}[/bold cyan]\n[dim]{a.target_urn}[/dim]"
            if tgt_info and a.target_urn
            else (a.target_urn or "")
        )

        cand_table.add_row(
            a.resource_type,
            a.match_type or "",
            f"{a.confidence:.2f}",
            a.action,
            src_disp,
            tgt_disp,
        )

    console.print(cand_table)
    if total > display_limit:
        more_count = total - display_limit
        console.print(f"[dim]... and {more_count:,} more candidate pairs in full report.[/dim]\n")

    # 3. Artifact Paths
    if effective_output_dir is not None:
        stem = Path(batch.file_name).stem
        plan_path = effective_output_dir / f"{stem}.batch{batch_id}.compare.plan.yaml"
        report_path = effective_output_dir / f"{stem}.batch{batch_id}.compare.report.md"
        console.print("[bold green]Generated Artifacts:[/bold green]")
        console.print(f"  • Plan YAML: [cyan]{plan_path}[/cyan]")
        console.print(f"  • Report:    [cyan]{report_path}[/cyan]\n")

    # 4. Next Steps
    console.print("[bold]Next Steps:[/bold]")
    console.print(
        f"  1. Discover & filter candidates interactively:\n"
        f"     [yellow]fairwddi compare discover --batch-id {batch_id} --type QuestionItem[/yellow]"
    )
    console.print(
        f"  2. Generate review-gated Harmonization Plan:\n"
        f"     [yellow]fairwddi harmonize plan --batch-id {batch_id}[/yellow]"
    )
    console.print(
        "  3. Inspect in Question Bank Explorer web UI:\n"
        "     [yellow]fairwddi serve --open[/yellow]\n"
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
    batch_id: int | None = typer.Option(None, "--batch-id", "-b", help="Scope to IngestBatch ID."),
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
    batch_id: int | None = typer.Option(None, "--batch-id", "-b", help="Scope to IngestBatch ID."),
    resource_type: str | None = typer.Option(None, "--type", "-t", help="Filter by resource type."),
    study_urn: str | None = typer.Option(None, "--study", "-s", help="Scope to StudyUnit URN."),
    query: str | None = typer.Option(None, "--query", "-q", help="Substring filter."),
    threshold: float = typer.Option(0.75, "--threshold", help="Similarity threshold."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .harmonize.plan.yaml & .report.md."
    ),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Approve review gate."),
) -> None:
    """Generate a review-gated Harmonization Plan (.harmonize.plan.yaml & .report.md)."""
    from fairwddi.ingest.harmonizer import plan_harmonization

    configure_django_for_cli()
    effective_output_dir = output_dir if output_dir is not None else Path(".")
    plan = plan_harmonization(
        batch_id=batch_id,
        resource_type=resource_type,
        study_urn=study_urn,
        query=query,
        threshold=threshold,
        output_dir=effective_output_dir,
        auto_approve=auto_approve,
    )
    console.print(
        f"[bold green]Generated Harmonization Plan [cyan]{plan.job_id}[/cyan]:[/bold green] "
        f"[yellow]{len(plan.actions)}[/yellow] action(s), "
        f"[yellow]{plan.pending_review_count}[/yellow] pending review."
    )
    plan_path = effective_output_dir / f"{plan.job_id}.harmonize.plan.yaml"
    report_path = effective_output_dir / f"{plan.job_id}.harmonize.report.md"
    console.print(f"  • Plan YAML: [cyan]{plan_path}[/cyan]")
    console.print(f"  • Report:    [cyan]{report_path}[/cyan]")
    console.print("\n[dim]To apply this plan:[/dim]")
    console.print(f"  [yellow]fairwddi harmonize apply {plan_path}[/yellow]\n")


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


@harmonize_app.command("elevate")
def harmonize_elevate_cmd(
    source_urns: list[str] = typer.Option(
        ...,
        "--source",
        "-s",
        help="Source study-specific URN(s) to elevate (can specify multiple times).",
    ),
    target_urn: str | None = typer.Option(
        None,
        "--target-urn",
        "-t",
        help="Explicit canonical generic DDI URN (auto-generated with slug randomizer if omitted).",
    ),
    resource_type: str | None = typer.Option(
        None,
        "--type",
        "-T",
        help="Optional DDI resource type. Auto-inferred from source URNs if omitted.",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Human-readable label/name for the elevated generic resource.",
    ),
    agency: str | None = typer.Option(
        None,
        "--agency",
        "-a",
        help="DDI maintenance agency (defaults to DDI_AGENCY or 'fr.cdsp').",
    ),
    update_references: bool = typer.Option(
        True,
        "--update-references/--no-update-references",
        help="Update relational and junction references across the DDI cascade.",
    ),
    retire_sources: bool = typer.Option(
        True,
        "--retire-sources/--keep-sources",
        help="Retire source records from primary entity table while preserving URNAlias.",
    ),
    note: str = typer.Option(
        "",
        "--note",
        help="Audit/provenance note.",
    ),
) -> None:
    """Elevate one or more study-specific resources into a generic harmonized resource."""
    from fairwddi.ingest.harmonizer import elevate_resource

    configure_django_for_cli()
    try:
        res = elevate_resource(
            source_urns=source_urns,
            generic_urn=target_urn,
            resource_type=resource_type,
            generic_name=name,
            agency=agency,
            retire_sources=retire_sources,
            update_references=update_references,
            provenance_note=note,
        )
    except Exception as exc:
        console.print(f"[bold red]Elevation Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Elevated Resource Created ({res['resource_type']})", border_style="green")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="green")
    table.add_row("Generic URN", f"[bold green]{res['generic_urn']}[/bold green]")
    table.add_row("Resource Type", res["resource_type"])
    table.add_row("Registry Status", "[bold cyan]elevated[/bold cyan]")
    table.add_row("Sources Elevated", str(len(res["source_urns"])))
    for s_idx, s_urn in enumerate(res["source_urns"], 1):
        table.add_row(f"  • Source #{s_idx}", s_urn)
    table.add_row("Aliases Created", str(res["aliases_created"]))
    table.add_row("Semantic Links", str(res["semantic_links_created"]))
    table.add_row("Retired Sources", str(res["retired_sources"]))

    refs = res.get("updated_references", {})
    if refs:
        for ref_k, ref_v in refs.items():
            table.add_row(f"  ↳ Ref: {ref_k}", f"{ref_v} updated")

    console.print(table)
    job_id = res["job_id"]
    console.print(f"\n[dim]To revert: [yellow]fairwddi harmonize undo {job_id}[/yellow][/dim]\n")


@harmonize_app.command("absorb")
def harmonize_absorb_cmd(
    source_urns: list[str] = typer.Option(
        ...,
        "--source",
        "-s",
        help="Source study-specific URN(s) to absorb (can specify multiple times).",
    ),
    into_urn: str = typer.Option(
        ...,
        "--into",
        "-i",
        help="Target canonical harmonized/elevated URN to absorb into.",
    ),
    resource_type: str | None = typer.Option(
        None,
        "--type",
        "-T",
        help="Optional DDI resource type. Auto-inferred from into_urn if omitted.",
    ),
    update_references: bool = typer.Option(
        True,
        "--update-references/--no-update-references",
        help="Update relational references across the DDI cascade to point to into_urn.",
    ),
    retire_sources: bool = typer.Option(
        True,
        "--retire-sources/--keep-sources",
        help="Retire source records from primary entity table while preserving URNAlias.",
    ),
    note: str = typer.Option(
        "",
        "--note",
        help="Audit/provenance note.",
    ),
) -> None:
    """Absorb one or more study resources into an existing harmonized/elevated resource."""
    from fairwddi.ingest.harmonizer import absorb_resource

    configure_django_for_cli()
    try:
        res = absorb_resource(
            source_urns=source_urns,
            into_urn=into_urn,
            resource_type=resource_type,
            retire_sources=retire_sources,
            update_references=update_references,
            provenance_note=note,
        )
    except Exception as exc:
        console.print(f"[bold red]Absorption Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(
        title=f"Resource Absorbed into ({res['resource_type']})", border_style="green"
    )
    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="green")
    table.add_row("Target Harmonized URN", f"[bold green]{res['target_urn']}[/bold green]")
    table.add_row("Resource Type", res["resource_type"])
    table.add_row("Sources Absorbed", str(len(res["source_urns"])))
    for s_idx, s_urn in enumerate(res["source_urns"], 1):
        table.add_row(f"  • Source #{s_idx}", s_urn)
    table.add_row("Aliases Created", str(res["aliases_created"]))
    table.add_row("Semantic Links", str(res["semantic_links_created"]))
    table.add_row("Retired Sources", str(res["retired_sources"]))

    refs = res.get("updated_references", {})
    if refs:
        for ref_k, ref_v in refs.items():
            table.add_row(f"  ↳ Ref: {ref_k}", f"{ref_v} updated")

    console.print(table)
    job_id = res["job_id"]
    console.print(f"\n[dim]To revert: [yellow]fairwddi harmonize undo {job_id}[/yellow][/dim]\n")


@harmonize_app.command("rename")
def harmonize_rename_cmd(
    old_urn: str = typer.Argument(..., help="Current URN to rename/promote."),
    new_urn: str = typer.Argument(..., help="New canonical generic DDI URN."),
    resource_type: str | None = typer.Option(
        None,
        "--type",
        "-T",
        help="DDI resource type (auto-detected from UrnRegistry if omitted).",
    ),
    update_references: bool = typer.Option(
        True,
        "--update-references/--no-update-references",
        help="Update relational references across the DDI cascade.",
    ),
    note: str = typer.Option(
        "",
        "--note",
        help="Audit/provenance note.",
    ),
) -> None:
    """Atomically rename a resource URN, updating cascade references and creating an alias."""
    from fairwddi.ingest.harmonizer import migrate_urn

    configure_django_for_cli()
    try:
        res = migrate_urn(
            old_urn=old_urn,
            new_urn=new_urn,
            resource_type=resource_type,
            provenance_note=note,
        )
    except Exception as exc:
        console.print(f"[bold red]Rename Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Successfully Renamed URN:[/bold green]\n"
        f"  • Old: [cyan]{old_urn}[/cyan]\n"
        f"  • New: [bold green]{res['generic_urn']}[/bold green]\n"
        f"  • Aliased: [yellow]{res['aliases_created']}[/yellow] | "
        f"References updated: [yellow]{sum(res.get('updated_references', {}).values())}[/yellow]"
    )


@harmonize_app.command("undo")
def harmonize_undo_cmd(
    job_id: str = typer.Argument(..., help="Harmonization job_id to revert."),
) -> None:
    """Revert an applied Harmonization Job or Elevation Job using EventLog snapshots."""
    from fairwddi.ingest.harmonizer import undo_harmonization

    configure_django_for_cli()
    try:
        res = undo_harmonization(job_id)
    except Exception as exc:
        console.print(f"[bold red]Harmonize Undo Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    restored = res.get("restored_sources", res.get("restored_targets", 0))
    tgt_info = (
        f", rolled back target [cyan]{res['target_urn']}[/cyan]"
        if res.get("is_absorption")
        else ""
    )
    console.print(
        f"[bold green]Reverted Job [cyan]{res['job_id']}[/cyan]:[/bold green] "
        f"restored {restored} resource(s){tgt_info}, "
        f"removed {res.get('removed_aliases', 0)} alias(es)."
    )


@app.command("serve")
@app.command(
    "ui",
    help="Alias for 'serve': launch the Question Bank Explorer web app and REST API.",
)
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address."),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port number."),
    open_browser: bool = typer.Option(
        False, "--open", "-o", help="Automatically open browser to Visual Explorer."
    ),
) -> None:
    """Launch the interactive Question Bank & Harmonization Explorer web app and REST API."""
    configure_django_for_cli()
    from fairwddi.api.server import run_server

    try:
        run_server(host=host, port=port, open_browser=open_browser)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")


if __name__ == "__main__":
    app()

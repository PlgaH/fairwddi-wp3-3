"""FAIRwDDI Lifecycle CLI application using Typer and Rich."""

from pathlib import Path
from typing import Any

import typer
import typer.core
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import fairwddi
from fairwddi.db.config import configure_django_for_cli, get_database_config
from fairwddi.db.ddl import export_postgres_ddl


class DefaultToRunImportGroup(typer.core.TyperGroup):
    """Route ``fairwddi import <file> [OPTIONS]`` directly to the ``run`` command."""

    def resolve_command(self, ctx: Any, args: list[str]) -> tuple[str | None, Any, list[str]]:
        if args and args[0] not in ("--help", "-h"):
            if args[0] not in self.commands:
                has_explicit_subcmd = any(a in self.commands for a in args if not a.startswith("-"))
                if not has_explicit_subcmd:
                    args = ["run", *args]
        return super().resolve_command(ctx, args)


app = typer.Typer(
    name="fairwddi",
    help="FAIR DDI-Lifecycle CLI for social science question bank interoperability.",
    no_args_is_help=True,
)
db_app = typer.Typer(
    name="db",
    help="Database management, migrations, vocabulary loading, and DDL export commands.",
    no_args_is_help=True,
)
app.add_typer(db_app, name="db")

preflight_app = typer.Typer(
    name="preflight",
    help="Stage 1: Preflight readiness checks, profile QA, URN audits, and DDI-C upgrades.",
    no_args_is_help=True,
)
app.add_typer(preflight_app, name="preflight")

import_app = typer.Typer(
    name="import",
    cls=DefaultToRunImportGroup,
    help="Deterministic DDI metadata import (run directly via `fairwddi import <file>`).",
    no_args_is_help=True,
)
app.add_typer(import_app, name="import")

group_app = typer.Typer(
    name="group",
    help="Curate and inspect reusable DDI resource Groups (with canonical URN & slug).",
    no_args_is_help=True,
)
app.add_typer(group_app, name="group")

compare_app = typer.Typer(
    name="compare",
    help="Read-only two-set, three-layer (syntactic, semantic, conceptual) DDI comparison.",
    no_args_is_help=True,
)
app.add_typer(compare_app, name="compare")

harmonize_app = typer.Typer(
    name="harmonize",
    help="Plan, approve, execute, and undo comparison-driven DDI harmonization.",
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

    if load_vocab:
        vocab_file = Path("vocab/ELSST_R6.ttl")
        if vocab_file.exists():
            console.print("[dim]Loading standard ELSST vocabulary...[/dim]")
            stats = load_skos_vocabulary(str(vocab_file), max_levels=1)
            loaded_count = stats.get("total_concepts", stats.get("concepts_loaded", 0))
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
# Modular FAIRwDDI Workflow CLI Groups
# (preflight, import, group, compare, harmonize)
# -----------------------------------------------------------------------------


@preflight_app.command("check")
def preflight_check_cmd(
    file_path: str = typer.Argument(..., help="Path to incoming DDI-C or DDI-L metadata file."),
    profile: str = typer.Option("request", "--profile", "-p", help="Profile preset or YAML path."),
    output_dir: Path = typer.Option(
        Path("."),
        "--output-dir",
        "-o",
        help="Directory to write .preflight.json & .preflight.report.md (default: '.').",
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Mark the preflight review gate as approved."
    ),
) -> None:
    """Inspect a DDI-C or DDI-L file for readiness, profile compliance, URNs, and links."""
    from fairwddi.importer.preflight import run_preflight_check

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

    stem = Path(file_path).stem
    console.print(
        f"[bold green]Preflight report written:[/bold green] "
        f"[cyan]{output_dir / f'{stem}.preflight.json'}[/cyan], "
        f"[cyan]{output_dir / f'{stem}.preflight.report.md'}[/cyan]"
    )


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
    category_scheme_mode: str = typer.Option(
        "single",
        "--category-scheme-mode",
        help="CategoryScheme granularity: 'single' (shared) or 'per_codelist' (1-1 per CodeList).",
    ),
) -> None:
    """Explicitly upgrade a classic or multilingual DDI-Codebook file to DDI-Lifecycle on disk."""
    from fairwddi.importer.preflight import upgrade_ddic_to_ddil

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
            category_scheme_mode=category_scheme_mode,  # type: ignore[arg-type]
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
    from fairwddi.importer.profiles import list_available_profiles

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


@preflight_app.command("profile")
def preflight_profile_cmd(
    file_path: str = typer.Argument(..., help="Path to DDI-C or DDI-L XML metadata file."),
    profile: str = typer.Option("request", "--profile", "-p", help="Profile preset or YAML path."),
    output_dir: Path = typer.Option(
        Path("."),
        "--output-dir",
        "-o",
        help="Directory to write <stem>.profile.json & <stem>.profile.md (default: '.').",
    ),
    title: str | None = typer.Option(None, "--title", help="Custom title for the profile report."),
) -> None:
    """Generate full DDI-C or DDI-L JSON and Markdown profile reports."""
    from fairwddi.importer.preflight import run_preflight_profile

    try:
        res = run_preflight_profile(
            file_path=file_path,
            profile=profile,
            output_dir=output_dir,
            title=title,
        )
    except Exception as exc:
        console.print(f"[bold red]Preflight Profile Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(
        title=f"DDI Profile Report [{res['source_file']}]",
        border_style="cyan",
    )
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="yellow")
    table.add_row("Specification", str(res["specification"]))
    if res.get("quality_grade"):
        table.add_row("Quality Grade", f"{res['quality_grade']} ({res.get('quality_score', '-')})")
    if res.get("total_elements") is not None:
        table.add_row("Total Elements / Resources", str(res["total_elements"]))
    console.print(table)
    console.print(
        f"[bold green]Profile artifacts written:[/bold green] "
        f"[cyan]{res['json_file']}[/cyan], [cyan]{res['markdown_file']}[/cyan]"
    )


@import_app.command("run")
def import_run_cmd(
    file_path: str = typer.Argument(..., help="Path to DDI-C or DDI-L metadata file to import."),
    profile: str = typer.Option("request", "--profile", "-p", help="Import profile."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory for preflight, upgrade, and import artifacts."
    ),
    agency: str | None = typer.Option(
        None, "--agency", "-a", help="Override DDI agency ID for DDI-C upgrade."
    ),
    id_strategy: str = typer.Option(
        "hierarchical", "--id-strategy", help="DDI-C upgrade ID strategy."
    ),
    harmonize_codes: bool = typer.Option(
        True,
        "--harmonize-codes/--no-harmonize-codes",
        help="Intra-file CodeList/Category deduplication during DDI-C upgrade.",
    ),
    harmonize_questions: bool = typer.Option(
        True,
        "--harmonize-questions/--no-harmonize-questions",
        help="Intra-file QuestionItem deduplication during DDI-C upgrade.",
    ),
    category_scheme_mode: str = typer.Option(
        "single",
        "--category-scheme-mode",
        help="CategoryScheme granularity for DDI-C upgrade: 'single' or 'per_codelist'.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only without writing DB records."),
    force_reload: bool = typer.Option(
        False, "--force-reload", help="Replace previous active IngestBatch with identical SHA-256."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Automatically approve review gates."
    ),
) -> None:
    """Import a DDI metadata file cleanly into ReQuest core tables (zero harmonization)."""
    from fairwddi.importer.pipeline import run_import

    configure_django_for_cli()
    try:
        res = run_import(
            file_path=file_path,
            profile=profile,
            output_dir=output_dir,
            agency=agency,
            id_strategy=id_strategy,
            harmonize_codes=harmonize_codes,
            harmonize_questions=harmonize_questions,
            category_scheme_mode=category_scheme_mode,  # type: ignore[arg-type]
            dry_run=dry_run,
            force_reload=force_reload,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Import Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    status = res.get("status", "completed")
    if status.startswith("halted"):
        console.print(
            f"[bold yellow]Import halted at {res.get('stage')}:[/bold yellow] "
            f"{res.get('pending_review_count', 0)} pending review item(s), "
            f"{res.get('error_count', 0)} error(s)."
        )
        raise typer.Exit(code=2)

    if status == "planned_only":
        imp_plan = res["import_plan"]
        console.print(
            f"[green]Dry-run plan [bold]{imp_plan.job_id}[/bold] generated[/green] "
            f"({imp_plan.summary.get('planned_actions', 0)} planned action(s))."
        )
        return

    imp = res.get("import_result") or {}
    table = Table(title="Import Execution Summary", border_style="green")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="yellow")
    table.add_row("Batch ID", f"#{res.get('batch_id')}")
    table.add_row("Status", str(imp.get("status", status)))
    table.add_row("Created URNs", str(imp.get("created_count", 0)))
    table.add_row("Reused URNs", str(imp.get("reused_count", 0)))
    table.add_row("Quarantined", str(imp.get("quarantine_count", 0)))
    table.add_row("Frequency Rows", str(imp.get("frequency_rows_count", 0)))
    console.print(table)


@import_app.command("plan")
def import_plan_cmd(
    file_path: str = typer.Argument(
        ..., help="Path to DDI-Lifecycle (.xml/.json/.jsonl) or DDI-Codebook (.xml) file."
    ),
    profile: str = typer.Option("request", "--profile", "-p", help="Import profile."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .import.plan.yaml & .report.md."
    ),
    force_reload: bool = typer.Option(
        False, "--force-reload", help="Ignore prior duplicate SHA-256."
    ),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Approve review gate."),
) -> None:
    """Generate a zero-write deterministic Import Plan (.import.plan.yaml & .report.md)."""
    from fairwddi.importer.loader import plan_import

    configure_django_for_cli()
    path = Path(file_path).resolve()
    eff_out = output_dir or path.parent
    try:
        plan = plan_import(
            file_path=path,
            profile=profile,
            output_dir=eff_out,
            force_reload=force_reload,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Import Plan Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    plan_out = eff_out / f"{path.stem}.import.plan.yaml"
    console.print(
        f"[bold green]Import Plan created:[/bold green] {plan_out} "
        f"(actions={len(plan.actions)}, review_pending={plan.pending_review_count})"
    )


@import_app.command("execute")
def import_execute_cmd(
    plan_or_file: str = typer.Argument(
        ..., help="Path to approved .import.plan.yaml file or metadata file."
    ),
    profile: str = typer.Option("request", "--profile", "-p", help="Import profile."),
    force_reload: bool = typer.Option(
        False, "--force-reload", help="Replace matching active batch."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Approve pending review items."
    ),
) -> None:
    """Execute an Import Plan (or load a file directly) into ReQuest core tables."""
    from fairwddi.importer.loader import execute_import

    configure_django_for_cli()
    try:
        res = execute_import(
            plan_or_file,
            profile=profile,
            force_reload=force_reload,
            auto_approve=auto_approve,
        )
    except Exception as exc:
        console.print(f"[bold red]Import Execute Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Import Batch #{res['batch_id']} ({res['status']}):[/bold green] "
        f"created={res['created_count']}, reused={res['reused_count']}, "
        f"quarantined={res['quarantine_count']}, freq_rows={res['frequency_rows_count']}"
    )


@import_app.command("undo")
def import_undo_cmd(
    batch_id: int = typer.Argument(..., help="IngestBatch ID to roll back cleanly."),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Bypass confirmation prompt.",
    ),
) -> None:
    """Atomically roll back an imported batch while enforcing referential integrity."""
    from fairwddi.importer.loader import get_import_batch_status, undo_import

    configure_django_for_cli()
    if not force:
        try:
            info = get_import_batch_status(batch_id)
            prompt_msg = (
                f"Roll back Import Batch #{batch_id} "
                f"({info['file_name']}, {info['created_count']} created URN(s))?"
            )
        except Exception:
            prompt_msg = f"Roll back Import Batch #{batch_id}?"
        typer.confirm(prompt_msg, default=False, abort=True)

    try:
        res = undo_import(batch_id)
    except Exception as exc:
        console.print(f"[bold red]Import Undo Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Rolled back Batch #{res['batch_id']}:[/bold green] "
        f"deleted {res['deleted_core_resources_count']} core resource(s)."
    )


@import_app.command("list")
def import_list_cmd(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by batch status."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max batches to list."),
) -> None:
    """List recorded import batches newest first."""
    from fairwddi.importer.loader import list_import_batches

    configure_django_for_cli()
    rows = list_import_batches(status=status, limit=limit)
    if not rows:
        console.print("[yellow]No import batches recorded yet.[/yellow]")
        return

    table = Table(title="Import Batches", border_style="cyan")
    table.add_column("ID", justify="right", style="bold cyan")
    table.add_column("File", style="white")
    table.add_column("Format", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created", justify="right")
    table.add_column("Reused", justify="right")
    for r in rows:
        table.add_row(
            str(r["id"]),
            str(r["file_name"]),
            str(r["source_format"]),
            str(r["status"]),
            str(r["created_count"]),
            str(r["reused_count"]),
        )
    console.print(table)


@import_app.command("status")
def import_status_cmd(
    batch_id: int = typer.Argument(..., help="IngestBatch ID to inspect."),
) -> None:
    """Display detailed status and resource counts for a single import batch."""
    from fairwddi.importer.loader import get_import_batch_status

    configure_django_for_cli()
    try:
        info_dict = get_import_batch_status(batch_id)
    except Exception as exc:
        console.print(f"[bold red]Import Status Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Import Batch #{info_dict['id']}", border_style="cyan")
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", style="yellow")
    for k in (
        "file_name",
        "source_format",
        "status",
        "created_count",
        "reused_count",
        "file_sha256",
    ):
        table.add_row(k, str(info_dict.get(k)))
    if info_dict.get("stats"):
        table.add_row("stats", str(info_dict["stats"]))
    console.print(table)


# ---------------------------------------------------------------------------
# DDI Group Management CLI (`fairwddi group`)
# ---------------------------------------------------------------------------


@group_app.command("create")
def group_create_cmd(
    name: str = typer.Argument(..., help="Human-readable Group name."),
    slug: str | None = typer.Option(None, "--slug", "-s", help="Unique short slug/nickname."),
    group_type: str = typer.Option(
        "custom", "--type", "-t", help="Group type (e.g. series, thematic, question_grid, custom)."
    ),
    description: str | None = typer.Option(None, "--description", "-d", help="Group description."),
    urn: str | None = typer.Option(None, "--urn", help="Explicit canonical DDI URN."),
    agency: str | None = typer.Option(None, "--agency", "-a", help="Agency for URN generation."),
    members: list[str] = typer.Option(
        [], "--member", "-m", help="Initial member URN (repeatable)."
    ),
) -> None:
    """Create a reusable DDI Group (longitudinal series, thematic scope, etc.)."""
    from fairwddi.groups.manager import create_group

    configure_django_for_cli()
    try:
        res = create_group(
            name=name,
            slug=slug,
            group_type=group_type,
            description=description,
            urn=urn,
            member_urns=members,
            agency=agency,
        )
    except Exception as exc:
        console.print(f"[bold red]Group Create Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Created Group [cyan]{res['slug']}[/cyan][/bold green] "
        f"({res['urn']}) with {res['member_count']} member(s)."
    )


@group_app.command("list")
def group_list_cmd(
    group_type: str | None = typer.Option(None, "--type", "-t", help="Filter by group_type."),
) -> None:
    """List curated DDI Groups with slugs, URNs, and member counts."""
    from fairwddi.groups.manager import list_groups

    configure_django_for_cli()
    rows = list_groups(group_type=group_type)
    if not rows:
        console.print("[yellow]No DDI Groups found.[/yellow]")
        return

    table = Table(title="Curated DDI Groups", border_style="cyan")
    table.add_column("Slug", style="bold green")
    table.add_column("Name", style="white")
    table.add_column("Type", style="cyan")
    table.add_column("Members", justify="right", style="yellow")
    table.add_column("URN", style="dim")
    for r in rows:
        table.add_row(
            str(r["slug"] or "-"),
            str(r["name"]),
            str(r["group_type"]),
            str(r["member_count"]),
            str(r["urn"]),
        )
    console.print(table)


@group_app.command("show")
def group_show_cmd(
    identifier: str = typer.Argument(..., help="Group slug or canonical URN."),
) -> None:
    """Inspect a Group and its members."""
    from fairwddi.groups.manager import get_group_details

    configure_django_for_cli()
    try:
        info_dict = get_group_details(identifier)
    except Exception as exc:
        console.print(f"[bold red]Group Show Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        Panel(
            f"[bold]Name:[/bold] {info_dict['name']}\n"
            f"[bold]Slug:[/bold] {info_dict['slug'] or '-'}\n"
            f"[bold]URN:[/bold] {info_dict['urn']}\n"
            f"[bold]Type:[/bold] {info_dict['group_type']} | "
            f"[bold]Origin:[/bold] {info_dict['origin']}\n"
            f"[bold]Members ({info_dict['member_count']}):[/bold]",
            title=f"Group: {info_dict['slug'] or info_dict['urn']}",
            border_style="cyan",
        )
    )
    if info_dict["members"]:
        table = Table(border_style="cyan")
        table.add_column("Type", style="cyan")
        table.add_column("Origin", style="green")
        table.add_column("URN", style="white")
        for m in info_dict["members"]:
            table.add_row(m["resource_type"], m["origin"], m["urn"])
        console.print(table)


@group_app.command("add")
def group_add_cmd(
    identifier: str = typer.Argument(..., help="Group slug or canonical URN."),
    member_urns: list[str] = typer.Argument(..., help="Resource URN(s) to add to the group."),
) -> None:
    """Add one or more resource URNs to an existing Group."""
    from fairwddi.groups.manager import add_group_members

    configure_django_for_cli()
    try:
        res = add_group_members(identifier, member_urns)
    except Exception as exc:
        console.print(f"[bold red]Group Add Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Group [cyan]{res['slug'] or res['urn']}[/cyan]:[/bold green] "
        f"added {res['added_count']} member(s) (total={res['member_count']})."
    )


@group_app.command("remove")
def group_remove_cmd(
    identifier: str = typer.Argument(..., help="Group slug or canonical URN."),
    member_urns: list[str] = typer.Argument(..., help="Resource URN(s) to remove."),
) -> None:
    """Remove member URN(s) from a Group."""
    from fairwddi.groups.manager import remove_group_members

    configure_django_for_cli()
    try:
        res = remove_group_members(identifier, member_urns)
    except Exception as exc:
        console.print(f"[bold red]Group Remove Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Group [cyan]{res['slug'] or res['urn']}[/cyan]:[/bold green] "
        f"removed {res['removed_count']} member(s) (remaining={res['member_count']})."
    )


@group_app.command("rename")
def group_rename_cmd(
    identifier: str = typer.Argument(..., help="Group slug or canonical URN."),
    name: str | None = typer.Option(None, "--name", "-n", help="New display name."),
    slug: str | None = typer.Option(None, "--slug", "-s", help="New unique short slug."),
    description: str | None = typer.Option(None, "--description", "-d", help="New description."),
) -> None:
    """Update a Group's name, short slug, and/or description."""
    from fairwddi.groups.manager import rename_group

    configure_django_for_cli()
    try:
        res = rename_group(identifier, name=name, slug=slug, description=description)
    except Exception as exc:
        console.print(f"[bold red]Group Rename Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Updated Group:[/bold green] slug={res['slug']} ({res['urn']})")


@group_app.command("delete")
def group_delete_cmd(
    identifier: str = typer.Argument(..., help="Group slug or canonical URN."),
) -> None:
    """Delete a Group and its dcterms:isPartOf membership links."""
    from fairwddi.groups.manager import delete_group

    configure_django_for_cli()
    try:
        res = delete_group(identifier)
    except Exception as exc:
        console.print(f"[bold red]Group Delete Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Deleted Group:[/bold green] {res['slug'] or res['urn']}")


# ---------------------------------------------------------------------------
# Three-Layer Read-Only Compare CLI (`fairwddi compare`)
# ---------------------------------------------------------------------------


@compare_app.command("run")
def compare_run_cmd(
    source: str = typer.Option(
        ...,
        "--source",
        "-s",
        help=(
            "Source set (group:<slug|urn>, batch:<id>, study:<urn>, "
            "bank[:all|imported|harmonized], urn:<u1,u2>)."
        ),
    ),
    target: str = typer.Option(
        ...,
        "--target",
        "-t",
        help=(
            "Target set (group:<slug|urn>, batch:<id>, study:<urn>, "
            "bank[:all|imported|harmonized], urn:<u1,u2>)."
        ),
    ),
    config: str | None = typer.Option(
        None, "--config", "-c", help="Comparison preset name or YAML file path."
    ),
    levels: list[str] = typer.Option(
        [],
        "--level",
        "-l",
        help="Correspondence level(s): syntactic, semantic, conceptual, all (repeatable).",
    ),
    resource_types: list[str] = typer.Option(
        [],
        "--type",
        help="Resource type(s) to compare (repeatable or comma-separated).",
    ),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Write .comparison.{yaml,json} and .comparison.report.md."
    ),
    output_format: str = typer.Option(
        "yaml", "--format", "-f", help="Structured output format: yaml or json."
    ),
) -> None:
    """Compare two resolved DDI resource sets across syntactic, semantic, and conceptual layers."""
    from fairwddi.compare.engine import run_comparison

    configure_django_for_cli()
    eff_out = output_dir or Path(".")
    try:
        res = run_comparison(
            source=source,
            target=target,
            config=config,
            levels=levels or None,
            resource_types=resource_types or None,
            output_dir=eff_out,
            output_format=output_format,  # type: ignore[arg-type]
        )
    except Exception as exc:
        console.print(f"[bold red]Compare Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Comparison Results [{res.job_id}]", border_style="cyan")
    table.add_column("ID", style="cyan")
    table.add_column("Level", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Match", style="yellow")
    table.add_column("Conf", justify="right")
    table.add_column("CodeList Qual", style="blue")
    table.add_column("Source -> Target", style="white")
    for cand in res.candidates[:30]:
        table.add_row(
            cand.id,
            cand.level.value,
            cand.resource_type,
            cand.match_type,
            f"{cand.confidence:.2f}",
            cand.qualification.codelist_qualification.value,
            f"{cand.source_urn} -> {cand.target_urn}",
        )
    console.print(table)
    out_ext = "json" if output_format == "json" else "yaml"
    console.print(
        f"[bold green]Saved {len(res.candidates)} candidate(s):[/bold green] "
        f"{eff_out / f'{res.job_id}.comparison.{out_ext}'}"
    )


@compare_app.command("configs")
def compare_configs_cmd() -> None:
    """List built-in comparison configuration presets."""
    from fairwddi.compare.config import list_comparison_configs

    configs = list_comparison_configs()
    if not configs:
        console.print("[yellow]No comparison configs found in profiles/compare.[/yellow]")
        return

    table = Table(title="Comparison Presets", border_style="cyan")
    table.add_column("Name", style="bold green")
    table.add_column("Levels", style="magenta")
    table.add_column("Resource Types", style="cyan")
    table.add_column("Description", style="white")
    for cfg in configs:
        table.add_row(
            cfg["name"],
            ", ".join(str(x) for x in cfg["levels"]),
            ", ".join(str(x) for x in cfg["resource_types"]),
            cfg["description"],
        )
    console.print(table)


@compare_app.command("init-config")
def compare_init_config_cmd(
    output: Path = typer.Argument(Path("compare.yaml"), help="Destination YAML config path."),
    preset: str = typer.Option("default", "--preset", "-p", help="Preset template to copy."),
) -> None:
    """Write a starter comparison configuration YAML file to disk."""
    import yaml

    from fairwddi.compare.config import load_comparison_config

    try:
        cfg = load_comparison_config(preset)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except Exception as exc:
        console.print(f"[bold red]Init-Config Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Wrote comparison config template:[/bold green] {output}")


# ---------------------------------------------------------------------------
# Comparison-Driven Harmonization CLI (`fairwddi harmonize`)
# ---------------------------------------------------------------------------


@harmonize_app.command("plan")
def harmonize_plan_cmd(
    comparison_file: Path = typer.Argument(..., help="Path to .comparison.yaml or .json file."),
    policy: str | None = typer.Option(
        None, "--policy", "-p", help="Harmonization policy preset or YAML path."
    ),
    approve_high: bool = typer.Option(
        False,
        "--approve-high",
        help="Automatically approve candidates meeting policy auto_approve_high criteria.",
    ),
    keep_pending: bool = typer.Option(
        False,
        "--keep-pending",
        help="Keep all candidates pending review (overrides --approve-high).",
    ),
    high_threshold: float | None = typer.Option(
        None,
        "--high-threshold",
        help="Override policy auto_approve_high.min_confidence threshold.",
    ),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", "-o", help="Directory to write .harmonize.plan.yaml & .report.md."
    ),
) -> None:
    """Generate a review-gated Harmonization Plan from comparison results."""
    from fairwddi.harmonize.planner import plan_harmonization

    configure_django_for_cli()
    eff_out = output_dir or comparison_file.parent
    try:
        plan = plan_harmonization(
            comparison_file,
            policy=policy,
            approve_high=approve_high,
            high_threshold=high_threshold,
            keep_pending=keep_pending,
            output_dir=eff_out,
        )
    except Exception as exc:
        console.print(f"[bold red]Harmonize Plan Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Harmonization Plan created:[/bold green] "
        f"{eff_out / f'{plan.job_id}.harmonize.plan.yaml'} "
        f"(total={len(plan.actions)}, approved={plan.approved_count}, "
        f"pending={plan.pending_review_count}, high_tier={plan.high_tier_count})"
    )


@harmonize_app.command("execute")
def harmonize_execute_cmd(
    plan_file: Path = typer.Argument(..., help="Path to .harmonize.plan.yaml file to execute."),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Execute all items ignoring review gate."
    ),
) -> None:
    """Execute approved actions from a Harmonization Plan and record EventLog snapshots."""
    from fairwddi.harmonize.manager import execute_harmonization

    configure_django_for_cli()
    try:
        res = execute_harmonization(plan_file, auto_approve=auto_approve)
    except Exception as exc:
        console.print(f"[bold red]Harmonize Execute Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Executed Harmonization [cyan]{res['job_id']}[/cyan]:[/bold green] "
        f"linked={res['linked_existing_count']}, generated={res['generated_count']}, "
        f"grouped={res['grouped_count']}, semantic_links={res['semantic_links_created']}, "
        f"skipped_unapproved={res.get('skipped_unapproved_count', 0)}"
    )


@harmonize_app.command("approve-high")
def harmonize_approve_high_cmd(
    plan_file: Path = typer.Argument(..., help="Path to .harmonize.plan.yaml file to approve."),
    policy: str | None = typer.Option(None, "--policy", "-p", help="Policy preset or YAML path."),
    high_threshold: float | None = typer.Option(
        None, "--high-threshold", help="Override minimum confidence for high tier."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Optional output path (defaults to in-place update)."
    ),
) -> None:
    """Approve qualifying high-confidence items inside an existing Harmonization Plan."""
    from fairwddi.harmonize.planner import approve_high_actions

    try:
        plan = approve_high_actions(
            plan_file, policy=policy, high_threshold=high_threshold, output_path=output
        )
    except Exception as exc:
        console.print(f"[bold red]Approve-High Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Updated Plan [cyan]{plan.job_id}[/cyan]:[/bold green] "
        f"approved={plan.approved_count}, pending={plan.pending_review_count}, "
        f"gate_approved={plan.review_gate.approved}"
    )


@harmonize_app.command("create")
def harmonize_create_cmd(
    source_urns: list[str] = typer.Option(
        ..., "--source", "-s", help="Source imported resource URN(s) (repeatable)."
    ),
    target_urn: str | None = typer.Option(None, "--target-urn", help="Explicit harmonized URN."),
    resource_type: str | None = typer.Option(None, "--type", "-t", help="DDI resource type."),
    name: str | None = typer.Option(None, "--name", "-n", help="Harmonized resource name."),
    agency: str | None = typer.Option(None, "--agency", "-a", help="Agency for URN generation."),
    origin: str = typer.Option("generated", "--origin", help="'generated' or 'instantiated'."),
    note: str = typer.Option("", "--note", help="Provenance note."),
) -> None:
    """Manually create a harmonized (generated/instantiated) resource from imported sources."""
    from fairwddi.harmonize.manager import create_harmonized_resource

    configure_django_for_cli()
    try:
        res = create_harmonized_resource(
            source_urns=source_urns,
            target_urn=target_urn,
            resource_type=resource_type,
            name=name,
            agency=agency,
            origin=origin,
            provenance_note=note,
        )
    except Exception as exc:
        console.print(f"[bold red]Harmonize Create Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Created Harmonized {res['resource_type']}:[/bold green] "
        f"{res['target_urn']} (job={res['job_id']})"
    )


@harmonize_app.command("link")
def harmonize_link_cmd(
    source_urns: list[str] = typer.Option(
        ..., "--source", "-s", help="Source imported resource URN(s) (repeatable)."
    ),
    into_urn: str = typer.Option(
        ..., "--into", "-t", help="Target generated/instantiated resource URN."
    ),
    resource_type: str | None = typer.Option(None, "--type", help="Optional resource type check."),
    note: str = typer.Option("", "--note", help="Provenance note."),
) -> None:
    """Manually link imported resource(s) into an existing harmonized resource."""
    from fairwddi.harmonize.manager import link_to_harmonized_resource

    configure_django_for_cli()
    try:
        res = link_to_harmonized_resource(
            source_urns=source_urns,
            target_urn=into_urn,
            resource_type=resource_type,
            provenance_note=note,
        )
    except Exception as exc:
        console.print(f"[bold red]Harmonize Link Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Linked {len(res['source_urns'])} source(s) "
        f"into {res['target_urn']}[/bold green] (job={res['job_id']})"
    )


@harmonize_app.command("undo")
def harmonize_undo_cmd(
    job_id: str = typer.Argument(..., help="Harmonization job_id to revert."),
) -> None:
    """Revert an executed Harmonization Job using EventLog snapshots."""
    from fairwddi.harmonize.manager import undo_harmonization

    configure_django_for_cli()
    try:
        res = undo_harmonization(job_id)
    except Exception as exc:
        console.print(f"[bold red]Harmonize Undo Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Reverted Job [cyan]{res['job_id']}[/cyan]:[/bold green] "
        f"removed {res.get('removed_semantic_links', 0)} semantic link(s)."
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

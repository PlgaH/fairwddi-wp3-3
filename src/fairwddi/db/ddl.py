"""DDL generator and export utility for PostgreSQL >= 17."""

from __future__ import annotations

from pathlib import Path


def get_sql_ddl_path() -> Path:
    """Return the absolute path to the bundled postgres_init.sql script."""
    return Path(__file__).resolve().parent / "sql" / "postgres_init.sql"


def generate_ddl_sql() -> str:
    """Read and return the raw PostgreSQL DDL SQL string."""
    ddl_path = get_sql_ddl_path()
    if ddl_path.exists():
        return ddl_path.read_text(encoding="utf-8")

    raise FileNotFoundError(f"PostgreSQL DDL script not found at {ddl_path}")


def export_postgres_ddl(output_path: str | Path | None = None) -> str:
    """Export PostgreSQL DDL to a destination file path or return the SQL string."""
    sql = generate_ddl_sql()
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sql, encoding="utf-8")
    return sql

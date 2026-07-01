from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def get_connection(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def list_tables(db_path: str) -> list[str]:
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to list tables for {db_path}: {exc}") from exc
    return [row["name"] for row in rows]


def get_table_columns(db_path: str, table_name: str) -> list[dict[str, Any]]:
    _ensure_table_exists(db_path, table_name)
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(f"PRAGMA table_info({_quote_identifier(table_name)})").fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to read columns for table '{table_name}': {exc}") from exc

    return [
        {
            "name": row["name"],
            "type": row["type"],
            "not_null": bool(row["notnull"]),
            "default_value": row["dflt_value"],
            "primary_key": bool(row["pk"]),
        }
        for row in rows
    ]


def get_foreign_keys(db_path: str, table_name: str) -> list[dict[str, str]]:
    _ensure_table_exists(db_path, table_name)
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(f"PRAGMA foreign_key_list({_quote_identifier(table_name)})").fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to read foreign keys for table '{table_name}': {exc}") from exc

    return [
        {
            "table": table_name,
            "from": row["from"],
            "to_table": row["table"],
            "to": row["to"],
        }
        for row in rows
    ]


def get_sample_rows(db_path: str, table_name: str, limit: int = 3) -> list[dict[str, Any]]:
    _ensure_table_exists(db_path, table_name)
    if limit < 0:
        raise ValueError("Sample row limit must be non-negative")

    quoted_table = _quote_identifier(table_name)
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(f"SELECT * FROM {quoted_table} LIMIT ?", (limit,)).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to read sample rows for table '{table_name}': {exc}") from exc

    return [dict(row) for row in rows]


def read_database_schema(db_path: str, sample_limit: int = 3) -> dict[str, Any]:
    tables = []
    for table_name in list_tables(db_path):
        columns = get_table_columns(db_path, table_name)
        tables.append(
            {
                "table_name": table_name,
                "columns": columns,
                "primary_keys": [column["name"] for column in columns if column["primary_key"]],
                "foreign_keys": get_foreign_keys(db_path, table_name),
                "sample_rows": get_sample_rows(db_path, table_name, sample_limit),
            }
        )
    return {"db_path": db_path, "tables": tables}


def format_schema_for_prompt(schema: dict[str, Any]) -> str:
    lines = [f"Database: {schema.get('db_path', '')}"]
    for table in schema.get("tables", []):
        lines.append("")
        lines.append(f"Table: {table.get('table_name', '')}")
        lines.append("Columns:")
        for column in table.get("columns", []):
            flags = []
            if column.get("primary_key"):
                flags.append("primary key")
            if column.get("not_null"):
                flags.append("not null")
            suffix = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"- {column.get('name')}: {column.get('type')}{suffix}")

        primary_keys = table.get("primary_keys", [])
        lines.append(f"Primary keys: {', '.join(primary_keys) if primary_keys else 'none'}")

        foreign_keys = table.get("foreign_keys", [])
        lines.append("Foreign keys:")
        if foreign_keys:
            for key in foreign_keys:
                lines.append(
                    f"- {key.get('table')}.{key.get('from')} -> {key.get('to_table')}.{key.get('to')}"
                )
        else:
            lines.append("- none")

        sample_rows = table.get("sample_rows", [])
        lines.append("Sample rows:")
        if sample_rows:
            for row in sample_rows:
                lines.append(f"- {row}")
        else:
            lines.append("- none")

    return "\n".join(lines)


def read_sqlite_schema(db_path: str | Path) -> str:
    return format_schema_for_prompt(read_database_schema(str(db_path)))


def _ensure_table_exists(db_path: str, table_name: str) -> None:
    if table_name not in list_tables(db_path):
        raise ValueError(f"Table not found in database: {table_name}")


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("data/northwind/northwind.db")

REQUIRED_TABLES = [
    "customers",
    "employees",
    "shippers",
    "suppliers",
    "categories",
    "products",
    "orders",
    "order_details",
    "employee_targets",
    "returns",
    "inventory_transactions",
]


def get_table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def count_rows(conn: sqlite3.Connection, table_name: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def check_northwind_database(db_path: Path = DB_PATH) -> None:
    if not db_path.exists():
        print("Database not found. Please run:")
        print("python scripts/create_northwind_db.py")
        return

    with sqlite3.connect(db_path) as conn:
        table_names = get_table_names(conn)
        missing_tables = sorted(set(REQUIRED_TABLES) - set(table_names))
        if missing_tables:
            missing = ", ".join(missing_tables)
            raise RuntimeError(f"Northwind database is missing required tables: {missing}")

        print(f"Database path: {db_path.resolve()}")
        print("Tables:")
        for table_name in table_names:
            print(f"- {table_name}")

        print("Table row counts:")
        for table_name in table_names:
            print(f"- {table_name}: {count_rows(conn, table_name)}")

    print("Northwind database check passed.")


def main() -> None:
    check_northwind_database()


if __name__ == "__main__":
    main()

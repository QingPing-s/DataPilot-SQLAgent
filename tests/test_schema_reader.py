from __future__ import annotations

import sqlite3

import pytest

from src.schema_reader import (
    format_schema_for_prompt,
    get_connection,
    get_foreign_keys,
    get_sample_rows,
    get_table_columns,
    list_tables,
    read_database_schema,
    read_sqlite_schema,
)


@pytest.fixture()
def demo_db(tmp_path):
    db_path = tmp_path / "demo.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                country TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id TEXT NOT NULL,
                order_date TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
            )
            """
        )
        conn.execute("INSERT INTO customers VALUES ('ALFKI', 'Alfreds Futterkiste', 'Germany')")
        conn.execute("INSERT INTO orders VALUES (1, 'ALFKI', '2024-01-15')")
    return db_path


def test_get_connection_sets_row_factory(demo_db):
    with get_connection(str(demo_db)) as conn:
        row = conn.execute("SELECT customer_id FROM customers").fetchone()

    assert row["customer_id"] == "ALFKI"


def test_get_connection_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        get_connection(str(tmp_path / "missing.sqlite"))


def test_list_tables_excludes_internal_tables(demo_db):
    assert list_tables(str(demo_db)) == ["customers", "orders"]


def test_get_table_columns(demo_db):
    columns = get_table_columns(str(demo_db), "customers")

    assert columns[0]["name"] == "customer_id"
    assert columns[0]["primary_key"] is True
    assert columns[1]["not_null"] is True


def test_get_foreign_keys(demo_db):
    foreign_keys = get_foreign_keys(str(demo_db), "orders")

    assert foreign_keys == [
        {
            "table": "orders",
            "from": "customer_id",
            "to_table": "customers",
            "to": "customer_id",
        }
    ]


def test_get_sample_rows(demo_db):
    rows = get_sample_rows(str(demo_db), "customers", limit=1)

    assert rows == [{"customer_id": "ALFKI", "company_name": "Alfreds Futterkiste", "country": "Germany"}]


def test_read_database_schema_matches_expected_shape(demo_db):
    schema = read_database_schema(str(demo_db), sample_limit=1)

    assert schema["db_path"] == str(demo_db)
    assert schema["tables"][0]["table_name"] == "customers"
    assert schema["tables"][0]["primary_keys"] == ["customer_id"]
    assert schema["tables"][1]["foreign_keys"][0]["to_table"] == "customers"


def test_format_schema_for_prompt_contains_core_sections(demo_db):
    prompt_text = format_schema_for_prompt(read_database_schema(str(demo_db), sample_limit=1))

    assert "Table: customers" in prompt_text
    assert "Columns:" in prompt_text
    assert "Primary keys: customer_id" in prompt_text
    assert "orders.customer_id -> customers.customer_id" in prompt_text
    assert "Sample rows:" in prompt_text


def test_read_sqlite_schema_compatibility_wrapper(demo_db):
    prompt_text = read_sqlite_schema(demo_db)

    assert "Table: customers" in prompt_text

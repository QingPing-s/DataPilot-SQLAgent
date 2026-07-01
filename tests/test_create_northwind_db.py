from __future__ import annotations

import sqlite3

from scripts.create_northwind_db import create_northwind_db
from src.schema_reader import read_database_schema
from src.sql_executor import execute_sql
from src.sql_generator import fallback_generate_sql


def test_create_northwind_v2_database(tmp_path):
    db_path = create_northwind_db(tmp_path / "northwind.db")

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        product_columns = {row[1] for row in connection.execute("PRAGMA table_info(products)")}
        order_columns = {row[1] for row in connection.execute("PRAGMA table_info(orders)")}
        order_count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        detail_count = connection.execute("SELECT COUNT(*) FROM order_details").fetchone()[0]
        first_order, last_order = connection.execute(
            "SELECT MIN(order_date), MAX(order_date) FROM orders"
        ).fetchone()
        return_count = connection.execute("SELECT COUNT(*) FROM returns").fetchone()[0]
        transaction_count = connection.execute("SELECT COUNT(*) FROM inventory_transactions").fetchone()[0]
        target_count = connection.execute("SELECT COUNT(*) FROM employee_targets").fetchone()[0]
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()

    assert {"employee_targets", "returns", "inventory_transactions"}.issubset(tables)
    assert {"unit_cost", "reorder_level", "units_on_order", "discontinued"}.issubset(product_columns)
    assert {"required_date", "shipped_date", "freight", "order_status"}.issubset(order_columns)
    assert order_count == 500
    assert detail_count >= 1000
    assert first_order.startswith("2023-")
    assert last_order.startswith("2025-")
    assert return_count > 0
    assert transaction_count > detail_count
    assert target_count == 8 * 36
    assert foreign_key_errors == []


def test_northwind_v2_business_fallback_queries_execute(tmp_path):
    db_path = create_northwind_db(tmp_path / "northwind.db")
    schema = read_database_schema(str(db_path), sample_limit=0)

    for question in (
        "利润最高的产品",
        "员工目标完成率最高的是谁",
        "准时率最低的承运商",
        "退货最多的产品",
        "哪些产品需要补货",
    ):
        generated = fallback_generate_sql(question, schema)
        result = execute_sql(str(db_path), generated["sql"])
        assert result["success"] is True, f"{question}: {result['error']}"
        assert result["row_count"] > 0, question

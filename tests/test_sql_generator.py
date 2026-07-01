from __future__ import annotations

import pytest

from src import sql_generator


def test_generate_sql_plan_validates_llm_json(monkeypatch):
    def fake_call_llm_json(messages, temperature=0.2):
        return {
            "question": "How many customers?",
            "relevant_tables": ["customers"],
            "relevant_columns": ["customer_id"],
            "join_keys": [],
            "filters": [],
            "aggregations": ["COUNT(*)"],
            "order_by": [],
            "limit": None,
            "reasoning": "Count customer rows.",
        }

    monkeypatch.setattr(sql_generator, "call_llm_json", fake_call_llm_json)

    result = sql_generator.generate_sql_plan("How many customers?", "Table: customers")

    assert result["relevant_tables"] == ["customers"]


def test_generate_sql_validates_llm_json(monkeypatch):
    def fake_call_llm_json(messages, temperature=0.2):
        return {"sql": "SELECT COUNT(*) AS count FROM customers", "explanation": "Counts customers."}

    monkeypatch.setattr(sql_generator, "call_llm_json", fake_call_llm_json)

    result = sql_generator.generate_sql("How many customers?", "Table: customers", {"relevant_tables": ["customers"]})

    assert result["sql"].startswith("SELECT")


def test_generate_sql_raises_clear_error_on_invalid_json(monkeypatch):
    def fake_call_llm_json(messages, temperature=0.2):
        return {"sql": "SELECT 1"}

    monkeypatch.setattr(sql_generator, "call_llm_json", fake_call_llm_json)

    with pytest.raises(RuntimeError, match="invalid GeneratedSQL"):
        sql_generator.generate_sql("Demo?", "Table: sample", {})


def test_fallback_generate_sql_does_not_call_llm(monkeypatch):
    def fail_call_llm_json(messages, temperature=0.2):
        raise AssertionError("LLM should not be called")

    monkeypatch.setattr(sql_generator, "call_llm_json", fail_call_llm_json)
    schema = {
        "tables": [
            {
                "table_name": "customers",
                "columns": [{"name": "customer_id", "type": "TEXT"}],
            }
        ]
    }

    result = sql_generator.fallback_generate_sql("list customers", schema)

    assert result["sql"] == "SELECT * FROM customers LIMIT 10"


def test_northwind_fallback_supports_chinese_employee_performance():
    result = sql_generator.fallback_generate_sql("员工绩效最高的是谁", _northwind_schema())

    assert "SUM(od.unit_price * od.quantity" in result["sql"]
    assert "average_order_value" in result["sql"]
    assert result["sql"].endswith("LIMIT 1")


def test_northwind_fallback_rejects_profit_without_cost_fields():
    result = sql_generator.fallback_generate_sql("最大的利润是多少", _northwind_schema())

    assert "cannot be calculated" in result["sql"]
    assert sql_generator.is_unsupported_profit_question("最大的利润是多少", _northwind_schema()) is True


def test_northwind_fallback_supports_chinese_category_sales():
    result = sql_generator.fallback_generate_sql("统计每个产品类别的销售额", _northwind_schema())

    assert "FROM categories c" in result["sql"]
    assert "sales_amount" in result["sql"]


def _northwind_schema():
    table_names = [
        "customers",
        "employees",
        "shippers",
        "suppliers",
        "categories",
        "products",
        "orders",
        "order_details",
    ]
    return {
        "tables": [
            {
                "table_name": table_name,
                "columns": [{"name": "employee_id", "type": "INTEGER"}],
            }
            for table_name in table_names
        ]
    }

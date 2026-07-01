from __future__ import annotations

from src import sql_repair


def test_repair_sql_validates_llm_json(monkeypatch):
    def fake_call_llm_json(messages, temperature=0.2):
        return {
            "repaired_sql": "SELECT customer_id FROM customers",
            "repair_reason": "Fixed missing column name.",
        }

    monkeypatch.setattr(sql_repair, "call_llm_json", fake_call_llm_json)

    result = sql_repair.repair_sql("List customers", "Table: customers", "SELECT bad FROM customers", "no such column")

    assert result["repaired_sql"] == "SELECT customer_id FROM customers"

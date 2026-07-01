from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.llm_client import call_llm_json
from src.prompts import build_sql_generation_prompt, build_sql_plan_prompt
from src.schemas import GeneratedSQL, SQLPlan


def generate_sql_plan(question: str, schema_text: str) -> dict[str, Any]:
    """
    Call DeepSeek API to generate and validate a SQLPlan.
    """
    try:
        payload = call_llm_json(build_sql_plan_prompt(question, schema_text))
        return _model_to_dict(SQLPlan(**payload))
    except ValidationError as exc:
        raise RuntimeError(f"LLM returned invalid SQLPlan JSON: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to generate SQL plan: {exc}") from exc


def generate_sql(question: str, schema_text: str, plan: dict) -> dict[str, Any]:
    """
    Call DeepSeek API to generate and validate GeneratedSQL.
    """
    try:
        payload = call_llm_json(build_sql_generation_prompt(question, schema_text, plan))
        return _model_to_dict(GeneratedSQL(**payload))
    except ValidationError as exc:
        raise RuntimeError(f"LLM returned invalid GeneratedSQL JSON: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to generate SQL: {exc}") from exc


def fallback_generate_sql(question: str, schema: dict) -> dict[str, Any]:
    """
    Rule-based local demo fallback. This does not call an LLM and is not for formal eval.
    """
    tables = schema.get("tables", [])
    if not tables:
        return _model_to_dict(GeneratedSQL(sql="SELECT 1 AS value", explanation="Fallback query without schema."))

    question_lower = question.lower()
    if _is_northwind_schema(schema):
        northwind_result = _northwind_fallback(question_lower, schema)
        if northwind_result:
            return _model_to_dict(GeneratedSQL(**northwind_result))

    table = _pick_table(question_lower, tables)
    table_name = table["table_name"]
    columns = table.get("columns", [])
    numeric_column = _pick_numeric_column(columns)

    if "count" in question_lower or "how many" in question_lower:
        sql = f"SELECT COUNT(*) AS count FROM {table_name}"
        explanation = f"Fallback count query over {table_name}."
    elif "average" in question_lower or "avg" in question_lower:
        if numeric_column:
            sql = f"SELECT AVG({numeric_column}) AS average_{numeric_column} FROM {table_name}"
            explanation = f"Fallback average query over {table_name}.{numeric_column}."
        else:
            sql = f"SELECT * FROM {table_name} LIMIT 10"
            explanation = f"Fallback list query because no numeric column was found in {table_name}."
    elif "total" in question_lower or "sum" in question_lower:
        if numeric_column:
            sql = f"SELECT SUM({numeric_column}) AS total_{numeric_column} FROM {table_name}"
            explanation = f"Fallback total query over {table_name}.{numeric_column}."
        else:
            sql = f"SELECT * FROM {table_name} LIMIT 10"
            explanation = f"Fallback list query because no numeric column was found in {table_name}."
    elif "top" in question_lower or "highest" in question_lower or "most" in question_lower:
        if numeric_column:
            sql = f"SELECT * FROM {table_name} ORDER BY {numeric_column} DESC LIMIT 10"
            explanation = f"Fallback top query ordered by {table_name}.{numeric_column}."
        else:
            sql = f"SELECT * FROM {table_name} LIMIT 10"
            explanation = f"Fallback list query because no numeric column was found in {table_name}."
    elif "list" in question_lower or "show" in question_lower:
        sql = f"SELECT * FROM {table_name} LIMIT 10"
        explanation = f"Fallback list query over {table_name}."
    else:
        first_table = tables[0]["table_name"]
        sql = f"SELECT * FROM {first_table} LIMIT 10"
        explanation = f"Fallback default query over first table {first_table}."

    return _model_to_dict(GeneratedSQL(sql=sql, explanation=explanation))


def is_unsupported_profit_question(question: str, schema: dict) -> bool:
    question_lower = question.lower()
    asks_for_profit = _contains_any(question_lower, ("利润", "毛利", "净利", "profit", "margin"))
    if not asks_for_profit:
        return False

    available_columns = {
        column.get("name", "").lower()
        for table in schema.get("tables", [])
        for column in table.get("columns", [])
    }
    cost_columns = {"cost", "unit_cost", "purchase_price", "cost_price"}
    return not bool(available_columns & cost_columns)


def _northwind_fallback(question: str, schema: dict) -> dict[str, str] | None:
    if is_unsupported_profit_question(question, schema):
        return {
            "sql": (
                "SELECT 'Profit cannot be calculated because the database has no product cost, "
                "freight cost, tax, or return fields.' AS limitation"
            ),
            "explanation": "The requested profit metric is unavailable in the current Northwind schema.",
        }

    top_one = _contains_any(
        question,
        ("最高", "最大", "最多", "最低", "最少", "最差", "第一", "top", "highest", "most", "lowest", "worst"),
    )
    limit = " LIMIT 1" if top_one else " LIMIT 10"

    if _contains_any(question, ("利润", "毛利", "净利", "profit", "margin")):
        return {
            "sql": (
                "WITH return_totals AS ("
                "SELECT order_id, product_id, SUM(quantity) AS returned_quantity "
                "FROM returns GROUP BY order_id, product_id), "
                "product_profit AS ("
                "SELECT p.product_id, p.product_name, "
                "SUM(od.unit_price * (1 - od.discount) * "
                "(od.quantity - COALESCE(r.returned_quantity, 0))) AS revenue, "
                "SUM(od.cost_price * (od.quantity - COALESCE(r.returned_quantity, 0))) AS cost "
                "FROM products p JOIN order_details od ON p.product_id = od.product_id "
                "JOIN orders o ON od.order_id = o.order_id "
                "LEFT JOIN return_totals r ON od.order_id = r.order_id AND od.product_id = r.product_id "
                "WHERE o.order_status <> 'Cancelled' GROUP BY p.product_id, p.product_name) "
                "SELECT product_id, product_name, ROUND(revenue, 2) AS revenue, "
                "ROUND(cost, 2) AS cost, ROUND(revenue - cost, 2) AS gross_profit, "
                "ROUND((revenue - cost) * 100.0 / NULLIF(revenue, 0), 2) AS gross_margin_percent "
                f"FROM product_profit ORDER BY gross_profit DESC{limit}"
            ),
            "explanation": "Calculates product gross profit from net sales after returns and historical cost price.",
        }

    if _contains_any(question, ("目标", "完成率", "达成率", "target", "quota")):
        return {
            "sql": (
                "WITH actual_sales AS ("
                "SELECT o.employee_id, CAST(strftime('%Y', o.order_date) AS INTEGER) AS sales_year, "
                "CAST(strftime('%m', o.order_date) AS INTEGER) AS sales_month, "
                "SUM(od.unit_price * od.quantity * (1 - od.discount)) AS sales_amount "
                "FROM orders o JOIN order_details od ON o.order_id = od.order_id "
                "WHERE o.order_status <> 'Cancelled' "
                "GROUP BY o.employee_id, sales_year, sales_month) "
                "SELECT e.employee_id, e.first_name, e.last_name, t.target_year, t.target_month, "
                "ROUND(t.sales_target, 2) AS sales_target, "
                "ROUND(COALESCE(a.sales_amount, 0), 2) AS sales_amount, "
                "ROUND(COALESCE(a.sales_amount, 0) * 100.0 / t.sales_target, 2) AS target_completion_percent "
                "FROM employee_targets t JOIN employees e ON t.employee_id = e.employee_id "
                "LEFT JOIN actual_sales a ON t.employee_id = a.employee_id "
                "AND t.target_year = a.sales_year AND t.target_month = a.sales_month "
                f"ORDER BY target_completion_percent DESC{limit}"
            ),
            "explanation": "Compares each employee's monthly sales with the configured monthly sales target.",
        }

    if _contains_any(question, ("准时", "延迟", "配送时长", "送达时间", "on-time", "delay", "delivery time")):
        ascending = _contains_any(question, ("最低", "最差", "lowest", "worst"))
        direction = "ASC" if ascending else "DESC"
        return {
            "sql": (
                "SELECT s.shipper_id, s.company_name, COUNT(o.order_id) AS delivered_orders, "
                "ROUND(AVG(julianday(o.shipped_date) - julianday(o.order_date)), 2) AS average_shipping_days, "
                "ROUND(100.0 * SUM(CASE WHEN o.shipped_date <= o.required_date THEN 1 ELSE 0 END) "
                "/ COUNT(o.order_id), 2) AS on_time_rate "
                "FROM shippers s JOIN orders o ON s.shipper_id = o.shipper_id "
                "WHERE o.order_status <> 'Cancelled' AND o.shipped_date IS NOT NULL "
                "GROUP BY s.shipper_id, s.company_name "
                f"ORDER BY on_time_rate {direction}, average_shipping_days ASC{limit}"
            ),
            "explanation": "Calculates average shipping time and on-time rate for each shipper.",
        }

    if _contains_any(question, ("退货", "return")):
        return {
            "sql": (
                "SELECT p.product_id, p.product_name, COUNT(r.return_id) AS return_count, "
                "SUM(r.quantity) AS returned_quantity "
                "FROM returns r JOIN products p ON r.product_id = p.product_id "
                "GROUP BY p.product_id, p.product_name "
                f"ORDER BY returned_quantity DESC, return_count DESC{limit}"
            ),
            "explanation": "Ranks products by returned quantity and number of return records.",
        }

    if _contains_any(question, ("员工", "雇员", "employee", "staff")):
        return {
            "sql": (
                "SELECT e.employee_id, e.first_name, e.last_name, "
                "COUNT(DISTINCT o.order_id) AS order_count, "
                "ROUND(COALESCE(SUM(od.unit_price * od.quantity * (1 - od.discount)), 0), 2) AS sales_amount, "
                "ROUND(COALESCE(SUM(od.unit_price * od.quantity * (1 - od.discount)), 0) / "
                "NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS average_order_value "
                "FROM employees e LEFT JOIN orders o ON e.employee_id = o.employee_id "
                "LEFT JOIN order_details od ON o.order_id = od.order_id "
                "WHERE o.order_status <> 'Cancelled' "
                "GROUP BY e.employee_id, e.first_name, e.last_name "
                f"ORDER BY sales_amount DESC, order_count DESC{limit}"
            ),
            "explanation": "Ranks employee performance by handled sales amount, with order count and average order value.",
        }

    if _contains_any(question, ("客户", "customer")):
        return {
            "sql": (
                "SELECT c.customer_id, c.company_name, COUNT(DISTINCT o.order_id) AS order_count, "
                "ROUND(COALESCE(SUM(od.unit_price * od.quantity * (1 - od.discount)), 0), 2) AS sales_amount "
                "FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id "
                "LEFT JOIN order_details od ON o.order_id = od.order_id "
                "WHERE o.order_status <> 'Cancelled' "
                "GROUP BY c.customer_id, c.company_name "
                f"ORDER BY sales_amount DESC, order_count DESC{limit}"
            ),
            "explanation": "Ranks customers by discounted sales amount.",
        }

    if _contains_any(question, ("供应商", "supplier")):
        return {
            "sql": (
                "SELECT s.supplier_id, s.company_name, "
                "ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount)), 2) AS sales_amount "
                "FROM suppliers s JOIN products p ON s.supplier_id = p.supplier_id "
                "JOIN order_details od ON p.product_id = od.product_id "
                "JOIN orders o ON od.order_id = o.order_id WHERE o.order_status <> 'Cancelled' "
                "GROUP BY s.supplier_id, s.company_name "
                f"ORDER BY sales_amount DESC{limit}"
            ),
            "explanation": "Ranks suppliers by sales generated by their products.",
        }

    if _contains_any(question, ("承运商", "配送商", "物流商", "shipper")):
        return {
            "sql": (
                "SELECT s.shipper_id, s.company_name, COUNT(o.order_id) AS order_count "
                "FROM shippers s LEFT JOIN orders o ON s.shipper_id = o.shipper_id "
                "GROUP BY s.shipper_id, s.company_name "
                f"ORDER BY order_count DESC, s.shipper_id{limit}"
            ),
            "explanation": "Ranks shippers by number of handled orders.",
        }

    if _contains_any(question, ("库存", "缺货", "补货", "stock", "inventory")):
        if _contains_any(question, ("补货", "低于", "预警", "reorder", "restock")):
            return {
                "sql": (
                    "SELECT product_id, product_name, units_in_stock, reorder_level, units_on_order "
                    "FROM products WHERE units_in_stock <= reorder_level OR units_on_order > 0 "
                    "ORDER BY units_in_stock ASC, units_on_order DESC LIMIT 10"
                ),
                "explanation": "Lists products at or below their reorder level, including inbound stock.",
            }
        return {
            "sql": (
                "SELECT p.product_id, p.product_name, p.units_in_stock, "
                "COALESCE(SUM(od.quantity), 0) AS units_sold, "
                "ROUND(COALESCE(SUM(od.unit_price * od.quantity * (1 - od.discount)), 0), 2) AS sales_amount "
                "FROM products p LEFT JOIN order_details od ON p.product_id = od.product_id "
                "GROUP BY p.product_id, p.product_name, p.units_in_stock "
                "ORDER BY p.units_in_stock ASC, units_sold DESC LIMIT 10"
            ),
            "explanation": "Shows low-stock products together with units sold and sales amount.",
        }

    if _contains_any(question, ("月度", "每月", "月份", "monthly", "month", "趋势", "trend")):
        return {
            "sql": (
                "SELECT substr(o.order_date, 1, 7) AS sales_month, "
                "COUNT(DISTINCT o.order_id) AS order_count, "
                "ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount)), 2) AS sales_amount "
                "FROM orders o JOIN order_details od ON o.order_id = od.order_id "
                "WHERE o.order_status <> 'Cancelled' "
                "GROUP BY substr(o.order_date, 1, 7) ORDER BY sales_month"
            ),
            "explanation": "Summarizes monthly order count and discounted sales amount.",
        }

    if _contains_any(question, ("国家", "地区", "country")):
        return {
            "sql": (
                "SELECT o.ship_country AS country, COUNT(DISTINCT o.order_id) AS order_count, "
                "ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount)), 2) AS sales_amount "
                "FROM orders o JOIN order_details od ON o.order_id = od.order_id "
                "WHERE o.order_status <> 'Cancelled' "
                "GROUP BY o.ship_country "
                f"ORDER BY sales_amount DESC, order_count DESC{limit}"
            ),
            "explanation": "Ranks shipping countries by discounted sales amount.",
        }

    if _contains_any(question, ("类别", "分类", "品类", "category")):
        return {
            "sql": (
                "SELECT c.category_name, "
                "ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount)), 2) AS sales_amount "
                "FROM categories c JOIN products p ON c.category_id = p.category_id "
                "JOIN order_details od ON p.product_id = od.product_id "
                "JOIN orders o ON od.order_id = o.order_id WHERE o.order_status <> 'Cancelled' "
                "GROUP BY c.category_id, c.category_name "
                f"ORDER BY sales_amount DESC{limit}"
            ),
            "explanation": "Ranks product categories by discounted sales amount.",
        }

    return None


def _is_northwind_schema(schema: dict) -> bool:
    table_names = {table.get("table_name") for table in schema.get("tables", [])}
    return {"customers", "employees", "products", "orders", "order_details"}.issubset(table_names)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _pick_table(question_lower: str, tables: list[dict[str, Any]]) -> dict[str, Any]:
    for table in tables:
        table_name = table.get("table_name", "")
        normalized = table_name.lower()
        singular = normalized[:-1] if normalized.endswith("s") else normalized
        if normalized in question_lower or singular in question_lower:
            return table
    return tables[0]


def _pick_numeric_column(columns: list[dict[str, Any]]) -> str | None:
    numeric_types = ("int", "real", "numeric", "decimal", "float", "double")
    for column in columns:
        column_type = str(column.get("type", "")).lower()
        if any(kind in column_type for kind in numeric_types):
            return column.get("name")
    return None


def _model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

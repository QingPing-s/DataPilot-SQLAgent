from __future__ import annotations

import json
from typing import Any


SQL_PLAN_SYSTEM_PROMPT = (
    "You are a SQL Planner Agent. Produce a precise SQLPlan JSON object for SQLite analysis."
)
SQL_GENERATION_SYSTEM_PROMPT = (
    "You are a SQL Generator Agent. Generate one safe SQLite SELECT query and return JSON only."
)
SQL_REPAIR_SYSTEM_PROMPT = (
    "You are a SQL Debugger Agent. Repair failed SQLite SELECT SQL and return JSON only."
)
ANSWER_SYSTEM_PROMPT = (
    "You are an Answer Analyst Agent. Explain SQL execution results faithfully and return JSON only."
)
JUDGE_SYSTEM_PROMPT = (
    "You are an LLM-as-a-Judge. Evaluate output quality without changing facts and return JSON only."
)


def build_sql_plan_prompt(question: str, schema_text: str) -> list[dict]:
    user_content = f"""
Create a SQLPlan JSON object for the user's question.

Rules:
- Use only tables and columns that appear in the schema.
- Do not invent tables, columns, filters, or relationships.
- If a join is needed, include the join key in join_keys.
- For ambiguous employee performance questions, use discounted sales amount as the primary metric;
  include order count and average order value when possible.
- Exclude orders with order_status='Cancelled' from sales and profit metrics.
- Calculate gross profit from discounted revenue minus cost_price, adjusted for returned quantity.
- For shipping performance, use shipped_date and required_date to calculate delivery time and on-time rate.
- For employee target questions, compare monthly sales with employee_targets.sales_target.
- Do not claim to calculate profit when product cost fields are absent.
- Output must be valid JSON only.

Required JSON shape:
{{
  "question": "...",
  "relevant_tables": [],
  "relevant_columns": [],
  "join_keys": [],
  "filters": [],
  "aggregations": [],
  "order_by": [],
  "limit": null,
  "reasoning": "..."
}}

Schema:
{schema_text}

Question:
{question}
""".strip()
    return _messages(SQL_PLAN_SYSTEM_PROMPT, user_content)


def build_sql_generation_prompt(question: str, schema_text: str, plan: dict) -> list[dict]:
    user_content = f"""
Generate SQLite SELECT SQL for the user's question using the schema and SQL plan.

Rules:
- Return valid JSON only.
- Only generate read-only SELECT SQL.
- Use SQLite syntax.
- Use only tables and columns that appear in the schema.
- Do not output Markdown code fences.
- Put the SQL string in the json.sql field.
- For ambiguous employee performance questions, rank by discounted sales amount rather than order count alone.
- Exclude cancelled orders from business performance metrics.
- Use order_details.cost_price and returns when calculating gross profit.
- Use employee_targets for target completion and shipped_date/required_date for shipping performance.
- Do not calculate profit unless the schema contains an explicit cost field.

Required JSON shape:
{{
  "sql": "...",
  "explanation": "..."
}}

Schema:
{schema_text}

SQL plan:
{_to_json(plan)}

Question:
{question}
""".strip()
    return _messages(SQL_GENERATION_SYSTEM_PROMPT, user_content)


def build_sql_repair_prompt(question: str, schema_text: str, failed_sql: str, error: str) -> list[dict]:
    user_content = f"""
Repair the failed SQLite SQL using the error message.

Rules:
- Return valid JSON only.
- Only generate read-only SELECT SQL.
- Fix the SQL based on the error message.
- Do not change the user's intent.
- Do not use tables or columns that are not in the schema.
- Do not output Markdown code fences.

Required JSON shape:
{{
  "repaired_sql": "...",
  "repair_reason": "..."
}}

Schema:
{schema_text}

Question:
{question}

Failed SQL:
{failed_sql}

Error:
{error}
""".strip()
    return _messages(SQL_REPAIR_SYSTEM_PROMPT, user_content)


def build_answer_prompt(question: str, sql: str, execution_result: dict) -> list[dict]:
    user_content = f"""
Generate a natural language answer based only on the SQL execution result.

Rules:
- Return valid JSON only.
- The answer must be grounded in the SQL execution result.
- Do not invent values, counts, rankings, or trends that are not present in the result.
- If the result is empty, clearly say that no rows were returned.
- Keep key_insights to 3-5 items.

Required JSON shape:
{{
  "question": "...",
  "sql": "...",
  "answer": "...",
  "key_insights": []
}}

Question:
{question}

SQL:
{sql}

Execution result:
{_to_json(execution_result)}
""".strip()
    return _messages(ANSWER_SYSTEM_PROMPT, user_content)


def build_judge_prompt(
    question: str,
    schema_text: str,
    sql: str,
    execution_result: dict,
    final_answer: dict,
    gold_sql: str | None = None,
    gold_result: dict | None = None,
) -> list[dict]:
    gold_section = {
        "gold_sql": gold_sql,
        "gold_result": gold_result,
    }
    user_content = f"""
Evaluate the SQL Agent output quality.

Rules:
- Return valid JSON only.
- Do not modify facts or provide a new answer.
- Judge only the quality of the SQL, execution result usage, and final answer.
- Focus on whether the final answer is faithful to the SQL execution result.
- If SQL execution failed, focus on the quality of error analysis.
- Scores must be from 1 to 5.

Required JSON shape:
{{
  "question_sql_alignment": 1,
  "answer_faithfulness": 1,
  "explanation_quality": 1,
  "result_usefulness": 1,
  "error_analysis_quality": 1,
  "has_hallucination": false,
  "issues": [],
  "overall_judge_score": 1,
  "judge_reason": "..."
}}

Schema:
{schema_text}

Question:
{question}

SQL:
{sql}

Execution result:
{_to_json(execution_result)}

Final answer:
{_to_json(final_answer)}

Gold reference, if available:
{_to_json(gold_section)}
""".strip()
    return _messages(JUDGE_SYSTEM_PROMPT, user_content)


def _messages(system_content: str, user_content: str) -> list[dict]:
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)
